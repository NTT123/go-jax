from setuptools import setup

__version__ = "0.2.0"
url = "https://github.com/ntt123/go-jax"

install_requires = ["jax", "jaxlib", "chex", "pax3"]
setup_requires = []
tests_require = []

setup(
    name="go-jax",
    version=__version__,
    description="Go game engine in JAX.",
    author="ntt123",
    url=url,
    keywords=["go-game", "rl", "jax", "alphago"],
    install_requires=install_requires,
    setup_requires=setup_requires,
    tests_require=tests_require,
    packages=["go_jax"],
    python_requires=">=3.7",
)
