from functools import partial

import jax
import jax.numpy as jnp


def select_tree(pred: jnp.ndarray, a, b):
    """Selects a pytree based on the given predicate."""
    assert pred.ndim == 0 and pred.dtype == jnp.bool_, "expected boolean scalar"
    return jax.tree_map(partial(jax.lax.select, pred), a, b)
