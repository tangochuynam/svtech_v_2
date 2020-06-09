from itertools import groupby

import MySQLdb
import re
from jinja2 import Environment, FileSystemLoader

from Database import Database
from IFL import INTERFACE_UNIT


class PEER_L2VPN:

    def __init__(self, peer = '', vc_id = '', bk_peer ='', upe = False, bk_vc_id = ''):
        self.peer = peer
        self.vc_id = vc_id      # type int
        self.bk_peer = bk_peer
        self.upe = upe
        self.bk_vc_id = bk_vc_id


class NEIGHBOR:
    db = Database.db
    cursor = Database.cursor
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
        except MySQLdb.Error as e:
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
    db = Database.db
    cursor = Database.cursor
    list_ifd = []
    list_bd_id_ip = []
    router_type = ""
    hostname = ""
    service_name = 'l2vpn'
    service_ccc = 'ccc'

    def __init__(self, name = "", vsi = "", mtu = 0, encap = '',
                 loop_detect = False, admin_status = True, description = '', isolated = False):
        self.name = name
        self.bd_id = ""
        self.vsi = vsi
        self.mtu = mtu
        self.encap = encap
        self.loop_detect = loop_detect
        self.isolated = isolated
        self.admin_status = admin_status
        self.description = description
        self.flag_pim = False
        self.flag_irb = False
        self.listPeer_no_split = []
        self.listPeer_split = []
        self.listPeer_global = []
        self.interface_unit = []
        self.list_recheck_split = []
        self.list_recheck_no_split = []
        self.flag_global = False

    @staticmethod
    def query_data(hostname, list_ifd, router_type):
        try:
            L2VPN.router_type = router_type
            L2VPN.hostname = hostname
            # print ("coming into SQL")
            L2VPN.list_ifd = list_ifd
            list_l2vpn = []
            list_vsi = L2VPN.get_list_vsi(hostname)

            for vsi in list_vsi:
                sql_query = " select Peer, VC_ID, UPE, BK_Peer, BK_vc_id from l2vpn " \
                            "where Name = '%s' and HostName = '%s' " \
                            % (vsi.name, hostname)
                #print('line 120 in l2vpn.py:', sql_query)
                L2VPN.cursor.execute(sql_query)
                list_rows = L2VPN.cursor.fetchall()
                # get list of interface_unit from IFL table and IFD table
                # --- update 2020 not get from DB, get from list_ifd
                # list_rows_ifl = INTERFACE_UNIT.query_data(hostname, vsi.name, L2VPN.list_ifd)
                list_rows_ifl = INTERFACE_UNIT.get_service_list(L2VPN.list_ifd, L2VPN.service_name, vsi.name)
                data = vsi.extract_data(list_rows, list_rows_ifl)
                #for int_unit in list_rows_ifl:
                #    if int_unit.mx_ifd == 'irb':
                #        print ("query_data "+ "unit1: " + str(int_unit.unit1) + " stitching: " + str(int_unit.stitching))
                list_l2vpn.append(data)
            return list_l2vpn
        except MySQLdb.Error as e:
            #sua loi khong tim thay db sql 10/4/2020
            if e.args[0]== 1064:
                print("line 133 in l2vpn.py:", e)
                return list_l2vpn
            else:
            # rollback in case there is any error
                print("line 137 in l2vpn.py:", e)
                L2VPN.db.rollback()

    @staticmethod
    def query_data_ccc(hostname, list_ifd, router_type):
        try:
            L2VPN.router_type = router_type
            L2VPN.hostname = hostname
            # print ("coming into SQL")
            L2VPN.list_ifd = list_ifd
            list_ccc = []
            list_ccc = L2VPN.get_list_ccc(hostname)
            return list_ccc
        except MySQLdb.Error as e:
            print(e)
            # rollback in case there is any error
            L2VPN.db.rollback()

    @staticmethod
    def query_vlan_local(hostname, list_bd_id_ip):
        try:
            L2VPN.list_bd_id_ip = list_bd_id_ip
            list_l2vpn_local = []
            list_bdid_local = L2VPN.get_list_bdid_local(hostname)
            #print ("length bdid local: " + str(len(list_bdid_local)))
            for bdid in list_bdid_local:
               # print ("bdid: " + bdid)
               #  list_rows_ifl = INTERFACE_UNIT.query_data(hostname, bdid, L2VPN.list_ifd)
                list_rows_ifl = INTERFACE_UNIT.get_service_list(L2VPN.list_ifd, L2VPN.service_name, bdid)
                l2_vpn_local = L2VPN.extract_data_local(list_rows_ifl, hostname, bdid)
                list_l2vpn_local.append(l2_vpn_local)
            return list_l2vpn_local
        except MySQLdb.Error as e:
            print(e)
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
        except MySQLdb.Error as e:
            print(e)
            L2VPN.db.rollback()

    @staticmethod
    def get_list_vsi(hostname):
        try:
            sql_query = "select Name, Vsi_id, Isolate, Encap, MTU, " \
                        "Loop_detect, Description, Admin_status from vsi " \
                        "where Hostname = '%s' " % hostname
            L2VPN.cursor.execute(sql_query)
            # handle the data
            list_rows = L2VPN.cursor.fetchall()
            return list(map(lambda x: L2VPN(name=x[0], vsi=x[1], isolated=x[2],
                                            encap=x[3], mtu=x[4], loop_detect=x[5],
                                            description=x[6], admin_status=x[7]),  list_rows))
        except MySQLdb.Error as e:
            print (e)
            L2VPN.db.rollback()

    @staticmethod
    def get_list_ccc(hostname):
        try:
            sql_query = "select CCC_Name from ifl where hostname = '%s' " \
                        "and Service like '%s' group by CCC_Name" % (hostname, 'ccc%')
            L2VPN.cursor.execute(sql_query)
            # handle the data
            list_rows = L2VPN.cursor.fetchall()
            if len(list_rows) > 0:
                list_ccc = list(map(lambda x: CCC(name=x[0]), list_rows))
                for item_ccc in list_ccc:
                    print('line 218 in l2vpn.py:', hostname, item_ccc.name)
                    # sql = "select ifd.MX_IFD,ifl.Unit1 from ifl "\
                    #       "inner join ifd on ifl.Hostname=ifd.Hostname and ifl.IFD = ifd.Name "\
                    #       "where ifl.hostname='%s' and ifl.Service like '%s' and  ifl.CCC_Name='%s'" %\
                    #      (hostname, 'ccc%', item_ccc.name)
                    # L2VPN.cursor.execute(sql)
                    # list_rows1 = L2VPN.cursor.fetchall()
                    list_rows1 = INTERFACE_UNIT.get_service_list(L2VPN.list_ifd, L2VPN.service_ccc, item_ccc.name)
                    print(list_rows1)
                    if len(list_rows1) > 0:
                        item_ccc.list_intf_ccc = list(map(lambda x: x[0]+'.'+str(x[1]) ,list_rows1))
            else:
                list_ccc = []
            return list_ccc
        except MySQLdb.Error as e:
            print (e)
            L2VPN.db.rollback()

    @staticmethod
    def extract_data_local(list_rows_ifl, hostname, bd_id):
        l2_vpn = L2VPN(hostname)
        l2_vpn.interface_unit = list_rows_ifl
        l2_vpn.name = bd_id
        l2_vpn.bd_id = bd_id
        # get flag_irb from list_interface_unit
        # list_irb = list(map(lambda x: x.mx_ifd, l2_vpn.interface_unit))
        if l2_vpn.bd_id in L2VPN.list_bd_id_ip:
            l2_vpn.flag_irb = True
        # handle special case to get flag_pim
        #l2_vpn.get_flag_pim(db, cursor, hostname, l2_vpn.bd_id, l2_vpn.flag_irb)
        return l2_vpn

    def extract_data(self, list_rows, list_rows_ifl):
        self.interface_unit = list_rows_ifl
        # change name of vsi (chinh la obj l2vpn)
        if ('(' in self.name) | (')' in self.name) | ('&' in self.name) | ('"' in self.name):
            self.name = '-'.join(re.split("[()&\"]", self.name))

        for row in list_rows:
            upe = row[2]
            peer_l2vpn = PEER_L2VPN(peer=row[0], vc_id=row[1], upe=row[2], bk_peer=row[3], bk_vc_id=row[4])
            if upe:
                if self.isolated:
                    self.listPeer_global.append(peer_l2vpn)
                else:
                    self.listPeer_no_split.append(peer_l2vpn)
            else:
                self.listPeer_split.append(peer_l2vpn)

        # handle the special case (garbage in configuration in cisco) vpn-id and vc_id
        self.get_list_recheck_split()
        self.get_list_recheck_no_split()
        self.get_flag_global()
        #print ("after")
        #print (data.list_recheck)
        #for int_unit in data.interface_unit:
        #    if int_unit.mx_ifd == 'irb':
        #        print ("unit1: " + str(int_unit.unit1) + " stitching: " + str(int_unit.stitching))
        return self

    def get_list_recheck_split(self):
        self.list_recheck_split = list(filter(lambda x: self.vsi != x.vc_id, self.listPeer_split))

    def get_list_recheck_no_split(self):
        self.list_recheck_no_split = list(filter(lambda x: self.vsi != x.vc_id, self.listPeer_no_split))

    def get_flag_global(self):
        lst_tmp = list(filter(lambda x: self.vsi != x.vc_id, self.listPeer_global))
        if len(lst_tmp) > 0:
            self.flag_global = True

    def get_flag_pim(self, hostname, bd_id, flag_irb):
        try:
            if flag_irb:
                sql = "select PIM from ifl where Hostname = '%s' and IFD = 'Vlan' and Unit = '%s' " % (hostname, bd_id)
                L2VPN.cursor.execute(sql)
                list_rows = L2VPN.cursor.fetchall()
                list_temp = list(map(lambda x: x[0], list_rows))
                self.flag_pim = list_temp[0]
                #print ("length: " + str(len(list_temp)) + " bd_id: " + bd_id)
        except MySQLdb.Error as e:
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


class CCC:
    def __init__(self, name=''):
        self.name = name
        self.list_intf_ccc = []