import os

from utils import bread, bwrite, is_hexdigits


class Head():
    __instance = None
    __init = False

    def __new__(cls, *args, **kwargs):
        if cls.__instance == None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, repo_path):
        if self.__init:
            return
        self.__init = True

        self.__repo_path = repo_path
        self.__path = os.path.join(repo_path, ".git", "HEAD")
        refed_path = bread(self.__path).decode()

        self.__obj = None
        if not is_hexdigits(refed_path):
            brh_name = os.path.basename(refed_path)
            self.__obj = Branch(brh_name, repo_path)
        else:
            self.__obj = refed_path

    # move to commit (id: sha1) with branch if HEAD->branch, otherwise just move
    def move_with_branch(self, sha1):
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
        # sha1
        if isinstance(obj, str):
            self.__obj = obj
            bwrite(self.__path, self.__obj.encode())
        # branch
        elif isinstance(obj, Branch):
            self.__obj = obj
            bwrite(self.__path, self.__obj.get_full_name().encode())
        # tag...refer to the sha1 refered by this tag
        elif isinstance(obj, Tag):
            self.__obj = obj.get_sha1()
            bwrite(self.__path, self.__obj.encode())
        else:
            assert False, "invalid deference..."

    def get_sha1(self):
        if self.is_ref_branch():
            return self.__obj.get_sha1()
        elif self.is_ref_sha1():
            return self.__obj
        else:
            assert False, "invalid deference..."

    def get_name(self):
        assert self.is_ref_branch(), "ref to sha1..no name"
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
        # assert self.__sha1 != "", f"branch {name} is empty"

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

    def get_full_name(self):
        return "/" + os.path.join("refs", "heads", self.__name)

    def get_sha1(self):
        return self.__sha1

    @classmethod
    def is_branch(cls, name, repo_path):
        return name in cls.get_branches(repo_path).keys()

    @classmethod
    def get_branches(cls, repo_path):
        brhes = dict()
        brh_dir = os.path.join(repo_path, ".git", "refs", "heads")
        for name in os.listdir(brh_dir):
            branch = Branch(name, repo_path)
            brhes[branch.get_name()] = branch.get_sha1()
        return brhes

    @classmethod
    def remove(cls, name, repo_path):
        assert cls.is_branch(name, repo_path), f"{name} is not a branch name"
        brh_path = os.path.join(repo_path, ".git", "refs", "heads", name)
        os.unlink(brh_path)


class Tag():
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
        self.__path = os.path.join(repo_path, ".git", "refs", "tags", name)
        assert os.path.exists(self.__path), f"tag {name} not exisit"
        self.__name = name
        self.__sha1 = bread(self.__path).decode()
        # assert self.__sha1 != "", f"branch {name} is empty"

    def build_from_memory(self, name, sha1, repo_path):
        self.__path = os.path.join(repo_path, ".git", "refs", "tags", name)
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

    @classmethod
    def is_tag(cls, name, repo_path):
        return name in cls.get_tags(repo_path).keys()

    @classmethod
    def get_tags(cls, repo_path):
        tags = dict()
        tag_dir = os.path.join(repo_path, ".git", "refs", "tags")
        for name in os.listdir(tag_dir):
            tag = Tag(name, repo_path)
            tags[tag.get_name()] = tag.get_sha1()
        return tags

    @classmethod
    def remove(cls, name, repo_path):
        assert cls.is_tag(name, repo_path), f"{name} is not a branch name"
        tag_path = os.path.join(repo_path, ".git", "refs", "tags", name)
        os.unlink(tag_path)
