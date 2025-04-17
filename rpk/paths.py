from functools import lru_cache
from pathlib import Path


@lru_cache
def here():
    return Path(__file__).parent


@lru_cache
def root():
    return here().parent


@lru_cache
def packages():
    return root() / "packages"
