import IFL


class Utils:
    def __init__(self):
        pass

    @staticmethod
    def convert(x):
        interface_unit = IFL.INTERFACE_UNIT(x[0], x[1], "", "")
        interface_unit.ip_helper_list = x[2].split(' ')
        return interface_unit