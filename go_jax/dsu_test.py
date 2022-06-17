import jax.numpy as jnp
import pax

from .dsu import DSU


def test_dsu_init():
    s = DSU(5)
    assert s.parent.tolist() == [0, 1, 2, 3, 4]
    assert s.size.tolist() == [1, 1, 1, 1, 1]


@pax.pure
def merge_sets(s, a, b):
    s.union_sets(a, b)
    return s


@pax.pure
def get_all_roots(s):
    roots = s.get_all_roots()
    return s, roots


@pax.pure
def masked_reset(s, m):
    s.masked_reset(m)
    return s


def test_dsu_union():
    s = DSU(5)
    s = merge_sets(s, 0, 1)
    assert s.size[0].item() == 2
    s = merge_sets(s, 2, 3)
    s = merge_sets(s, 2, 4)
    assert s.size[2] == 3
    s = merge_sets(s, 0, 2)
    assert s.size[2] == 5
    s.pp()
    s, roots = get_all_roots(s)
    assert s.parent.tolist() == [2, 2, 2, 2, 2]
    print(roots)
    s.pp()


def test_masked_reset():
    s = DSU(4)
    s = merge_sets(s, 0, 1)
    s = merge_sets(s, 2, 3)
    s.pp()
    s = masked_reset(s, jnp.array([True, True, False, False]))
    assert s.parent.tolist() == [0, 1, 2, 2]
    assert s.size.tolist() == [1, 1, 2, 1]
    s.pp()
