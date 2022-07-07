# go-jax
Go game engine in JAX.

```sh
pip install git+https://github.com/NTT123/go-jax.git
```

Usage:

```python
>>> import pax
>>> from go_jax import GoBoard, put_stone
>>> 
>>> game = GoBoard(board_size=9)
>>> game, *_ = put_stone(game, "ef")
>>> game, *_ = put_stone(game, "ed")
>>> game.render()
  a b c d e f g h i 
a . . . . . . . . . 
b . . . . . . . . . 
c . . . . . . . . . 
d . . . . . . . . . 
e . . . O . X . . . 
f . . . . . . . . . 
g . . . . . . . . . 
h . . . . . . . . . 
i . . . . . . . . . 
```