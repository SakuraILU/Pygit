import os

from utils import bread, bwrite, is_hexdigits


class Head():
    def __init__(self, repo_path):
        self.__repo_path = repo_path
        self.__path = os.path.join(repo_path, ".git", "HEAD")
        refed_path = bread(self.__path).decode()

        self.__obj = None
        if not is_hexdigits(refed_path):
            brh_name = os.path.basename(refed_path)
            self.__obj = Branch(brh_name, repo_path)
        else:
            self.__obj = refed_path

    def move_forward(self, sha1):
        if self.is_ref_branch():
            self.__obj.set_sha1(sha1)
        elif self.is_ref_sha1():
            self.ref_to(sha1)
        else:
            assert False, "shouldn't reach here"

    def is_ref_branch(self):
        return isinstance(self.__obj, Branch)

    def is_ref_sha1(self):
        return isinstance(self.__obj, str)

    def ref_to(self, obj):
        self.__obj = obj
        if self.is_ref_sha1():
            bwrite(self.__path, self.__obj.encode())
        elif self.is_ref_branch():
            bwrite(self.__path, self.__obj.get_full_name().encode())

    def get_sha1(self):
        return self.__obj.get_sha1() if self.is_ref_branch() else self.__obj

    def get_name(self):
        assert self.is_ref_branch(), "doesn't ref to a branch"
        return self.__obj.get_name()


class Branch():
    def __init__(self, *args, **kwargs):
        if (len(args)) + (len(kwargs)) == 2:
            self.build_from_bytes(*args, **kwargs)
        elif (len(args)) + (len(kwargs)) == 3:
            self.build_from_memory(*args, **kwargs)
        else:
            assert False, "invalid construction, accepted construction parameters:\
                                    \n\t1. (name, sha1, repo_path)\
                                    \n\t2. (bytes, repo_path)"

    def build_from_bytes(self, name, repo_path):
        self.__path = os.path.join(repo_path, ".git", "refs", "heads", name)
        assert os.path.exists(self.__path), f"branch {name} not exisit"
        self.__name = name
        self.__sha1 = bread(self.__path).decode()
        assert self.__sha1 != "", f"branch {name} is empty"

    def build_from_memory(self, name, sha1, repo_path):
        self.__path = os.path.join(repo_path, ".git", "refs", "heads", name)
        self.__name = name
        self.__sha1 = sha1
        self.__set_persist_sha1(self.__sha1)

    def __set_persist_sha1(self, sha1):
        self.__sha1 = sha1
        bwrite(self.__path, sha1.encode())

    def get_name(self):
        return self.__name

    def get_full_name(self):
        return "/" + os.path.join("refs", "heads", self.__name)

    def get_sha1(self):
        return self.__sha1

    @classmethod
    def get_branches(cls, repo_path):
        brhes = dict()
        brh_dir = os.path.join(repo_path, ".git", "refs", "heads")
        for name in os.listdir(brh_dir):
            branch = Branch(name, repo_path)
            brhes[branch.get_name()] = branch.get_sha1()
        return brhes
