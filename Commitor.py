import os
import stat
import subprocess

from collections import namedtuple
import textwrap

from utils import bread, bwrite
from Commit import Commit
from Tree import Tree
from Object import Object


class Commitor():
    Branch = namedtuple("Branch", ["name", "sha1"])

    def __init__(self, repo_path):
        self.__repo_path = repo_path
        self.__head_ref_path = os.path.join(self.__repo_path, ".git", "HEAD")
        self.__head_path = os.path.join(
            self.__repo_path, ".git", bread(self.__head_ref_path).decode()[1:])
        curbrh_name = os.path.basename(self.__head_path)
        curbrh_sha1 = bread(self.__head_path).decode()
        assert len(curbrh_sha1) == 0 or len(
            curbrh_sha1) == 20, "invalid length of head hash number"
        self.__curbrh = self.Branch(curbrh_name, curbrh_sha1)

    def commit(self, ientries, msg):
        root = self.__build_tree(ientries)

        sha1 = self.__write_tree(root)
        commit = Commit(sha1, [self.__curbrh.sha1] if len(
            self.__curbrh.sha1) == 20 else [], msg)

        obj = Object(commit, self.__repo_path)
        sha1 = obj.hash_object()
        print(f"commited to master {sha1}")
        self.set_curbrh_sha1(sha1)

    def __build_tree(self, ientries):
        root_node = dict()
        for entry in ientries:
            paths = entry.getpath().split(os.path.sep)
            cur_node = root_node
            for path in paths[:-1]:
                if path not in cur_node:
                    # print("add dir", path)
                    cur_node[path] = {}
                cur_node = cur_node[path]
            # print("add entry", paths[-1])
            cur_node[paths[-1]] = entry

        return root_node

    def __write_tree(self, node):
        tree = Tree()
        for path, node_or_entry in node.items():
            if (isinstance(node_or_entry, dict)):
                # print("visit dir path", path, "goto ", node_or_entry)
                sha1 = self.__write_tree(node_or_entry)
                tree.add_tentry(stat.S_IFDIR, path, sha1)
            else:
                # print("visit leaf path", path)
                tree.add_tentry(node_or_entry.getmode(),
                                path, node_or_entry.getsha1())
        # print(tree)
        obj = Object(tree, self.__repo_path)
        sha1 = obj.hash_object()
        return sha1

    def set_curbrh_sha1(self, sha1):
        bwrite(self.__head_path, sha1.encode())

    def get_curbrh_sha1(self):
        return self.__curbrh.sha1

    def __get_commit_by_name(self):
        pass

    def log(self):
        curbrh_sha1 = self.__curbrh.sha1
        out = ""
        while True:
            obj = Object(curbrh_sha1, self.__repo_path)
            assert obj.iscommit(), "not a commit..."
            commit = obj.getrawobj()

            parent_sha1s = commit.get_parent_sha1s()
            assert len(parent_sha1s) == 1 or len(
                parent_sha1s) == 0, "only support a linear commit history..."

            commit_msg = f"* \033[33mcommit {curbrh_sha1}\n" + \
                str(commit) + "\n"
            if len(parent_sha1s) == 0:
                out += textwrap.indent(commit_msg,
                                       "  ", lambda line: line[0] != "*")
                break
            else:
                out += textwrap.indent(commit_msg,
                                       "\033[31m| \033[0m", lambda line: line[0] != "*")

                curbrh_sha1 = parent_sha1s[0]
                out += "\033[31m|\n\033[31m|\n"

        pless = subprocess.Popen("less", shell=True, stdin=subprocess.PIPE)
        pless.communicate(input=out.encode())
