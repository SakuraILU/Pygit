import enum
import hashlib

import struct
import os

import zlib
import difflib

from ParseCmd import parse_cmd
from Index import Index
from utils import bread, bwrite
from Object import Object
from Blob import Blob
from Tree import Tree


class CatMode(enum.IntEnum):
    INVALID = 0
    TYPE = 1
    SIZE = 2
    PRETTY = 3
    COMMIT = 4
    TREE = 5
    BLOB = 6


class GitRepo():
    __instance = None
    __init = False

    def __new__(cls, *args, **kwargs):
        if cls.__instance == None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self):
        if self.__init:
            return
        self.__init = True

        self.__version = 2

        self.__repo_path = None
        self.__index = None

    def init_repo_path(self):
        self.__repo_path = self.get_repo_path()
        self.__index = Index(self.__repo_path, self.__version)

    def get_repo_path(self):
        if self.__repo_path != None:
            return self.__repo_path

        curpath = os.path.realpath(".")

        while curpath != "/":
            gitpath = os.path.join(curpath, ".git")
            if os.path.isdir(gitpath):
                return curpath
            else:
                curpath = os.path.realpath(os.path.join(curpath, ".."))

        return None

    def init(self, repo_path):
        self.__repo_path = repo_path

        os.mkdir(self.__repo_path)
        git_path = os.path.join(self.__repo_path, ".git")
        os.mkdir(git_path)
        git_dirs = ["objects", "refs", "refs/heads"]
        for dir in git_dirs:
            os.mkdir(os.path.join(git_path, dir))
        head_path = os.path.join(git_path, "HEAD")
        bwrite(head_path, os.path.join("refs", "heads", "master"))
        bwrite(os.path.join(git_path, "index"), "")

    def add(self, paths):
        # remove repeted path...converted list to set
        paths = set(paths)

        for path in paths:
            self.__index.add_ientry(path)

        self.__index.write_index()

    def ls_file(self, stage):
        ientries = self.__index.get_ientries()
        for ientry in ientries:
            out = ""
            if stage:
                out += f"{ientry.getmode():o} {ientry.getsha1()} {ientry.getflags() >> 12}\t\t"
            out += ientry.getpath()
            print(out)

    def status(self):
        fchanged, fcreate, fdelete = self.__diff_working2index()

        for path in fchanged:
            print(f"modified:\t{path}")
        print("")
        for path in fcreate:
            print(f"new:\t\t{path}")
        print("")
        for path in fdelete:
            print(f"deleted: \t{path}")

    def diff(self):
        fchanged, _, _ = self.__diff_working2index()

        ientry_map = {ientry.getpath(): ientry.getsha1()
                      for ientry in self.__index.get_ientries()}

        for path in fchanged:
            wrk_data = bread(os.path.join(self.__repo_path, path)).decode()
            obj = Object(ientry_map[path], self.__repo_path)
            obj_data = obj.getrawobj().getdata()
            assert obj.isblob(), "only support blob diff"
            wrk_lines = wrk_data.splitlines()
            obj_lines = obj_data.splitlines()

            for diff_line in difflib.unified_diff(obj_lines, wrk_lines, os.path.join("a", path), os.path.join("b", path)):
                print(diff_line)

    def __diff_working2index(self):
        ls = os.walk(self.__repo_path)
        fpaths = set()
        for root, dirs, files in ls:
            if (root == self.__repo_path):
                dirs.remove(".git")
            cur_files = {os.path.relpath(os.path.join(
                root, file), self.__repo_path) for file in files}
            fpaths.update(cur_files)

        ientry_map = {entry.getpath(): entry.getsha1()
                      for entry in self.__index.get_ientries()}
        ientry_paths = set(ientry_map.keys())

        fcreate = fpaths - ientry_paths
        fdelete = ientry_paths - fpaths

        fchanged = set()
        for path in fpaths.intersection(ientry_map):
            data = bread(os.path.join(self.__repo_path, path))
            obj = Object(Blob(data), self.__repo_path)
            if obj.hash_object(write=False) != ientry_map[path]:
                fchanged.add(path)

        return fchanged, fcreate, fdelete

    def cat_file(self, mode, sha1_prefix):
        obj = Object(sha1_prefix, self.__repo_path)

        if (mode == CatMode.TYPE):
            print(obj.gettypename())
        elif (mode == CatMode.SIZE):
            print(obj.getlen())
        elif (mode == CatMode.PRETTY):
            assert obj_type == ObjType.BLOB, "only support blob..."
            print(obj.getrawobj())
        elif (mode == CatMode.BLOB):
            assert obj.isblob(), f"object type is not blob..."
            print(obj.getrawobj())
        elif (mode == CatMode.TREE):
            assert obj.istree(), f"object type is not blob..."
            print(obj.getrawobj())
        else:
            assert False, "only support blob..."

    def commit(self):
        tree = Tree()
        for entry in self.__index.get_ientries():
            tree.add_tentry(entry.getmode(), entry.getpath(), entry.getsha1())
        obj = Object(tree, self.__repo_path)
        print(obj.hash_object())


if __name__ == "__main__":
    repo = GitRepo()

    args = parse_cmd()
    if args.command == "init":
        repo.init(args.path)

    repo.init_repo_path()
    if args.command == "hash-object":
        data = bread(args.path)
        obj = Object(Blob(data), repo.get_repo_path())
        obj.hash_object()
    elif args.command == "add":
        repo.add(args.paths)
    elif args.command == "ls-files":
        repo.ls_file(args.stage)
    elif args.command == "status":
        repo.status()
    elif args.command == "cat-file":
        mode = CatMode.INVALID
        if args.type:
            mode = CatMode.TYPE
        if args.size:
            assert mode == CatMode.INVALID, "parameter conflicts, -t, -s, -p is incompatible with each other"
            mode = CatMode.SIZE
        if args.pretty:
            assert mode == CatMode.INVALID, "parameter conflicts, -t, -s, -p is incompatible with each other"
            mode = CatMode.PRETTY

        assert not (mode != CatMode.INVALID and
                    args.mode is not None), "parameter conflicts, mode is incompatible with other parameters"

        if args.mode == "commit":
            mode = CatMode.COMMIT
        elif args.mode == "tree":
            mode = CatMode.TREE
        elif args.mode == "blob":
            mode = CatMode.BLOB

        repo.cat_file(mode, args.sha1_prefix)

    elif args.command == "diff":
        repo.diff()
    elif args.command == "commit":
        repo.commit()
