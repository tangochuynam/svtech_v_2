class Path:
    hostname = ""

    def __init__(self, name, hostname, nh, index, type):
        self.name = name
        self.hostname = hostname
        self.nh = nh
        self.index = index
        self.type = type