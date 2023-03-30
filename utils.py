import os


class ColorEscape():
    red = "\033[31m"
    green = "\033[32m"
    orange = "\033[33m"
    blue = "\033[34m"
    magenta = "\033[35m"
    cyan = "\033[36m"
    white = "\033[37m"
    none = "\033[0m"


def bwrite(file, data):
    with open(file, "wb") as f:
        f.write(data)


def bread(file):
    with open(file, "rb") as f:
        data = f.read()
    return data


def is_hexdigits(s):
    return all(c in "0123456789abcdefABCDEF" for c in s)
