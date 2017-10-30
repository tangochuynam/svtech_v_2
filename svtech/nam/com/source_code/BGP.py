import MySQLdb

import Database


class NEIGHBOR_PEER_AS:
    def __init__(self, local_address_name="", peer="", remote_as="", bfd_interval="",
                 bfd_multiplier="", import_policy="", export_policy =""):
        self.remote_as = remote_as
        self.peer = peer
        self.local_address_name = local_address_name
        self.bfd_interval = bfd_interval
        self.bfd_multiplier = bfd_multiplier
        if import_policy is not None:
            self.import_policy = import_policy
        else:
            print("import policy is null")
            self.import_policy = ''
        if export_policy is not None:
            self.export_policy = export_policy
        else:
            print "export policy is null"
            self.export_policy = ''


class BGP:
    db = Database.Database.db
    cursor = Database.Database.cursor
    router_type = ""
    def __init__(self):
        self.name_group = ""
        self.cluster_id = ""
        self.list_neighbor_peer_as = []
        #self.as_bgp = ""
        #self.peer = ""
        #self.rid = ""
        #self.peer_group = ""
        #self.redistribute = ""
        #self.vrf_name = ""
        #self.nlri = ""

    @staticmethod
    def set_router_type(type):
        BGP.router_type = type

    @staticmethod
    def query_data(hostname, vrf_name):
        try:
            sql = "select Peer_group from bgp where Hostname = '%s' and VRF_Name = '%s' group by Peer_Group" % (hostname, vrf_name)
            BGP.cursor.execute(sql)
            list_rows = BGP.cursor.fetchall()
            list_group = list(map(lambda x: x[0], list_rows))
            list_bgp = BGP.extract_data(hostname, vrf_name, list_group)
            #print list_bgp
            return list_bgp
        except MySQLdb.Error, e:
            print (e)
            BGP.db.rollback()

    @staticmethod
    def extract_data(hostname, vrf_name, list_group):
        try:
            list_bgp = []
            for group in list_group:
                bgp = BGP()
                if group != "":
                    bgp.name_group = group
                else:
                    bgp.name_group = "ext"
                sql = "select Peer, Update_Source, Remote_AS, BFD_interval, BFD_multiplier, Import_policy, " \
                      "Export_policy from bgp" \
                      " where Hostname = '%s' and VRF_Name = '%s' and Peer_Group = '%s'" \
                      % (hostname, vrf_name, group)
                BGP.cursor.execute(sql)
                list_rows = BGP.cursor.fetchall()
                #print list_rows
                for row in list_rows:
                    neighbor_peer = BGP.get_neighbor_peer(hostname, row)
                    bgp.list_neighbor_peer_as.append(neighbor_peer)
                list_bgp.append(bgp)
            return list_bgp
        except MySQLdb.Error, e:
            print (e)
            BGP.db.rollback()

    @staticmethod
    def get_neighbor_peer(hostname, row):
        try:
            update_source = row[1]
            print ("update_source: " + update_source)
            if update_source != '':
                ifd = unit = ""
                if 'Vlan' in update_source:
                    ifd = update_source[0:4]
                    unit = update_source[4:]
                elif 'Looback' in update_source:
                    ifd = update_source[0:7]
                    unit = update_source[7:]
                else:
                    ifd, unit = update_source.split('.')
                sql = "select IP from ifl where Hostname = '%s' and IFD = '%s' and Unit = '%s'" % (hostname, ifd, unit)
                BGP.cursor.execute(sql)
                temp_row = BGP.cursor.fetchall()
                ip, subnet = temp_row[0][0].split()
            else:
                ip = ''
            #print ip,row[0],row[2],row[3], row[4], row[5], row[6]
            return NEIGHBOR_PEER_AS(ip, row[0], row[2], row[3], row[4], row[5],row[6])
        except MySQLdb.Error, e:
            print (e)
            BGP.db.rollback()

    @staticmethod
    def get_lst_neighbor_group_bgp(hostname, cluster=''):
        try:
            if BGP.router_type == 'ASR9k':
                if cluster == '':
                    sql = "select Peer, Import_policy, Export_policy, Remote_AS from bgp " \
                          "where Hostname = '%s' and VRF_Name = '' " \
                          "and Peer_Group = ''" % hostname
                else:
                    sql = "select Peer from bgp where Hostname = '%s' and VRF_Name = '' " \
                          "and Cluster = '%s' and Peer_Group != ''" % (hostname, cluster)
                BGP.cursor.execute(sql)
                rows = BGP.cursor.fetchall()
                if len(rows) > 0:
                    if cluster == '':
                        return list(map(lambda x: NEIGHBOR_PEER_AS(peer=x[0], import_policy=x[1], export_policy=x[2], remote_as=x[3]), rows))
                    else:
                        return list(map(lambda x: x[0], rows))
                else:
                    return list()
            elif BGP.router_type == 'C76xx':
                return []
            else:
                print ("Router_type is not ASR9k nor C76xx")
        except MySQLdb.Error, e:
            print (e)
            BGP.db.rollback()

    @staticmethod
    def query_bgp_HW(hostname):
        lst_bgp_hw = []
        try:
            BGP.hostname = hostname
            # xac dinh so peer group
            sql = "select Peer, Cluster_id from bgp " \
                  "where Hostname = '%s' and VRF_Name = '' and Peer not like '%s' " % (BGP.hostname, '%.%.%.%')
            BGP.cursor.execute(sql)
            rows = BGP.cursor.fetchall()
            if len(rows) > 0:
                for row in rows:
                    bgp = BGP()
                    bgp.name_group = row[0]
                    bgp.cluster_id = row[1]
                    sql_1 = "select Peer from bgp " \
                            "where Hostname = '%s' and VRF_Name = '' and Peer_group = '%s'" % (hostname, bgp.name_group)
                    BGP.cursor.execute(sql_1)
                    lst_row_1 = BGP.cursor.fetchall()
                    bgp.list_neighbor_peer_as = list(map(lambda x: x[0], lst_row_1))
                    lst_bgp_hw.append(bgp)
            else:
                bgp = BGP()
                bgp.name_group = 'IBGP-TO-RR'
                sql_2 = "select Peer from bgp where Hostname = '%s' and VRF_Name = '' and Peer_group = ''" % hostname
                BGP.cursor.execute(sql_2)
                lst_row_2 = BGP.cursor.fetchall()
                bgp.list_neighbor_peer_as = list(map(lambda x: x[0], lst_row_2))
                lst_bgp_hw.append(bgp)
        except MySQLdb.Error, e:
            print (e)
            BGP.db.rollback()
        finally:
            return lst_bgp_hw
