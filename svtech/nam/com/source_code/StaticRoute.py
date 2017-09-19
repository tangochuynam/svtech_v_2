import MySQLdb
import ipaddress as ip

import Database


class NH_AD:
    def __init__(self, nh, ad, multiplier, min_tx):
        self.nh = nh
        self.ad = ad    # type int
        self.multiplier = multiplier
        self.min_tx= min_tx


class StaticRoute:
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, net):
        self.net = net
        self.list_nh_ad = []
        #self.vrf_name = ""
        #self.interface_name = ""

       # self.track_id = 0  # type int
       # self.ad = 0  # type int
       # self.tag = 0 # type int

    @staticmethod
    def query_data(hostname, vrf_name):
        try:
            sql = "select Net from static_route where Hostname = '%s' and VRF_Name = '%s' group by Net" % (hostname, vrf_name)
            StaticRoute.cursor.execute(sql)
            list_rows = StaticRoute.cursor.fetchall()
            #print 'VRF_Name:',vrf_name
            #print list_rows
            list_group_net = list(map(lambda x: x[0], list_rows))
            list_static_route = StaticRoute.extract_data(hostname, vrf_name, list_group_net)
            return list_static_route
        except MySQLdb.Error, e:
            print (e)
            StaticRoute.db.rollback()

    @staticmethod
    def extract_data(hostname, vrf_name, list_group_net):
        try:
            list_static_route = []
            for net in list_group_net:
                sql = "select static_route.NH, static_route.AD,bfd.Multiplier,bfd.Min_tx from static_route " \
                      "left join bfd " \
                      "on static_route.Hostname=bfd.Hostname and static_route.BFD = bfd.Name " \
                      "where static_route.Hostname = '%s' and static_route.VRF_Name = '%s' and static_route.Net = '%s'" \
                      % (hostname, vrf_name, net)
                StaticRoute.cursor.execute(sql)
                # convert net_cisco to net_juniper
                if " " in net:
                    host, subnet = net.strip().split()
                    subnet_mask = host + '/' + subnet
                    network_ipv4 = ip.ip_network(unicode(subnet_mask))
                else:
                    network_ipv4 = net.strip()
                static_route = StaticRoute(str(network_ipv4))
                list_rows = StaticRoute.cursor.fetchall()
                for row in list_rows:
                    temp_multi = 3
                    temp_min =10
                    if row[2] >0:
                        temp_multi = row[2]
                    elif row[2] is None:
                        temp_multi = 0
                    if row[3]>0:
                       temp_min = row[3]
                    elif row[3] is None:
                        temp_min = 0
                    nh_ad = NH_AD(row[0], row[1], temp_multi, temp_min)
                    static_route.list_nh_ad.append(nh_ad)
                list_static_route.append(static_route)
            return list_static_route

        except MySQLdb.Error, e:
            print (e)
            StaticRoute.db.rollback()