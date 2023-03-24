import argparse
import enum
import hashlib
from collections import namedtuple
import struct

import os
import zlib

git_version = 2

git_repo_path = ""


class ObjType(enum.IntEnum):
    COMMIT = 1
    TREE = 2
    BLOB = 3

    def getname(enum):
        if enum == ObjType.COMMIT:
            return "commit"
        elif enum == ObjType.TREE:
            return "tree"
        elif enum == ObjType.BLOB:
            return "blob"
        else:
            assert False, "unsupported type"


class CatMode(enum.IntEnum):
    INVALID = 0
    TYPE = 1
    SIZE = 2
    PRETTY = 3
    COMMIT = 4
    TREE = 5
    BLOB = 6


IndexEntry = namedtuple("IndexEntry",
                        "ctime_s \
                        ctime_ns \
                        mtime_s \
                        mtime_ns \
                        dev \
                        ino \
                        mode \
                        uid \
                        gid \
                        size \
                        sha1 \
                        flags \
                        path "
                        )


def bwrite(file, data):
    with open(file, "wb") as f:
        f.write(data)


def bread(file):
    with open(file, "rb") as f:
        data = f.read()
    return data


def init(repo_path):
    git_repo_path = repo_path

    os.mkdir(repo_path)
    git_path = os.path.join(repo_path, ".git")
    os.mkdir(git_path)
    git_dirs = ["objects", "refs", "refs/heads"]
    for dir in git_dirs:
        os.mkdir(os.path.join(git_path, dir))
    head_path = os.path.join(git_path, "HEAD")
    bwrite(head_path, os.path.join("refs", "heads", "master"))


def add(paths):
    # remove repeted path...converted list to set
    paths = set(paths)
    # convert paths to standard relative path to the repository
    paths = [os.path.relpath(path, git_repo_path) for path in paths]

    index_path = os.path.join(".git", "index")
    assert os.path.exists(index_path)

    ientries = []
    oldientries = read_index()

    for entry in oldientries:
        if entry.path not in paths:
            ientries.append(entry)

    for path in paths:
        data = bread(path)
        sha1 = hash_object(ObjType.BLOB, data)
        fstat = os.stat(path)
        ientry = IndexEntry(ctime_s=fstat.st_ctime, ctime_ns=fstat.st_ctime,
                            mtime_s=fstat.st_mtime, mtime_ns=fstat.st_mtime_ns,
                            dev=fstat.st_dev, ino=fstat.st_ino,
                            mode=fstat.st_mode, uid=fstat.st_uid, gid=fstat.st_gid,
                            size=fstat.st_size,
                            sha1=sha1, flags=max(len(path), 0xFFF), path=path)
        ientries.append(ientry)

    ientries.sort(key=lambda elem: len(elem.path))

    # print(ientries)
    write_index(ientries)


def ls_file(stage):
    ientries = read_index()
    for ientry in ientries:
        out = ""
        if stage:
            out += f"{ientry.mode:o} {ientry.sha1} {ientry.flags >> 12}\t\t"
        out += ientry.path
        print(out)


def status():
    fchanged, fcreate, fdelete = diff_working2index()

    for path in fchanged:
        print(f"modified:\t{path}")
    print("")
    for path in fcreate:
        print(f"new:\t\t{path}")
    print("")
    for path in fdelete:
        print(f"deleted: \t{path}")


def diff_working2index():
    ls = os.walk(".")
    fpaths = set()
    for root, dirs, files in ls:
        if (root == '.'):
            dirs.remove(".git")
        cur_files = {os.path.relpath(os.path.join(
            root, file), git_repo_path) for file in files}
        fpaths.update(cur_files)

    ientry_map = {entry.path: entry.sha1 for entry in read_index()}
    ientry_paths = set(ientry_map.keys())

    fcreate = fpaths - ientry_paths
    fdelete = ientry_paths - fpaths

    fchanged = set()
    for path in fpaths.intersection(ientry_map):
        data = bread(path)
        if hash_object(ObjType.BLOB, data, write=False) != ientry_map[path]:
            fchanged.add(path)

    return fchanged, fcreate, fdelete


def cat_file(mode, sha1_prefix):
    assert len(
        sha1_prefix) >= 2, "the length of hash number must be greater or equal to 2"

    dirname = os.path.join(".git", "objects", sha1_prefix[:2])
    assert os.path.exists(dirname), f"object dir {dirname} dosen't exists"

    files = os.listdir(dirname)
    obj_file = ""
    if len(sha1_prefix) == 2:
        assert len(files) == 1, "multiple or none objects matched"
        obj_file = files[0]
    else:
        for file in files:
            if file.startswith(sha1_prefix[2:]):
                obj_file = os.path.join(dirname, file)
                break

    data = zlib.decompress(bread(obj_file)).decode()
    obj_type, data = data.split(" ", maxsplit=1)
    obj_type = int(obj_type)
    data_len, content = data.split("\x00", maxsplit=1)
    data_len = int(data_len)
    assert int(data_len) == len(
        content), f"the length of the content {data_len} is inconsistent with the length property in header {len(content)}, something goes wrong"

    if (mode == CatMode.TYPE):
        print(ObjType.getname(obj_type))
    elif (mode == CatMode.SIZE):
        print(data_len)
    elif (mode == CatMode.PRETTY):
        assert obj_type == ObjType.BLOB, "only support blob..."
        print(content)
    elif (mode == CatMode.BLOB):
        assert obj_type == ObjType.BLOB, f"object type is not blob..."
        print(content)
    else:
        assert False, "only support blob..."


def write_index(ientries):
    index_path = os.path.join(".git", "index")
    assert os.path.exists(index_path)

    header_len = 62
    bientries = []
    for entry in ientries:
        bientry = struct.pack('!ffffLLLLLL20sH', entry.ctime_s, entry.ctime_ns, entry.mtime_s, entry.mtime_ns,
                              entry.dev, entry.ino, entry.mode, entry.uid, entry.gid, entry.size, entry.sha1.encode(), entry.flags)
        # 8-byte align (padding with \x00)
        len_align = (header_len + len(entry.path) + 8) & (~0b111)
        bientry = (bientry + entry.path.encode() + b"\x00" *
                   (len_align - header_len - len(entry.path)))
        bientries.append(bientry)

    header = struct.pack("!4sLL", b"DIRC", git_version, len(bientries))
    idata = header + b"".join(bientries)
    idata = idata + hashlib.sha1(idata).hexdigest().encode()
    bwrite(os.path.join(".git", "index"), idata)


def read_index():
    ientries = []

    index_path = os.path.join(".git", "index")
    assert os.path.exists(index_path), "index doesn't exists"
    # if (not os.path.exists(index_path)):
    #     return ientries

    idata = bread(index_path)
    if len(idata) == 0:
        return ientries

    assert len(idata) > 12, "index header is imcompleted"
    magic, version, ientry_len = struct.unpack("!4sLL", idata[:12])
    idata = idata[12:]

    assert magic == b"DIRC", "magic check error"
    assert version == git_version, "git version check error"

    for i in range(ientry_len):
        assert len(idata) > 62, "the index entry is incomplete"
        ctime_s, ctime_ns, mtime_s, mtime_ns, dev, ino, mode, uid, gid,  size, sha1, flags = struct.unpack(
            '!ffffLLLLLL20sH', idata[:62])
        idata = idata[62:]
        path_len = idata.index(b'\x00')
        padding_len = ((62 + path_len + 8) & (~0b111)) - (62 + path_len)
        path = idata[:path_len]
        idata = idata[path_len + padding_len:]

        ientries.append(IndexEntry(ctime_s, ctime_ns, mtime_s, mtime_ns,
                                   dev, ino, mode, uid, gid,  size, sha1.decode(), flags, path.decode()))
    return ientries


def hash_object(obj_type, data, write=True):
    assert isinstance(data, bytes), "data hashed must be bytes"

    header = f"{obj_type} {len(data)}\x00".encode()
    obj = (header + data)
    sha1 = hashlib.sha1(obj).hexdigest()

    if write:
        obj_path = os.path.join('.git', 'objects', sha1[:2], sha1[2:])
        if (not os.path.exists(obj_path)):
            os.makedirs(os.path.dirname(obj_path))
            bwrite(obj_path, zlib.compress(obj))

    return sha1[:20]
    # print(header)


def parse_cmd():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command")
    init_cmd = subparsers.add_parser("init", help='initialize a new repo')
    init_cmd.add_argument(
        dest="path", nargs=1, help="Create an empty Git repository or reinitialize an existing one")

    hashobj_cmd = subparsers.add_parser(
        "hash-object", help="Compute object ID and optionally creates a blob from a file")
    hashobj_cmd.add_argument(
        "-t", "--type", choices=["blob"], default="blob", dest="type", help="Specify the type (default: \"blob\").")
    hashobj_cmd.add_argument(
        "--path", dest="path", help="Create an empty Git repository or reinitialize an existing one")

    add_cmd = subparsers.add_parser(
        "add", help="Add file contents to the index")
    add_cmd.add_argument(dest="paths", nargs="+",
                         help="path(s) of files to add")
    lsfile_cmd = subparsers.add_parser(
        "ls-file", help="List all the stage files")
    lsfile_cmd.add_argument("-s", "--stage", action="store_true", dest="stage",
                            help="Show staged contents' mode bits, object name and stage number in the output")

    status_cmd = subparsers.add_parser(
        "status", help="Show the working tree status")

    catfile_cmd = subparsers.add_parser(
        "cat-file", help="Show changes between commits, commit and working tree, etc")
    catfile_cmd.add_argument("-t", action="store_true",
                             dest="type", help="show object type")
    catfile_cmd.add_argument("-s", action="store_true",
                             dest="size", help="show object size")
    catfile_cmd.add_argument("-p", action="store_true",
                             dest="pretty", help="pretty-print object's content")
    catfile_cmd.add_argument(choices=["blob"], nargs="?", dest="mode",
                             help="The name (complete or prefix of the hash number) of the object to show")
    catfile_cmd.add_argument(dest="sha1_prefix",
                             help="Specify the object type (default: \"blob\").")
    return parser.parse_args()


if __name__ == "__main__":

    args = parse_cmd()
    if args.command == "init":
        init(args.path)
    elif args.command == "hash-object":
        data = bread(args.path)
        hash_object(ObjType.BLOB, data)
    elif args.command == "add":
        add(args.paths)
    elif args.command == "ls-file":
        ls_file(args.stage)
    elif args.command == "status":
        status()
    elif args.command == "cat-file":
        mode = CatMode.INVALID
        if args.type:
            mode = CatMode.TYPE
        elif args.size:
            mode = CatMode.SIZE
        elif args.pretty:
            mode = CatMode.PRETTY

        assert not (mode != CatMode.INVALID and
                    args.mode is not None), "parameter conflicts, mode shouldn't goes with other parameters"

        if args.mode == "commit":
            mode = CatMode.COMMIT
        elif args.mode == "tree":
            mode = CatMode.TREE
        elif args.mode == "blob":
            mode = CatMode.BLOB

        cat_file(mode, args.sha1_prefix)
