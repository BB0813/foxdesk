"""Probe file with several intentional bugs for AperturePrism bot verification."""
import os

GLOBAL_CACHE = {}


def greet(name):
    # BUG: misspelled variable -> NameError at runtime
    return f"Hello, {nmae}!"


def is_ready(flag):
    # BUG: assignment instead of comparison (syntax-level logic error)
    if flag = "ready":
        return True
    return False


def max_of(a, b):
    # BUG: wrong comparison returns the smaller value
    if a < b:
        return a
    return b


def read_config(path):
    # BUG: file handle never closed -> fd/resource leak
    f = open(path, encoding="utf-8")
    data = f.read()
    return data