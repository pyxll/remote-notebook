"""
Equivalent functions to the main pyxll module, but that work with a remote
Excel client instead of running in-process.
"""
from .xl_func import xl_func


__all__ = [
    "xl_func"
]
