import MySQLdb
from itertools import groupby
from jinja2 import Environment, FileSystemLoader
from IFL import INTERFACE_UNIT
import re
import Database


class PEER_L2VPN:
    def __init__(self, peer, vc_id, bk_peer):
        self.peer = peer
        self.vc_id = vc_id      # type int
        self.bk_peer = bk_peer


class NEIGHBOR:
    db = Database.Database.db
    cursor = Database.Database.cursor
    list_ifd = []

    def __init__(self, name, bk_peer, mtu, vc_id, description, encap, bk_vc_id):
        self.name = name
        self.bk_peer = bk_peer
        self.mtu = mtu
        self.vc_id = vc_id
        self.encap = encap
        self.bk_vc_id = bk_vc_id
        if '"' in description:
            self.description = ''.join(e for e in description.split('"'))
        else:
            self.description = description
        self.interface_name = ""

    @staticmethod
    def query_data(hostname, list_ifd):
        try:
            NEIGHBOR.list_ifd = list_ifd
            sql = "select Peer, BK_Peer, MTU, VC_ID, Description, IFL, Encap, BK_vc_id " \
                  "from l2vpn where Hostname = '%s' and Type = 'l2circuit'" % (hostname)
            NEIGHBOR.cursor.execute(sql)
            list_rows = NEIGHBOR.cursor.fetchall()
            list_neighbor = NEIGHBOR.extract_data(list_rows, hostname)
            return list_neighbor
        except MySQLdb.Error, e:
            print (e)
            NEIGHBOR.db.rollback()

    @staticmethod
    def extract_data(list_rows, hostname):
        list_neighbor = []
        for row in list_rows:
            neighbor = NEIGHBOR(row[0], row[1], row[2], row[3], row[4], row[6], row[7])
            neighbor.description = neighbor.description.lstrip()
            if '.' in row[5]:
                ifd, unit = row[5].split('.')
                neighbor.interface_name = INTERFACE_UNIT.query_data_new_ifl(hostname, ifd.strip(), unit.strip(), NEIGHBOR.list_ifd)
            if neighbor.interface_name.startswith(('ae', 'xe', 'ge')):
                list_neighbor.append(neighbor)
        return list_neighbor

    @staticmethod
    def writefile(neighbor_list, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        info_neighbor= {'neighbor_list': neighbor_list}
        file_ouput = path_output + "/" + hostname
        with open(file_ouput, 'a') as f:
            f_txt = template_env.get_template(file_name).render(info_neighbor)
            f.write(f_txt)
        print("write successful")


class L2VPN:
    db = Database.Database.db
    cursor = Database.Database.cursor
    list_ifd = []
    list_bd_id_ip = []
    router_type = ""

    def __init__(self, hostname):
        self.name = ""
        self.bd_id = ""
        # self.noSplit = False
        # self.type = ""
        # self.pwClass = ""
        self.vpn_id = ""
        self.mtu = 0
        self.hostname = hostname
        self.flag_pim = False
        self.flag_irb = False
        self.flag_inactive_vpls = True
        self.listPeer_no_split = []
        self.listPeer_split = []
        self.listPeer_global = []
        self.interface_unit = []
        self.list_recheck = []

    @staticmethod
    def query_data(hostname, list_ifd, router_type):
        try:
            # print ("coming into SQL")
            L2VPN.list_ifd = list_ifd
            list_l2vpn = []
            list_bdid = L2VPN.get_list_service(hostname)
            L2VPN.router_type = router_type
            for bdid in list_bdid:
                sql_query = " select Peer, VC_ID, Name, No_split, BK_Peer, MTU, VPN_ID, Meshgroup from l2vpn where Type = '%s' and HostName = '%s' and BD_ID = '%s' " \
                            % ('vpls', hostname, bdid)
                L2VPN.cursor.execute(sql_query)
                list_rows = L2VPN.cursor.fetchall()
                # get list of interface_unit from IFL table and IFD table
                list_rows_ifl = INTERFACE_UNIT.query_data(hostname, bdid, L2VPN.list_ifd)
                data = L2VPN.extract_data(list_rows, list_rows_ifl, hostname, bdid)
                #for int_unit in list_rows_ifl:
                #    if int_unit.mx_ifd == 'irb':
                #        print ("query_data "+ "unit1: " + str(int_unit.unit1) + " stitching: " + str(int_unit.stitching))
                list_l2vpn.append(data)
            return list_l2vpn
        except MySQLdb.Error, e:
            print (e)
            # rollback in case there is any error
            L2VPN.db.rollback()

    @staticmethod
    def query_vlan_local(hostname, list_bd_id_ip):
        try:
            L2VPN.list_bd_id_ip = list_bd_id_ip
            # print ("coming into SQL")
            list_l2vpn_local = []
            list_bdid_local = L2VPN.get_list_bdid_local(hostname)
            #print ("length bdid local: " + str(len(list_bdid_local)))
            for bdid in list_bdid_local:
               # print ("bdid: " + bdid)
                list_rows_ifl = INTERFACE_UNIT.query_data(hostname, bdid, L2VPN.list_ifd)
                l2_vpn_local = L2VPN.extract_data_local(list_rows_ifl, hostname, bdid)
                list_l2vpn_local.append(l2_vpn_local)
            return list_l2vpn_local
        except MySQLdb.Error, e:
            print (e)
            # rollback in case there is any error
            L2VPN.db.rollback()

    @staticmethod
    def get_list_bdid_local(hostname):
        try:
            sql_query = ("select ifl.BD_ID from ifl "
                         "where ifl.Hostname = '%s' and ifl.Service = 'vpls' and ifl.BD_ID "
                         "not in (select l2vpn.bd_id from l2vpn where l2vpn.Hostname = '%s' )"
                         "and ifl.BD_ID not in (select BD_ID from ifl "
                         "where ifl.Hostname = '%s' and (ifl.IFD = 'Vlan' or ifl.IFD = 'BVI') and ifl.PIM = 1) "
                         "group by BD_ID ") % (hostname, hostname, hostname)
            L2VPN.cursor.execute(sql_query)
            list_bdid_local = L2VPN.cursor.fetchall()
            return list(map(lambda x: x[0], list_bdid_local))
        except MySQLdb.Error, e:
            print (e)
            L2VPN.db.rollback()

    @staticmethod
    def get_list_service(hostname):
        try:
            sql_query = "select BD_ID from l2vpn where Type = '%s' and Hostname = '%s' and BD_ID != '' group by BD_ID" % (
            'vpls', hostname)
            L2VPN.cursor.execute(sql_query)
            # handle the data
            list_rows = L2VPN.cursor.fetchall()
            return list(map(lambda x: x[0], list_rows))
        except MySQLdb.Error, e:
            print (e)
            L2VPN.db.rollback()

    @staticmethod
    def extract_data_local(list_rows_ifl, hostname, bd_id):
        l2_vpn = L2VPN(hostname)
        l2_vpn.interface_unit = list_rows_ifl
        l2_vpn.name = 'VLAN' + '-' + bd_id
        l2_vpn.bd_id = bd_id
        # get flag_irb from list_interface_unit
        list_irb = list(map(lambda x: x.mx_ifd, l2_vpn.interface_unit))
        if l2_vpn.bd_id in L2VPN.list_bd_id_ip:
            l2_vpn.flag_irb = True
        # handle special case to get flag_pim
        #l2_vpn.get_flag_pim(db, cursor, hostname, l2_vpn.bd_id, l2_vpn.flag_irb)
        return l2_vpn

    @staticmethod
    def extract_data(list_rows, list_rows_ifl, hostname, bd_id):
        data = L2VPN(hostname)
        data.interface_unit = list_rows_ifl
        data.bd_id = bd_id
        name = list_rows[0][2]
        data.mtu = list_rows[0][5]
        data.vpn_id = list_rows[0][6]
        # Peer: 0, VC_ID: 1, Name: 2, No_split: 3, BK_Peer: 4, MTU: 5, VPN_ID: 6,
        if name == '':
            data.name = 'VLAN' + '-' + bd_id
        else:
            if ('(' in name) | (')' in name) | ('&' in name) | ('"' in name):
                data.name = '-'.join(re.split("[()&\"]", name))
            else:
                data.name = name
        for row in list_rows:
            no_split = row[3]
            if L2VPN.router_type == 'C76xx':
                if no_split:
                    data.listPeer_no_split.append(PEER_L2VPN(row[0], row[1], row[4]))
                else:
                    data.listPeer_split.append(PEER_L2VPN(row[0], row[1], row[4]))
            elif L2VPN.router_type == 'ASR9k':
                mesh_group = row[7]
                if mesh_group != '':
                    data.listPeer_split.append(PEER_L2VPN(row[0], row[1], row[4]))
                else:
                    if no_split:
                        data.listPeer_no_split.append(PEER_L2VPN(row[0], row[1], row[4]))
                    else:
                        data.listPeer_global.append(PEER_L2VPN(row[0], row[1], row[4]))
            else:
                print ("this kind is not C76xx or ASR9k")


        # handle the special case (garbage in configuration in cisco) vpn-id and vc_id
        data.get_vpn_id_and_list_recheck(hostname, bd_id)
        data.get_mtu_from_ifl(hostname, bd_id)
        data.get_flag_inactive_vpls(hostname, bd_id)
        #print ("after")
        #print (data.list_recheck)
        #for int_unit in data.interface_unit:
        #    if int_unit.mx_ifd == 'irb':
        #        print ("unit1: " + str(int_unit.unit1) + " stitching: " + str(int_unit.stitching))
        return data

    def get_flag_inactive_vpls(self, hostname, bd_id):
        try:
            sql = ""
            if L2VPN.router_type == 'C76xx':
                sql = "select Admin_status from ifl where Hostname = '%s' and IFD = 'Vlan' and BD_ID = '%s' " % (hostname, bd_id)
            elif L2VPN.router_type == 'ASR9k':
                sql = "select Admin_status from l2vpn where Hostname = '%s' and BD_ID = '%s' " % (hostname, bd_id)
            else:
                print("router type is not supported")
            if sql != '':
                L2VPN.cursor.execute(sql)
                row = L2VPN.cursor.fetchall()
                row_temp = list(map(lambda x: x[0], row))
                if not row_temp[0]:
                    self.flag_inactive_vpls = False
        except MySQLdb.Error, e:
            print (e)
            L2VPN.db.rollback()

    def get_mtu_from_ifl(self, hostname, bd_id):
        try:
            sql = "select MTU from ifl where Hostname = '%s' and BD_ID = '%s' and (IFD = 'Vlan' or IFD = 'BVI')" % (hostname, bd_id)
            L2VPN.cursor.execute(sql)
            list_rows = L2VPN.cursor.fetchall()
            list_temp = list(map(lambda x: x[0], list_rows))
            if len(list_temp) > 0:
                if list_temp[0] > 0:
                    self.mtu = list_temp[0]
        except MySQLdb.Error, e:
            print (e)
            L2VPN.db.rollback()

    def get_vpn_id_and_list_recheck(self, hostname, bd_id):
        try:
            sql = "select VC_ID from l2vpn where Hostname = '%s' and BD_ID = '%s' and Type = 'vpls'" % (hostname, bd_id)
            L2VPN.cursor.execute(sql)
            list_rows = L2VPN.cursor.fetchall()
            list_vc_id = list(map(lambda x: x[0], list_rows))
            list_vc_id = sorted(list_vc_id)
            dict_vc_id = {}
            key_max = 0
            # convert to dict with key and list of elenment in the same group(same value)
            if len(list_vc_id) > 1:
                for k, v in groupby(list_vc_id):
                    dict_vc_id[k] = list(v)
                # convert this dict to key and value = len(list)
                list_dict_temp = list(map(lambda (x, y): {x: len(y)}, dict_vc_id.iteritems()))
                # convert list of dict to dict
                dict_convert = {item.keys()[0]: item.values()[0] for item in list_dict_temp}
                if self.vpn_id not in dict_convert:
                    key_max = max(dict_convert, key=dict_convert.get)
                    self.vpn_id = key_max
                    # remove key_max in dict
                    del dict_convert[key_max]
                    self.list_recheck = dict_convert.keys()
                else:
                    del dict_convert[self.vpn_id]
                    self.list_recheck = dict_convert.keys()
            else:
                self.vpn_id = list_vc_id[0]

            #print("key_max: " + str(key_max))
            #print("before")
            #print(self.list_recheck)

        except MySQLdb.Error, e:
            print (e)
            L2VPN.db.rollback()

    def get_flag_pim(self, hostname, bd_id, flag_irb):
        try:
            if flag_irb:
                sql = "select PIM from ifl where Hostname = '%s' and IFD = 'Vlan' and Unit = '%s' " % (hostname, bd_id)
                L2VPN.cursor.execute(sql)
                list_rows = L2VPN.cursor.fetchall()
                list_temp = list(map(lambda x: x[0], list_rows))
                self.flag_pim = list_temp[0]
                #print ("length: " + str(len(list_temp)) + " bd_id: " + bd_id)
        except MySQLdb.Error, e:
            print (e)
            L2VPN.db.rollback()


    @staticmethod
    def writefile(l2vpn_list, l2vpn_list_local, list_policer, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        info_l2vpn = {'l2vpn_list': l2vpn_list, 'l2vpn_list_local': l2vpn_list_local, 'list_policer': list_policer}
        file_ouput = path_output + "/" + hostname
        with open(file_ouput, 'w') as f:
            f_txt = template_env.get_template(file_name).render(info_l2vpn)
            f.write(f_txt)
        print("write successful")


class RECHECK:
    def __init__(self):
        self.vc_id = ""
        self.list_neighbor = []