"""
Go board gym-like environment.
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
    turn: chex.Array  # who is playing (1: black, -1: white)

    def __init__(self, board_size: int = 9):
        super().__init__()
        self.board_size = board_size
        self.board = jnp.zeros((board_size, board_size), dtype=jnp.int32)
        self.prev_pass_move = jnp.array(False, dtype=jnp.bool_)
        self.turn = jnp.array(1, dtype=jnp.int32)
        self.dsu = DSU(board_size**2)
        self.done = jnp.array(False, dtype=jnp.bool_)

    def step(self, action):
        """One environment step.

        This function is similar to OpenAI gym `step` function.


        Note on "pass move":
            - For better performance, we did not treat "pass move" differently.
            A pass move is just a move that overrides one stone on the board.
        """
        i, j = jnp.divmod(action, self.board_size)
        prev_board = self.board
        is_pass_move = self.board[i, j] == self.turn
        is_invalid_action = self.board[i, j] == -self.turn
        self.board = self.board.at[i, j].set(self.turn)
        self.turn = -self.turn
        board = self.board.reshape((-1,))

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
        self.dsu = dsu_reset(dsu, board == 0)
        board = board.reshape(self.board.shape)
        reward = jnp.array(0.0, dtype=jnp.float32)
        done = self.done
        same_board = jnp.all(prev_board == board)
        repeat_position = jnp.logical_and(same_board, jnp.logical_not(is_pass_move))
        is_invalid_action = jnp.logical_or(is_invalid_action, repeat_position)
        done = jnp.logical_or(done, is_invalid_action)
        two_passes = jnp.logical_and(self.prev_pass_move, is_pass_move)
        done = jnp.logical_or(done, two_passes)
        self.done = done
        self.board = board
        self.prev_pass_move = is_pass_move

        return {
            "observation": self.board,
            "reward": reward,
            "done": done,
        }

    def invalid_actions(self):
        """Return invalid actions."""
        # overriding opponent's stones are invalid actions.
        return self.board == -self.turn

    def step_s(self, xy_position: str):
        """A step using string actions."""
        x_pos = ord(xy_position[0]) - ord("a")
        y_pos = ord(xy_position[1]) - ord("a")
        action = x_pos * self.board_size + y_pos
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


_env_step = jax.jit(pax.pure(lambda e, a: (e, e.step(a))))


def put_stone(env, action):
    i = ord(action[0]) - ord("a")
    j = ord(action[1]) - ord("a")
    action = i * env.board_size + j
    return _env_step(env, action)


if __name__ == "__main__":
    game = GoBoard(9)
    while game.done.item() == False:
        game.render()
        user_action = input("> ")
        game, _ = put_stone(game, user_action)
