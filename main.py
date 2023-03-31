import os
import struct
import stat
import subprocess
import tempfile

from utils import bread, bwrite
from Index import Index
from ParseCmd import parse_cmd
import difflib
import zlib
import enum
import hashlib

from Object import Object
from Tree import Tree
from Blob import Blob
from Commit import Commit
from Commitor import Commitor
from Ref import Branch, Head
from utils import is_hexdigits, ColorEscape, can_cvt2str


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

    __editor = "vim"

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
        for git_dir in git_dirs:
            os.mkdir(os.path.join(git_path, git_dir))
        head_path = os.path.join(git_path, "HEAD")
        bwrite(head_path, os.path.join(
            "refs", "heads", "master").encode())  # HEAD
        # master branch
        os.mknod(os.path.join(git_path, "refs", "heads", "master"))
        os.mknod(os.path.join(git_path, "index"))  # index

    def add(self, paths):
        # remove repeted path...converted list to set
        paths = set(paths)
        for path in paths.copy():
            if os.path.isdir(path):
                paths.remove(path)
                paths.update(self.__files_under_dir(path))

        for path in paths:
            self.__index.add_ientry(path)

        self.__index.write_index()

    def ls_file(self, stage):
        if stage:
            print(self.__index)
        else:
            ientries = self.__index.get_ientries()
            for ientry in ientries:
                print(ientry.getpath())

    def status(self):
        fchanged, fcreate, fdelete = self.__diff_working2index()
        for path in fchanged:
            print(f"modified: \t{path}")
        if len(fchanged) != 0:
            print("")

        for path in fcreate:
            print(f"untracked:\t{path}")
        if len(fcreate) != 0:
            print("")

        for path in fdelete:
            print(f"deleted:  \t{path}")

    def diff(self):
        fchanged, _, _ = self.__diff_working2index()

        ientry_map = {ientry.getpath(): ientry.getsha1()
                      for ientry in self.__index.get_ientries()}

        for path in fchanged:
            file_data = bread(os.path.join(self.__repo_path, path))
            # print(wrk_data)
            obj = Object(ientry_map[path], self.__repo_path)
            assert obj.isblob(), "only support blob diff"
            blob = obj.getrawobj()
            if not blob.can_cvt2str() or not can_cvt2str(file_data):
                print(
                    f"\n{ColorEscape.red}{path} is modified, but is not a txt file, can not to be diffed{ColorEscape.white}\n")
                continue
            blob_data = str(blob)
            file_data = file_data.decode()
            file_lines = file_data.splitlines()
            blob_lines = blob_data.splitlines()

            for diff_line in difflib.unified_diff(file_lines, blob_lines, os.path.join("a", path), os.path.join("b", path)):
                print(diff_line)

    def __diff_working2index(self):
        fpaths = self.__files_under_dir(self.__repo_path)

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

    # relpaths from repo_path...
    def __files_under_dir(self, root_dir):
        fpaths = set()
        for root, dirs, files in os.walk(root_dir):
            if (os.path.realpath(root) == self.__repo_path):
                dirs.remove(".git")

            files = {os.path.relpath(os.path.join(
                root, file), self.__repo_path) for file in files}
            # TODO: can ignore some files here...
            fpaths.update(files)
        return fpaths

    def __clean_empty_dirs_under_dir(self, root_dir):
        for root, dirs, files in os.walk(root_dir):
            if (os.path.realpath(root) == self.__repo_path):
                # print(os.path.realpath(root), "remove .git")
                dirs.remove(".git")

            for sub_dir in dirs:
                self.__clean_empty_dirs_under_dir(
                    os.path.join(root_dir, sub_dir)
                )

            if len(os.listdir(root)) == 0:
                if os.path.islink(root):
                    os.unlink(root)
                elif os.path.isdir(root):
                    os.rmdir(root)
                else:
                    assert False, "not a dir or symlink->dir"

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
            assert obj.isblob(), "object type is not blob..."
            blob = obj.getrawobj()
            if blob.can_cvt2str():
                print(blob)
            else:
                print(blob.serialization())
        elif (mode == CatMode.TREE):
            assert obj.istree(), "object type is not tree..."
            print(obj.getrawobj())
        elif (mode == CatMode.COMMIT):
            assert obj.iscommit(), "object type is not commit..."
            print(obj.getrawobj())
        else:
            assert False, "only support blob..."

    def commit(self, msg):
        commior = Commitor(self.__repo_path)
        if msg == None:
            try:
                f = tempfile.NamedTemporaryFile()
                pvim = subprocess.Popen(
                    f"{self.__editor} {f.name}", shell=True)
                pvim.wait()
                msg = bread(f.name).decode()
            finally:
                f.close()

        commior.commit(self.__index, msg)

    def log(self):
        commitor = Commitor(self.__repo_path)
        commitor.log()

    def checkout(self, name, index=False):
        if index:
            if not name:
                self.__remove_tracted_files()
                self.__clean_empty_dirs_under_dir(self.__repo_path)
                for entry in self.__index.get_ientries():
                    if not stat.S_ISDIR(entry.getmode()):
                        self.__restore_index2working(entry.getpath())
            else:
                self.__restore_index2working(name)
        else:
            self.__remove_tracted_files()
            head = Head(self.__repo_path)
            # print(name.isnumeric() and len(name) >= 2)
            sha1 = None
            if is_hexdigits(name) and len(name) >= 2:
                sha1_prefix = name
                obj = Object(sha1_prefix, self.__repo_path)
                sha1 = obj.getsha1()
                print(f"set hash {sha1}")
                head.ref_to(sha1)
            elif not is_hexdigits(name):
                print("checkout ", name)
                head.ref_to(Branch(name, self.__repo_path))
                sha1 = head.get_sha1()
            else:
                assert False, "invalid head"
            commit = Object(head.get_sha1(), self.__repo_path).getrawobj()

            self.__index.reset_to_commit(commit)
            self.checkout(name=None, index=True)

    def __restore_index2working(self, path):
        bdata = self.__index.get_bytedata(path)
        path = os.path.join(self.__repo_path, path)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        bwrite(path, bdata)

    def __remove_tracted_files(self):
        _, fcreate, _ = self.__diff_working2index()
        for file in self.__files_under_dir(self.__repo_path):
            if file not in fcreate:
                os.unlink(os.path.join(self.__repo_path, file))

    def branch(self, name, ls=False):
        if ls:
            brhes = Branch.get_branches(self.__repo_path)
            for name, sha1 in brhes.items():
                print(
                    f"{ColorEscape.green}{name}{ColorEscape.white}\t{sha1}")
        else:
            head = Head(self.__repo_path)
            sha1 = head.get_sha1()
            brh = Branch(name, sha1, self.__repo_path)
            print(f"create a new branch {name} at {sha1}")

    def rm(self, paths, index=False):
        paths = set(paths)
        for path in paths.copy():
            if os.path.isdir(os.path.join(self.__repo_path, path)):
                paths.remove(path)
                paths.update(self.__files_under_dir(path))

        for path in paths:
            self.__index.remove_ientry(path)
            if not index:
                os.unlink(os.path.join(self.__repo_path, path))
                self.__clean_empty_dirs_under_dir(self.__repo_path)
        self.__index.write_index()


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
        repo.commit(args.msg)
    elif args.command == "log":
        repo.log()
    elif args.command == "checkout":
        repo.checkout(args.names, args.index)
    elif args.command == "branch":
        if not args.ls:
            assert args.name != None, "no name specified"
        repo.branch(args.name, args.ls)
    elif args.command == "rm":
        repo.rm(args.paths, args.index)
    else:
        assert False, "invalid command"
