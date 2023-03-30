import os
import stat
import subprocess

from collections import namedtuple
import textwrap

from utils import bread, bwrite, ColorEscape
from Commit import Commit
from Tree import Tree
from Object import Object
from Ref import Head, Branch


class Commitor():
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
        self.__head = Head(repo_path)

    def commit(self, ientries, msg):
        root = self.__build_tree(ientries)

        sha1 = self.__write_tree(root)
        commit = Commit(sha1, [self.__head.get_sha1()] if len(
            self.__head.get_sha1()) == 20 else [], msg)

        obj = Object(commit, self.__repo_path)
        sha1 = obj.hash_object()
        print(f"commited to master {sha1}")
        self.__head.move_forward(sha1)

    def __build_tree(self, ientries):
        root_node = dict()
        cur_node = root_node
        for entry in ientries:
            print(entry.getpath())
            paths = entry.getpath().split(os.path.sep)
            for path in paths[:-1]:
                if path not in cur_node:
                    print("add dir", path)
                    cur_node[path] = {}
                cur_node = cur_node[path]
            print("add entry", paths[-1])
            cur_node[paths[-1]] = entry
            cur_node = root_node

        return root_node

    def __write_tree(self, node):
        tree = Tree()
        for path, node in node.items():
            # print(path, isinstance(node, dict))
            if (isinstance(node, dict)):
                print("visit dir path", path, "goto ", node)
                sha1 = self.__write_tree(node)
                tree.add_tentry(stat.S_IFDIR, path, sha1)
                print(f"leave dir {path}")
            else:
                print("visit leaf path", path)
                tree.add_tentry(node.getmode(),
                                path, node.getsha1())
        # print(tree)
        obj = Object(tree, self.__repo_path)
        sha1 = obj.hash_object()
        return sha1

    def read_tree(self, commit):
        tree = Object(commit.get_tree_sha1(), self.__repo_path).getrawobj()
        return self.__read_tree(tree, "")

    def __read_tree(self, tree, path):
        print(path)
        tentries = set()
        for tentry in tree.get_tentries():
            if (stat.S_ISDIR(tentry.getmode())):
                tree = Object(tentry.getsha1(), self.__repo_path).getrawobj()
                tentries.update(
                    self.__read_tree(
                        tree, os.path.join(path, tentry.getpath())
                    )
                )
            else:
                tentries.add(
                    Tree.TreeEntry(
                        tentry.getmode(),
                        os.path.join(path, tentry.getpath()),
                        tentry.getsha1()
                    )
                )
        return tentries

    def __get_commit_by_name(self):
        pass

    def log(self):
        brhes = Branch.get_branches(self.__repo_path)

        curbrh_sha1 = self.__head.get_sha1()

        out = ""
        brh_msg = f"{ColorEscape.cyan}HEAD"
        if self.__head.is_ref_branch():
            brh_msg += f" -> {ColorEscape.green}{self.__head.get_name()}"
            brhes.pop(self.__head.get_name())

        while True:
            obj = Object(curbrh_sha1, self.__repo_path)
            assert obj.iscommit(), "not a commit..."
            commit = obj.getrawobj()

            parent_sha1s = commit.get_parent_sha1s()
            assert len(parent_sha1s) == 1 or len(
                parent_sha1s) == 0, "only support a linear commit history..."

            for name, sha1 in brhes.copy().items():
                if sha1 == curbrh_sha1:
                    brh_msg += f", {name}"
                    brhes.pop(name)

            brh_msg = brh_msg.strip(" ,")
            if len(brh_msg) != 0:
                brh_msg = f"{ColorEscape.orange}({ColorEscape.green}" + \
                    brh_msg + f"{ColorEscape.orange})"

            commit_msg = f"* {ColorEscape.orange}commit {curbrh_sha1} " + brh_msg + "\n" + \
                str(commit) + "\n"
            if len(parent_sha1s) == 0:
                out += textwrap.indent(commit_msg,
                                       "  ", lambda line: line[0] != "*")
                break
            else:
                out += textwrap.indent(commit_msg,
                                       f"{ColorEscape.red}| {ColorEscape.white}", lambda line: line[0] != "*")

                curbrh_sha1 = parent_sha1s[0]
                out += f"{ColorEscape.red}|\n{ColorEscape.red}|\n"

            brh_msg = ""

        pless = subprocess.Popen("less", shell=True, stdin=subprocess.PIPE)
        pless.communicate(input=out.encode())
