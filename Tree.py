import stat


class Tree():

    class TreeEntry():
        def __init__(self, *args, **kwargs):
            if (len(args)) + (len(kwargs)) == 3:
                self.build_from_memory(*args, **kwargs)
            elif (len(args)) + (len(kwargs)) == 1:
                self.build_from_bytes(*args, **kwargs)
            else:
                assert False, "invalid construction, accepted construction parameters:\
                                \n\t1. (mode, path, sha1)\
                                \n\t2. (bytes)"

            self.__blen = 0

        def build_from_memory(self, mode, path, sha1):
            self.__mode = mode
            self.__path = path
            self.__sha1 = sha1

        def build_from_bytes(self, tdata):
            mode, tdata = tdata.split(b" ", maxsplit=1)
            self.__mode = int(mode, 8)  # mode is stored as a octal str number

            path, tdata = tdata.split(b"\x00", maxsplit=1)
            self.__path = path.decode()

            self.__sha1 = tdata[:20].decode()

        def serialization(self):
            return f"{self.__mode:o} {self.__path}\x00{self.__sha1}".encode()

        def getbytelen(self):
            if self.__blen == 0:
                self.__blen = len(self.serialization())

            return self.__blen

        def getmode(self):
            return self.__mode

        def getpath(self):
            return self.__path

        def getsha1(self):
            return self.__sha1

        def gettypename(self):
            if stat.S_ISDIR(self.__mode):
                return "tree"
            else:
                return "blob"

    def __init__(self, *args, **kwargs):
        self.__tentries = {}

        if (len(args)) + (len(kwargs)) == 1:
            self.build_from_bytes(*args, **kwargs)
        elif (len(args)) + (len(kwargs)) == 0:
            return
        else:
            assert False, "invalid invalid construction, accepted construction parameters:\
                            \n\t1. ()\
                            \n\t2. (bytes)"

    def build_from_bytes(self, tdata):
        blen = len(tdata)
        while blen > 0:
            entry = self.TreeEntry(tdata)
            self.__tentries[entry.getpath()] = entry
            tdata = tdata[entry.getbytelen():]

            blen -= entry.getbytelen()

    def add_tentry(self, mode, path, sha1):
        self.__tentries[path] = self.TreeEntry(mode, path, sha1)

    def get_tentries(self):
        return list(self.__tentries.values())

    def serialization(self):
        btentries = []
        for entry in self.__tentries.values():
            btentries.append(entry.serialization())
        return b"".join(btentries)

    def __str__(self):
        out = ""
        for entry in self.__tentries.values():
            out += f"{entry.getmode():o} {entry.gettypename()} {entry.getsha1()}\t{entry.getpath()}\n"
        return out
