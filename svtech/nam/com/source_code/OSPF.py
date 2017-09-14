class OSPF:
    hostname = ""

    def __init__(self, name, vrf_name, nw_area, passive):
        self.name = name
        self.vrf_name = vrf_name
        self.nw_area = nw_area
        self.passive = passive