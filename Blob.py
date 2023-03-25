class Blob():
    def __init__(self, data):
        self.__data = data

        if isinstance(self.__data, bytes):
            self.__data = self.__data.decode()

    def serialization(self):
        return self.__data.encode()

    def getlen(self):
        return len(self.__data)

    def getdata(self):
        return self.__data

    def __str__(self):
        return self.__data
