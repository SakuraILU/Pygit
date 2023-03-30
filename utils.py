import os


def bwrite(file, data):
    with open(file, "wb") as f:
        f.write(data)


def bread(file):
    with open(file, "rb") as f:
        data = f.read()
    return data


def is_hexdigits(s):
    return all(c in "0123456789abcdefABCDEF" for c in s)
