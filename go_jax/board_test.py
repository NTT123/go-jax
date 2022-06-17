from .board import GoBoard, put_stone


def test_simple_go_board():
    game = GoBoard(7)
    game, info = put_stone(game, "ee")
    game, info = put_stone(game, "de")
    game, info = put_stone(game, "cb")
    game, info = put_stone(game, "fe")
    game, info = put_stone(game, "ce")
    game, info = put_stone(game, "ed")
    game, info = put_stone(game, "dd")
    game, info = put_stone(game, "ef")
    assert game.board[4, 4].item() == 0


def test_ko_move():
    game = GoBoard(7)
    game, info = put_stone(game, "ee")
    game, info = put_stone(game, "de")
    game, info = put_stone(game, "cb")
    game, info = put_stone(game, "fe")
    game, info = put_stone(game, "ce")
    game, info = put_stone(game, "ed")
    game, info = put_stone(game, "dd")
    game, info = put_stone(game, "ef")
    game, info = put_stone(game, "ee")
    assert info["done"].item() == True


def test_ladder_capture():
    game = GoBoard(5)
    game, _ = put_stone(game, "aa")
    game, _ = put_stone(game, "ba")
    game, _ = put_stone(game, "ab")
    game, _ = put_stone(game, "ac")
    game, _ = put_stone(game, "bb")
    game, _ = put_stone(game, "cb")
    game, _ = put_stone(game, "bc")
    game, _ = put_stone(game, "bd")
    game, _ = put_stone(game, "cc")
    game, _ = put_stone(game, "dc")
    game, _ = put_stone(game, "db")
    game, _ = put_stone(game, "cd")
    assert game.board[2, 2].item() == 0
    assert game.board[1, 2].item() == 0
    assert game.board[1, 1].item() == 0
    assert game.board[0, 1].item() == 0
    assert game.board[0, 0].item() == 0
    # game.render()


def test_fill_eye():
    game = GoBoard(5)
    game, _ = put_stone(game, "cd")
    game, _ = put_stone(game, "bb")
    game, _ = put_stone(game, "cb")
    game, _ = put_stone(game, "ca")
    game, _ = put_stone(game, "bc")
    game, _ = put_stone(game, "ac")
    game, _ = put_stone(game, "dc")
    game, _ = put_stone(game, "db")
    game, _ = put_stone(game, "ea")
    game, _ = put_stone(game, "dd")
    game, _ = put_stone(game, "da")
    game, _ = put_stone(game, "ec")
    game, _ = put_stone(game, "aa")
    game, _ = put_stone(game, "bd")
    game, _ = put_stone(game, "ee")
    game, _ = put_stone(game, "ce")
    game, _ = put_stone(game, "ed")
    game, _ = put_stone(game, "cc")
    assert game.board[3, 2].item() == 0
    assert game.board[1, 2].item() == 0
    assert game.board[2, 1].item() == 0
    assert game.board[2, 3].item() == 0
    # game.render()
