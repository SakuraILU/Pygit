import os

import enum
import hashlib
import zlib

from utils import bread, bwrite

from Blob import Blob
from Tree import Tree
from Commit import Commit


class Object():

    class ObjType(enum.IntEnum):
        COMMIT = 1
        TREE = 2
        BLOB = 3

        @classmethod
        def getname(cls, enum):
            type2name = {cls.COMMIT: "commit",
                         cls.TREE: "tree", cls.BLOB: "blob"}
            if enum in type2name:
                return type2name[enum]
            else:
                assert False, "unsupported object type"

    def __init__(self, arg, repo_path):
        self.__objects_dir = os.path.join(repo_path, ".git", "objects")
        self.__sha1 = None

        if isinstance(arg, str):
            self.build_from_bytes(arg)
        else:
            self.build_from_memory(arg)

        self.__hashlen = 20

    def build_from_memory(self, raw_obj):
        self.__raw_obj = raw_obj

        self.__type = None
        if isinstance(raw_obj, Blob):
            self.__type = self.ObjType.BLOB
        elif isinstance(raw_obj, Tree):
            self.__type = self.ObjType.TREE
        elif isinstance(raw_obj, Commit):
            self.__type = self.ObjType.COMMIT
        else:
            assert False, "unsupported object type"

    def build_from_bytes(self, sha1_prefix):
        (self.__type, self.__len, content) = self.read_object(sha1_prefix)
        if self.isblob():
            self.__raw_obj = Blob(content)
        elif self.istree():
            self.__raw_obj = Tree(content)
        elif self.iscommit():
            self.__raw_obj = Commit(content)

    def getlen(self):
        return len(self.__raw_obj.serialization())

    def getrawobj(self):
        return self.__raw_obj

    def gettypename(self):
        return self.ObjType.getname(self.__type)

    def getsha1(self):
        if self.__sha1 == None:
            assert False, "not read from or persist into disk yet..."
        return self.__sha1

    def isblob(self):
        return self.ObjType.BLOB == self.__type

    def istree(self):
        return self.ObjType.TREE == self.__type

    def iscommit(self):
        return self.ObjType.COMMIT == self.__type

    def hash_object(self, write=True):
        header = f"{self.__type} {self.getlen()}\x00".encode()
        obj = header + self.__raw_obj.serialization()
        sha1 = hashlib.sha1(obj).hexdigest()[:self.__hashlen]

        if write:
            obj_path = os.path.join(self.__objects_dir, sha1[:2], sha1[2:])
            if (not os.path.exists(obj_path)):
                os.makedirs(os.path.dirname(obj_path), exist_ok=True)
                bwrite(obj_path, zlib.compress(obj))

        self.__sha1 = sha1[:20]

        return self.__sha1

    def read_object(self, sha1_prefix):
        obj_file = self.find_object(sha1_prefix)
        data = zlib.decompress(bread(obj_file))
        obj_type, data = data.split(b" ", maxsplit=1)
        obj_len, obj_content = data.split(b"\x00", maxsplit=1)
        assert int(obj_len) == len(
            obj_content), f"the length of the content {obj_len} is inconsistent with the length property in header {len(obj_content)}, something goes wrong"

        return int(obj_type), int(obj_len), obj_content

    def find_object(self, sha1_prefix):
        assert len(
            sha1_prefix) >= 2, "the length of hash number must be greater or equal to 2"

        dirname = os.path.join(self.__objects_dir, sha1_prefix[:2])
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

        self.__sha1 = obj_file[-21:-19] + obj_file[-18:]
        return obj_file
