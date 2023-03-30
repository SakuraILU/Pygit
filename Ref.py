import os

from utils import bread, bwrite, is_hexdigits


class Head():
    def __init__(self, repo_path):
        self.__repo_path = repo_path
        self.__path = os.path.join(repo_path, ".git", "HEAD")
        refed_path = bread(self.__path).decode()

        self.__brh = None
        self.__commit_sha1 = None
        if not is_hexdigits(refed_path):
            brh_name = os.path.basename(refed_path)
            self.__brh = Branch(brh_name, repo_path)
        else:
            self.__commit_sha1 = refed_path

    def move_forward(self, sha1):
        if self.is_ref_branch():
            assert self.__commit_sha1 == None, "it shouldn't ref to sha1..."
            self.__brh.set_sha1(sha1)
        elif self.is_ref_sha1():
            assert self.__brh == None, "it shouldn't ref to branch..."
        else:
            assert False, "shouldn't reach here"

    def is_ref_branch(self):
        return self.__brh != None and self.__commit_sha1 == None

    def is_ref_sha1(self):
        return self.__commit_sha1 != None and self.__brh == None

    def ref_sha1(self, sha1):
        self.__brh = None
        self.__commit_sha1 = sha1
        bwrite(self.__path, self.__commit_sha1.encode())

    def ref_branch(self, name):
        self.__commit_sha1 = None
        self.__brh = Branch(name, self.__repo_path)

        self.__ref_path = os.path.join(
            self.__repo_path, "git", "refs", "heads", name)
        bwrite(self.__path, self.__ref_path.encode())

    def get_sha1(self):
        return self.__brh.get_sha1() if self.__brh != None else self.__commit_sha1

    def get_name(self):
        assert self.__commit_sha1 == None, "doesn't ref to a branch"
        return self.__brh.get_name()


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
        self.set_sha1(self.__sha1)

    def set_sha1(self, sha1):
        self.__sha1 = sha1
        bwrite(self.__path, sha1.encode())

    def get_name(self):
        return self.__name

    def get_sha1(self):
        return self.__sha1
