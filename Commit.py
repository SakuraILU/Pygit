import time
import textwrap


class Commit():
    __author = "SakuraILU"
    __email = "lkyhaq@gmail.com"

    def __init__(self, *args, **kwargs):
        self.__tree_sha1 = None
        self.__parent_sha1s = []
        self.__msg = None
        self.__timesample = None
        self.__zone_offset = None

        if (len(args)) + (len(kwargs)) == 3:
            self.build_from_memory(*args, **kwargs)
        elif (len(args)) + (len(kwargs)) == 1:
            self.build_from_bytes(*args, **kwargs)
        else:
            assert False, "invalid construction, accepted construction parameters:\
                                    \n\t1. (tree_sha1, parent_sha1, msg)\
                                    \n\t2. (bytes)"

    def build_from_memory(self, tree_sha1, parent_sha1s, msg):
        self.__tree_sha1 = tree_sha1
        self.__parent_sha1s = parent_sha1s
        self.__msg = msg

    def build_from_bytes(self, cdata):
        cdata = cdata.decode()
        lines = cdata.splitlines()
        for line in lines:
            if line == "":
                break
            key, value = line.split(maxsplit=1)
            if key == "tree":
                assert len(
                    self.__parent_sha1s) == 0, "The tree keyword does not appear before the parent keyword"
                self.__tree_sha1 = value
            elif key == "parent":
                self.__parent_sha1s.append(value)
            elif key == "author":
                _, _, self.__timesample, self.__zone_offset = value.split()
                self.__timesample = float(self.__timesample)
                self.__zone_offset = int(self.__zone_offset)
            elif key == "committer":
                pass
            else:
                assert False, "invalid key, shouldn't reach here..."

        # tree, parents, author, commiter, [msg...]
        self.__msg = "".join(lines[1 + len(self.__parent_sha1s) + 2:])

    def serialization(self):
        timestamp = int(time.mktime(time.localtime()))
        utc_offset = -time.timezone
        author_time = '{} {}{:02}{:02}'.format(
            timestamp,
            '+' if utc_offset > 0 else '-',
            abs(utc_offset) // 3600,
            (abs(utc_offset) // 60) % 60)

        content = f"tree {self.__tree_sha1}\n"
        for parent_sha1 in self.__parent_sha1s:
            content += f"parent {parent_sha1}\n"
        content += f"author {self.__author} <{self.__email}> {author_time}\n"
        content += f"committer {self.__author} <{self.__email}> {author_time}\n"
        content += f"\n"
        content += self.__msg

        return content.encode()

    def get_parent_sha1s(self):
        return self.__parent_sha1s

    def __str__(self):
        out = f"tree:   {self.__tree_sha1}\n"
        for parent_sha1 in self.__parent_sha1s:
            out += f"parent: {parent_sha1}\n"
        out += f"Author: {self.__author} <{self.__email}>\n"
        out += f"Date:   {time.asctime(time.localtime(self.__timesample))} {self.__zone_offset}\n"
        out += f"\n"
        out += textwrap.indent(self.__msg, "    ")
        return out
