import os

from collections import namedtuple
import struct

import hashlib

from utils import bread, bwrite
from Object import Object
from Blob import Blob


class Index():

    class IndexEntry():
        def __init__(self, *args, **kwargs):
            self.__header_len = 62

            self.__blen = 0

            if (len(args)) + (len(kwargs)) == 13:
                self.build_from_memory(*args, **kwargs)
            elif (len(args)) + (len(kwargs)) == 1:
                self.build_from_bytes(*args, **kwargs)
            else:
                assert False, "invalid construction, accepted construction parameters:\
                                    \n\t1. (ctime_s, ctime_ns, mtime_s, mtime_ns,dev, ino, mode, uid, gid,  size, sha1, flags, path)\
                                    \n\t2. (bytes)"

        def build_from_memory(self, ctime_s, ctime_ns, mtime_s, mtime_ns,
                              dev, ino, mode, uid, gid,  size, sha1, flags, path):
            self.__ctime_s = ctime_s
            self.__ctime_ns = ctime_ns
            self.__mtime_s = mtime_s
            self.__mtime_ns = mtime_ns
            self.__dev = dev
            self.__ino = ino
            self.__mode = mode
            self.__uid = uid
            self.__gid = gid
            self.__size = size
            self.__sha1 = sha1
            self.__flags = flags
            self.__path = path

        def build_from_bytes(self, idata):
            assert len(idata) > 62, "the index entry is incomplete"

            (self.__ctime_s, self.__ctime_ns, self.__mtime_s, self.__mtime_ns,
             self.__dev, self.__ino,
             self.__mode, self.__uid, self.__gid,
             self.__size,
             self.__sha1, self.__flags) = struct.unpack(
                '!ffffLLLLLL20sH', idata[:62])
            self.__sha1 = self.__sha1.decode()
            idata = idata[self.__header_len:]

            path_len = idata.index(b'\x00')
            padding_len = ((self.__header_len + path_len + 8) &
                           (~0b111)) - (self.__header_len + path_len)
            self.__path = idata[:path_len].decode()

            idata = idata[path_len + padding_len:]

            self.__blen = self.__header_len + path_len + padding_len

        def getbytelen(self):
            if (self.__blen == 0):
                self.__blen = len(self.serialization())

            return self.__blen

        def serialization(self):
            bientry = struct.pack('!ffffLLLLLL20sH',
                                  self.__ctime_s, self.__ctime_ns, self.__mtime_s, self.__mtime_ns,
                                  self.__dev, self.__ino,
                                  self.__mode, self.__uid, self.__gid,
                                  self.__size,
                                  self.__sha1.encode(), self.__flags)

            # 8-byte align (padding with \x00)
            len_align = (self.__header_len +
                         len(self.__path.encode()) + 8) & (~0b111)
            bientry = (bientry + self.__path.encode() + b"\x00" *
                       (len_align - self.__header_len - len(self.__path)))

            return bientry

        def getpath(self):
            return self.__path

        def getsha1(self):
            return self.__sha1

        def getmode(self):
            return self.__mode

        def getflags(self):
            return self.__flags

    __instance = None
    __init = False

    def __new__(cls, *args, **kwargs):
        if cls.__instance == None:
            cls.__instance = object.__new__(cls)
        return cls.__instance

    def __init__(self, repo_path, version):
        if self.__init:
            return
        self.__init = True

        self.__repo_path = repo_path
        self.__index_path = os.path.join(repo_path, ".git", "index")
        assert os.path.exists(self.__index_path), "index doesn't exists"

        self.__magic = b"DIRC"
        self.__version = version
        assert version == 2, "only support version 2"
        self.__header_len = 12

        self.__ientries = dict()
        self.read_index()

    def add_ientry(self, path):
        fstat = os.stat(path)
        data = bread(path)
        obj = Object(Blob(data), self.__repo_path)
        sha1 = obj.hash_object()

        # convert paths to standard relative path to the repository
        path = os.path.relpath(path, self.__repo_path)

        ientry = self.IndexEntry(ctime_s=fstat.st_ctime, ctime_ns=fstat.st_ctime,
                                 mtime_s=fstat.st_mtime, mtime_ns=fstat.st_mtime_ns,
                                 dev=fstat.st_dev, ino=fstat.st_ino,
                                 mode=fstat.st_mode, uid=fstat.st_uid, gid=fstat.st_gid,
                                 size=fstat.st_size,
                                 sha1=sha1, flags=max(len(path), 0xFFF), path=path)

        self.__ientries[path] = ientry
        sorted(self.__ientries.items())

    def get_ientries(self):
        return list(self.__ientries.values())

    def write_index(self):
        assert os.path.exists(self.__index_path), "index doesn't exist"

        bientries = []
        for entry in self.__ientries.values():
            bientries.append(entry.serialization())

        header = struct.pack("!4sLL", self.__magic,
                             self.__version, len(bientries))
        idata = header + b"".join(bientries)
        idata = idata + hashlib.sha1(idata).hexdigest().encode()
        bwrite(self.__index_path, idata)

    def read_index(self):
        assert os.path.exists(self.__index_path), "index doesn't exist"

        idata = bread(self.__index_path)
        if len(idata) == 0:
            return

        assert len(idata) > self.__header_len, "index header is imcompleted"
        magic, version, ientry_len = struct.unpack(
            "!4sLL", idata[:self.__header_len])
        idata = idata[self.__header_len:]

        assert magic == self.__magic, "magic check error"
        assert version == self.__version, "git version check error"

        for i in range(ientry_len):
            ientry = self.IndexEntry(idata)
            idata = idata[ientry.getbytelen():]

            self.__ientries[ientry.getpath()] = ientry

    def __str__(self):
        out = ""
        for ientry in self.__ientries.values():
            out += f"{ientry.getmode():o} {ientry.getsha1()} {ientry.getflags() >> 12}\t\t{ientry.getpath()}\n"

        return out[:-1]  # move the last '\n' char
