"""
Go board gym-like environment.

Reference: https://github.com/pasky/michi/blob/master/michi.py
"""


import chex
import jax
import jax.numpy as jnp
import jmp
import pax

from .dsu import DSU


class GoBoard(pax.Module):
    """A jax-based go engine.

    It provides a gym-like API.
    """

    board_size: int  # size of the board
    num_recent_positions: int  # number of recent position will be kept
    komi: float  # added score to white player
    board: chex.Array  # the current position
    recent_boards: chex.Array  # a list of recent positions
    prev_pass_move: chex.Array  # if the previous move is a "pass" move
    turn: chex.Array  # who is playing (1: black, -1: white)
    dsu: DSU  # a data structure of connected components
    done: chex.Array  # the game ended
    count: chex.Array  # number of move played

    def __init__(
        self, board_size: int = 5, komi: float = 0.5, num_recent_positions: int = 16
    ):
        super().__init__()
        self.board_size = board_size
        self.num_recent_positions = num_recent_positions
        self.komi = komi
        self.reset()

    def reset(self):
        """Reset the game"""
        self.board = jnp.zeros((self.board_size, self.board_size), dtype=jnp.int8)
        self.recent_boards = jnp.stack([self.board] * self.num_recent_positions)
        self.prev_pass_move = jnp.array(False, dtype=jnp.bool_)
        self.turn = jnp.array(1, dtype=jnp.int8)
        self.dsu = DSU(self.board_size**2)
        self.done = jnp.array(False, dtype=jnp.bool_)
        self.count = jnp.array(0, dtype=jnp.int32)

    @pax.pure
    def step(self, action):
        """One environment step.

        For "pass" move, action = board_size x board_size
        """
        is_pass_move = action == (self.board_size**2)
        action = jnp.clip(action, a_min=0, a_max=self.board_size**2 - 1)
        i, j = jnp.divmod(action, self.board_size)
        is_invalid_action = self.board[i, j] != 0
        board = self.board.at[i, j].set(self.turn).reshape((-1,))

        ## update the dsu

        def update_dsu(s, loc):
            update = pax.pure(lambda s: (s, s.union_sets(action, loc))[0])
            return jmp.select_tree(board[action] == board[loc], update(s), s)

        def board_clip(x):
            return jnp.clip(x, a_min=0, a_max=self.board_size - 1)

        dsu = self.dsu
        l1 = board_clip(i - 1) * self.board_size + j
        l2 = board_clip(i + 1) * self.board_size + j
        l3 = i * self.board_size + board_clip(j - 1)
        l4 = i * self.board_size + board_clip(j + 1)
        dsu = update_dsu(dsu, l1)
        dsu = update_dsu(dsu, l2)
        dsu = update_dsu(dsu, l3)
        dsu = update_dsu(dsu, l4)
        dsu, roots = pax.pure(lambda s: (s, s.get_all_roots()))(dsu)

        ## kill stones with no liberties

        def nearby_filter(x):
            x = x.reshape((self.board_size, self.board_size))
            padded_x = jnp.pad(x, ((1, 1), (1, 1)))
            x1 = padded_x[:-2, 1:-1]
            x2 = padded_x[2:, 1:-1]
            x3 = padded_x[1:-1, :-2]
            x4 = padded_x[1:-1, 2:]
            x12 = jnp.logical_or(x1, x2)
            x34 = jnp.logical_or(x3, x4)
            x = jnp.logical_or(x12, x34)
            return x.reshape((-1,))

        def remove_stones(board, loc):
            empty = board == 0
            region = roots == roots[loc]  # the region of interest
            nearby_empty = jnp.logical_and(region, nearby_filter(empty))
            alive = jnp.any(nearby_empty)
            cleared_board = jnp.where(region, 0, board)
            return jnp.where(alive, board, cleared_board)

        opp = -board[action]
        board = jmp.select_tree(board[l1] == opp, remove_stones(board, l1), board)
        board = jmp.select_tree(board[l2] == opp, remove_stones(board, l2), board)
        board = jmp.select_tree(board[l3] == opp, remove_stones(board, l3), board)
        board = jmp.select_tree(board[l4] == opp, remove_stones(board, l4), board)

        # self-capture is not allowed
        board = remove_stones(board, action)
        is_invalid_action = jnp.logical_or(is_invalid_action, board[action] == 0)

        # dsu reset for removed stones
        dsu_reset = pax.pure(lambda s, m: (s, s.masked_reset(m))[0])
        dsu = dsu_reset(dsu, board == 0)

        board = board.reshape(self.board.shape)
        recent_boards = self.recent_boards
        same_board = jnp.any(jnp.all(recent_boards == board[None], axis=(1, 2)))
        repeat_position = jnp.logical_and(same_board, jnp.logical_not(is_pass_move))
        is_invalid_action = jnp.logical_or(is_invalid_action, repeat_position)

        # reset board and dsu for a pass move
        board, dsu = jmp.select_tree(is_pass_move, (self.board, self.dsu), (board, dsu))
        # a pass move is always a valid action
        is_invalid_action = jnp.where(is_pass_move, False, is_invalid_action)

        # is the game terminated?
        done = self.done
        done = jnp.logical_or(done, is_invalid_action)
        two_passes = jnp.logical_and(self.prev_pass_move, is_pass_move)
        done = jnp.logical_or(done, two_passes)
        count = self.count + 1
        done = jnp.logical_or(done, count >= self.max_num_steps())

        # update internal states
        game_score = self.final_score(board, self.turn)
        self.turn = jnp.where(done, self.turn, -self.turn)
        self.done = done
        self.board = board
        self.prev_pass_move = is_pass_move
        self.dsu = dsu
        self.count = count
        self.recent_boards = jnp.concatenate((recent_boards[1:], board[None]))

        reward = jnp.array(0.0)
        reward = jnp.where(done, jnp.where(game_score > 0, 1.0, -1.0), reward)
        reward = jnp.where(is_invalid_action, -1.0, reward)
        return self, reward

    def final_score(self, board, turn):
        """Compute final score of the game."""
        my_score = jnp.sum(board == turn, axis=(-1, -2))
        my_score = my_score + self.count_eyes(board, turn)
        my_score = my_score - self.turn * self.komi
        opp_score = jnp.sum(board == -turn, axis=(-1, -2))
        opp_score = opp_score + self.count_eyes(board, -turn)
        return my_score - opp_score

    def count_eyes(self, board, turn):
        """Count number of eyes for a player."""
        board = board.reshape((self.board_size, self.board_size))
        padded_board = jnp.pad(board == turn, ((1, 1), (1, 1)), constant_values=True)
        x1 = padded_board[:-2, 1:-1]
        x2 = padded_board[2:, 1:-1]
        x3 = padded_board[1:-1, :-2]
        x4 = padded_board[1:-1, 2:]
        x12 = jnp.logical_and(x1, x2)
        x34 = jnp.logical_and(x3, x4)
        x = jnp.logical_and(x12, x34)
        return jnp.sum(x)

    def num_actions(self):
        return self.board_size**2 + 1

    def max_num_steps(self):
        return (self.board_size**2) * 2

    def observation(self):
        return jnp.swapaxes(self.recent_boards, 0, -1)

    def canonical_observation(self):
        return self.observation() * self.turn

    def is_terminated(self) -> chex.Array:
        return self.done

    def invalid_actions(self):
        """Return invalid actions."""
        # overriding stones are invalid actions.
        actions = self.board != 0
        actions = actions.reshape(actions.shape[:-2] + (-1,))
        # append "pass" action at the end
        pad = [(0, 0) for _ in range(len(actions.shape))]
        pad[-1] = (0, 1)
        return jnp.pad(actions, pad)

    def step_s(self, xy_position: str):
        """A step using string actions."""
        action = self.parse_action(xy_position)
        return self.step(action)

    def render(self):
        """Render the board on the screen."""
        print(end="  ")
        for i in range(self.board_size):
            print(chr(ord("a") + i), end=" ")
        print()
        for i in range(self.board_size):
            print(chr(ord("a") + i), end=" ")
            for j in range(self.board_size):
                stone = self.board[i, j].item()
                if stone == 1:
                    symbol = "X"
                elif stone == -1:
                    symbol = "O"
                elif stone == 0:
                    symbol = "."
                else:
                    raise ValueError(f"Unexpected value: {symbol}")
                print(symbol, end=" ")
            print()

    def parse_action(self, action_str: str) -> int:
        """Parse 2d alphabet actions + "pass" action"""
        action_str = action_str.lower()
        if action_str == "pass":
            return self.board_size * self.board_size

        i = ord(action_str[0]) - ord("a")
        j = ord(action_str[1]) - ord("a")
        return i * self.board_size + j


_env_step = jax.jit(pax.pure(lambda e, a: e.step(a)))


def put_stone(env, action):
    """put a stone on the boar"""
    action = env.parse_action(action)
    action = jnp.array(action, dtype=jnp.int32)
    return _env_step(env, action)


if __name__ == "__main__":
    game = GoBoard(9)
    while game.done.item() is False:
        game.render()
        user_action = input("> ")
        game, _ = put_stone(game, user_action)
