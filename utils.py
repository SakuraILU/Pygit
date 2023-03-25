import os


def bwrite(file, data):
    with open(file, "wb") as f:
        f.write(data)


def bread(file):
    with open(file, "rb") as f:
        data = f.read()
    return data
