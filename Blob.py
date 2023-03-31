class Blob():
    def __init__(self, data):
        self.__data = data

        if isinstance(self.__data, str):
            self.__data = self.__data.encode()

    def serialization(self):
        return self.__data

    def getlen(self):
        return len(self.serialization())

    def can_cvt2str(self):
        try:
            self.__data.decode()
        except UnicodeDecodeError as e:
            return False
        return True

    def __str__(self):
        return self.__data.decode()
