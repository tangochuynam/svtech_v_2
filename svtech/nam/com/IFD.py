import MySQLdb
from jinja2 import Environment, FileSystemLoader
import ipaddr
import Database


class IFD:
    db = Database.Database.db
    cursor = Database.Database.cursor
    iso_address = ""
    list_bd_id_igmp = []
    list_bd_id_l2vpn = []
    list_policy_cos = []
    list_unit_vlan_policer = []
    list_bd_id_ip = []
    lst_dhcp_relay = []
    router_type = ""
    hostname = ""
    flag_create_notation = False

    def __init__(self, name, description, mtu, flex_service, parent_link,
                 ae_type, ae_mode, wanphy, speed, mx_ifd,
                 type_tmp, admin_status = True, native_vlan=''):
        self.name = name
        if '"' in description:
            self.description = ''.join(e for e in description.split('"'))
        else:
            self.description = description
        self.mtu = mtu
        self.flex_service = flex_service
        self.parent_link = parent_link
        self.ae_type = ae_type
        self.ae_mode = ae_mode
        self.wanphy = wanphy
        self.speed = speed
        self.mx_ifd = mx_ifd
        self.flag_default = False
        self.flag_default_l2circuit = False
        self.flag_default_vpls = False
        self.flag_svlan_untagged = False
        self.flag_cos = False
        self.type = type_tmp
        self.list_unit = []
        self.admin_status = admin_status
        # add new attribute
        self.native_vlan = native_vlan

    @staticmethod
    def filter_vlan_cos(list_ifd_all):
        ifd_vlans = []
        if IFD.router_type == 'C76xx':
            ifd_vlans = list(filter(lambda ifd: ifd.name == 'Vlan', list_ifd_all))
        elif IFD.router_type == 'ASR9k':
            ifd_vlans = list(filter(lambda ifd: ifd.name == 'BVI', list_ifd_all))
        elif IFD.router_type == 'HW':
            ifd_vlans = list(filter(lambda ifd: ifd.name == 'Vlanif', list_ifd_all))
        ifd_vlan = ifd_vlans[0]
        list_unit_flag_cos = list(filter(lambda unit: unit.flag_cos, ifd_vlan.list_unit))
        list_bd_id_cos = list(map(lambda x: x.bd_id, list_unit_flag_cos))
        #print ("list_bd_cos")
        #print (list_bd_id_cos)

        for ifd in list_ifd_all:
            if (ifd.name != 'Vlan') & (ifd.name != 'Loopback') & (ifd.name != 'BVI') & (ifd.name != 'Vlanif') & (ifd.name != 'LoopBack'):
                for unit_temp in ifd.list_unit:
                    if unit_temp.bd_id in list_bd_id_cos:
                        print ("ifd: " + ifd.name + " unit: " + str(unit_temp.unit1))
                        unit_temp.flag_cos = True
                        ifd.flag_cos = True
        #print ("list_ifd_all:" + str(len(list_ifd_all)))
        return list_ifd_all

    @staticmethod
    def set_class_paras(iso_address, list_bd_id_igmp, list_bd_id_l2vpn, list_policy_cos,
                            list_unit_vlan_policer, list_bd_id_ip, router_type, lst_dhcp_relay):
        IFD.iso_address = iso_address
        IFD.list_bd_id_igmp = list_bd_id_igmp
        IFD.list_bd_id_l2vpn = list_bd_id_l2vpn
        IFD.list_policy_cos = list_policy_cos
        IFD.list_unit_vlan_policer = list_unit_vlan_policer
        IFD.list_bd_id_ip = list_bd_id_ip
        IFD.router_type = router_type
        IFD.lst_dhcp_relay = lst_dhcp_relay

    @staticmethod
    def query_data(hostname, flag_create_notation):
        try:
            IFD.hostname = hostname
            IFD.flag_create_notation = flag_create_notation
            #print ("list_policy_cos: " + str(len(list_policy_cos)))
            sql = "select Name, Description, MTU, Flex_service, Parent_link, AE_type, AE_mode, Wanphy, " \
                  "Speed, MX_IFD, Type, Admin_status, Native_vlan " \
                  "from ifd " \
                  "where Hostname = '%s'" % hostname
            IFD.cursor.execute(sql)
            list_rows = IFD.cursor.fetchall()
            #print ("length_row: " + str(len(list_rows)))
            list_ifd = list(map(lambda x: IFD(x[0], x[1], int(x[2]), x[3], x[4], x[5],
                                              x[6], x[7], x[8], x[9] if x[9] is not None else x[0], x[10], x[11], x[12]), list_rows))

            for ifd in list_ifd:
                #print("ifd_mxifd: " + ifd.mx_ifd)
                ifd.insert_unit()

            # convert list_ifd to new list_ifd with new flex_service (relation parent_link in this list)
            list_ifd = list(map(lambda x: x.get_new_ifd_with_flex_service(list_ifd), list_ifd))
            return list_ifd
        except MySQLdb.Error, e:
            print (e)
            IFD.db.rollback()

    @staticmethod
    def convert_info_unit(info, ifd):

        ip_helper_tmp = info[19]
        if (ifd.name != 'Vlanif') | (ip_helper_tmp == ''):
            unit = UNIT(info[0], info[1], info[2], info[3], info[4], info[5],
                        info[6], info[7], info[8], info[9], info[10], info[11], info[12])
            # convert ip
            network = info[13]
            if network != '':
                if network == 'unnumbered lo0':
                    unit.ip = '1.1.1.1/31'
                    print('unnumbered lo0: ' + unit.ip)
                else:
                    if 'lo0' not in network:
                        host, subnet = network.strip().split()
                        subnet_mask = host + '/' + subnet
                        # print("subnet_mask: " + subnet_mask)
                        network_ipv4 = ipaddr.IPv4Network(subnet_mask)
                        # print("network: " + str(network_ipv4))
                        unit.ip = str(network_ipv4)
                        # check ',' and '-' in svlan and cvlan
                    else:
                        unit.ip = network
            svlan_temp = info[3]
            cvlan_temp = info[4]
            if (',' in svlan_temp) | ('-' in svlan_temp):
                unit.svlan_list = ' '.join(svlan_temp.split(','))
            if (',' in cvlan_temp) | ('-' in cvlan_temp):
                unit.cvlan_list = ' '.join(cvlan_temp.split(','))

            if (ifd.name != 'Vlan') & (ifd.name != 'Loopback') & (unit.bd_id != ''):
                if unit.bd_id in IFD.list_bd_id_ip:
                    unit.flag_bdid = False
                if unit.unit1 == 525:
                    print ("unit_525: " + str(unit.bd_id) + " flag_bd_id: " + str(unit.flag_bdid))

            # add more attribute
            unit.split_horizon = info[14]
            unit.ff_in = info[15]
            unit.mpls = info[16]
            unit.admin_status = info[17]
            unit.switch_mode = info[18]
            unit.vrf_name = info[20]
            unit.igmp = info[21]
            unit.vsi_encap = info[22]
            unit.unit = info[23]
            unit.ff_out = info[24]
            unit.dhcp_gw = info[25]
            # handle the flag_cos
            if unit.service_pol_in in IFD.list_policy_cos:
                unit.flag_cos = True
                ifd.flag_cos = True
                # print ('unit_with_flag_cos_true: ' + str(unit.unit1))
            # print ("split_horizon:" + str(unit.split_horizon) + " unit: " + str(unit.unit1))

            # only get the unit from IFD.list_unit_vlan_policer
            unit.get_spi_spo(IFD.list_unit_vlan_policer)
            #unit.get_dhcpGW_Vlan_Unit(IFD.lst_dhcp_relay)
            # flag_create_notation is used or not
            if IFD.flag_create_notation:
                unit.get_list_unit_remote(ifd.name, IFD.hostname)
            # print ("ifd: " + ifd.name + " mx_ifd: " + ifd.mx_ifd + " unit: " + str(unit.unit1) + " spi_in: " + unit.service_pol_in + " spo: " + unit.service_pol_out )
            return unit
        else:
            return None

    def get_new_ifd_with_flex_service(self, list_ifd):
        if self.parent_link != '':
            name = ""
            if IFD.router_type == 'C76xx':
                name = "Port-channel" + self.parent_link
            elif IFD.router_type == 'ASR9k':
                name = "Bundle-Ether" + self.parent_link
            elif IFD.router_type == 'HW':
                name = "Eth-Trunk" + self.parent_link
            #print ("name:" + name)
            parent_of_ifd = list(filter(lambda ifd: name == ifd.name, list_ifd))
            self.flex_service = parent_of_ifd[0].flex_service
        return self

    def insert_unit(self):
        try:
            #print("insert_unit_to " + "ifd_mxifd: " + ifd.mx_ifd + " flag_default: " + str(ifd.flag_default) + " flag_l2circuit: "
            #      + str(ifd.flag_default_l2circuit) + " flag_vpls: " + str(ifd.flag_default_vpls)
            #      + " flag_svlan_untagged: " + str(ifd.flag_svlan_untagged) + " parent_link: " + ifd.parent_link)

            sql = "select Unit1, Description, Service, SVLAN, CVLAN, Vlan_mapping, " \
                  "Vlan_translate, Vlan_map_svlan, Vlan_map_cvlan, Service_pol_in, Service_pol_out, " \
                  "MTU, BD_ID, IP, Split_horizon, FF_in, " \
                  "MPLS, Admin_status, Switch_mode, IP_helper, " \
                  "VRF_Name, IGMP, VSI_encap, Unit, FF_out, DHCP_GW " \
                  "from ifl " \
                  "where Hostname = '%s' and IFD = '%s'" % (IFD.hostname, self.name)
            IFD.cursor.execute(sql)
            list_rows = IFD.cursor.fetchall()
            list_unit_temp = list(map(lambda x: IFD.convert_info_unit(x, self), list_rows))
            # filter nhung phan tu None trong list_unit_temp
            self.list_unit = list(filter(lambda x: x is not None, list_unit_temp))
            # bo sung vao list_unit truong hop loopback cho dhcp relay
            #self.insert_to_list_unit_dhcp_relay()

        except MySQLdb.Error, e:
            print (e)
            IFD.db.rollback()

    def insert_to_list_unit_dhcp_relay(self):
        if (self.name == 'LoopBack') & (len(IFD.lst_dhcp_relay) > 0):
            for helper in IFD.lst_dhcp_relay:
                unit = UNIT()
                unit.unit1 = helper.unit
                unit.ip = helper.ip.split(' ')[0] + '/32'
                unit.vrf_name = helper.vrf_name
                unit.ip_helper = helper.ip_helper
                self.list_unit.append(unit)

    def check_special_case(self, hostname):
        try:

            #print("in_check_special_case: " + " ifd_mxifd: " + ifd.mx_ifd + " flag_default: " + str(ifd.flag_default) + " flag_default_l2circuit: "
            #      + str(ifd.flag_default_l2circuit) + " flag_default_vpls: " + str(ifd.flag_default_vpls)
            #      + " flag_svlan_untagged: " + str(ifd.flag_svlan_untagged) + " parent_link: " + ifd.parent_link)

            sql_count_unit = "select count(Unit) from ifl where hostname = '%s' and IFD ='%s' " % (hostname, self.name)
            IFD.cursor.execute(sql_count_unit)
            row_count_unit = IFD.cursor.fetchall()
            count_unit = row_count_unit[0][0]
            sql_df_flag = "select IFD from ifl where Hostname = '%s' and IFD = '%s' and SVLAN = '%s'  " \
                          % (hostname, self.name, 'default')
            IFD.cursor.execute(sql_df_flag)
            list_rows_1 = IFD.cursor.fetchall()
            if (len(list_rows_1) >= 1) & (count_unit == 1):
                self.flag_default = True
                self.list_unit = [UNIT()]

            sql_df_flag_l2_circuit = "select IFD from ifl " \
                                     "where Hostname = '%s' and IFD = '%s' and SVLAN = '%s' and Service = '%s' " \
                                     % (hostname, self.name, 'default', 'l2circuit')
            IFD.cursor.execute(sql_df_flag_l2_circuit)
            list_rows_2 = IFD.cursor.fetchall()

            if (len(list_rows_2) >= 1) & (count_unit == 1):
                self.flag_default_l2circuit = True
                self.list_unit = [UNIT()]
                return 0

            sql_df_flag_l2_vpls = "select IFD from ifl " \
                                  "where Hostname = '%s' and IFD = '%s' and SVLAN = '%s' and Service = '%s' " \
                                  % (hostname, self.name, 'default', 'vpls')
            IFD.cursor.execute(sql_df_flag_l2_vpls)
            list_rows_3 = IFD.cursor.fetchall()
            # print("list_rows_3: " + str(len(list_rows_3)))
            if (len(list_rows_3) >= 1) & (count_unit == 1):
                self.flag_default_vpls = True
                self.list_unit = [UNIT()]
                return 0
            sql_df_flag_untagged = "select IFD from ifl where Hostname = '%s' and IFD = '%s' and SVLAN = '%s' " \
                                   % (hostname, self.name, 'untagged')
            IFD.cursor.execute(sql_df_flag_untagged)
            list_rows_4 = IFD.cursor.fetchall()
            # print("list_rows_4: " + str(len(list_rows_4)))
            if len(list_rows_4) == 1:
                self.flag_svlan_untagged = True
                return 1
        except MySQLdb.Error, e:
            print (e)
            IFD.db.rollback()

    @staticmethod
    def writefile(list_ifd, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        interface = {'list_ifd': list_ifd}
        file_ouput = path_output + "/" + hostname
        with open(file_ouput, 'w') as f:
            f_txt = template_env.get_template(file_name).render(interface)
            f.write(f_txt)
        print("write successful")


class UNIT:
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, unit1=0, description="", service="", svlan="", cvlan="", vlan_mapping="",
                 vlan_translate="", vlan_map_svlan="", vlan_map_cvlan="",
                 service_pol_in="", service_pol_out="", mtu=0, bd_id=""):
        self.unit1 = unit1      #type int
        if '"' in description:
            self.description = ''.join(e for e in description.split('"'))
        else:
            self.description = description
        self.service = service
        self.svlan = svlan
        self.cvlan = cvlan
        self.vlan_mapping = vlan_mapping
        self.vlan_translate = vlan_translate
        self.vlan_map_svlan = vlan_map_svlan
        self.vlan_map_cvlan = vlan_map_cvlan
        self.service_pol_in = service_pol_in
        self.service_pol_out = service_pol_out
        self.mtu = mtu
        self.bd_id = bd_id
        self.split_horizon = False
        self.svlan_list = ""
        self.cvlan_list = ""
        self.ip = ""
        self.flag_bdid = True
        self.flag_bd_id_l2vpn = False
        self.flag_cos = False
        self.ff_in = ""
        self.ff_out = ''
        self.mpls = False
        self.admin_status = True
        self.switch_mode = ''
        self.dhcp_gw = ''
        self.vlan_unit = ''
        self.vrf_name = ''
        self.igmp = False
        self.vsi_encap = ''
        self.unit = ''
        self.hostname_remote = ''
        self.ifd = ''
        self.ip_helper = ''
        self.list_unit_remote = []

    def get_bd_id_vlan(self, db, cursor, bd_id, hostname):
        try:
            sql = "select BD_ID from ifl where Hostname = '%s' and Unit = '%s' and IFD = 'Vlan'" % (hostname, bd_id)
            cursor.execute(sql)
            list_rows = cursor.fetchall()
            if len(list_rows) < 1:
                self.flag_bdid = True

        except MySQLdb.Error, e:
            print (e)
            db.rollback()

    def get_spi_spo(self, list_unit_vlan_policer):
        for unit_vlan_policer in list_unit_vlan_policer:
            if self.bd_id == str(unit_vlan_policer.unit):
                if self.service_pol_in == '':
                    self.service_pol_in = unit_vlan_policer.service_pol_in
                if self.service_pol_out == '':
                    self.service_pol_out = unit_vlan_policer.service_pol_out
            #print ("unit_vlan: " + str(self.unit) + " spi_vlan: " + self.service_pol_in +
            #       " spo_vlan: " + self.service_pol_out)

    def get_dhcpGW_Vlan_Unit(self, lst_dhcp_relay):
        if len(lst_dhcp_relay) > 0:
            for helper in lst_dhcp_relay:
                if self.bd_id == helper.bd_id:
                    self.dhcp_gw = helper.ip.split(' ')[0]
                    self.vlan_unit = str(helper.unit)
        else:
            print('list dhcp relay is empty')

    def get_list_unit_remote(self, ifd_name, hostname):
        try:
            if self.service == 'l2circuit':
                sql = "select VC_ID, BK_vc_id from l2vpn " \
                      "where Hostname = '%s' and IFL = '%s' " % (hostname, ifd_name + '.' + str(self.unit))
                UNIT.cursor.execute(sql)
                rows = UNIT.cursor.fetchall()
                list_vc_bk_vc = list(map(lambda x: (x[0], x[1]), rows))
                self.get_list_unit_remote_helper(hostname, list_vc_bk_vc)
            elif self.service == 'vpls':
                sql = "select VC_ID, BK_vc_id from l2vpn " \
                      "where Hostname = '%s' and BD_ID = '%s' " % (hostname, self.bd_id)
                UNIT.cursor.execute(sql)
                rows = UNIT.cursor.fetchall()
                list_vc_bk_vc = list(map(lambda x: (x[0], x[1]), rows))
                self.get_list_unit_remote_helper(hostname, list_vc_bk_vc)
            else:
                print("list_unit_remote is not in service l2circuit and vpls")
        except MySQLdb.Error, e:
            print (e)
            print (" in_list_unit_remote")
            UNIT.db.rollback()

    def get_list_unit_remote_helper(self, hostname, list_vc_bk_vc):
        try:
            for element in list_vc_bk_vc:
                vc = element[0]
                bk_vc_id = element[1]
                if bk_vc_id > 0:
                    sql_1 = "select Hostname, BD_ID, IFL from l2vpn " \
                        "where Hostname like '%s' and Hostname != '%s' " \
                        "and (VC_ID = '%s' or BK_vc_id = '%s' or VC_ID = '%s' or BK_vc_id = '%s') " \
                        % (hostname[0:3] + '%', hostname, vc, vc, bk_vc_id, bk_vc_id)
                else:
                    sql_1 = "select Hostname, BD_ID, IFL from l2vpn " \
                            "where Hostname like '%s' and Hostname != '%s' " \
                            "and (VC_ID = '%s' or BK_vc_id = '%s') " \
                            % (hostname[0:3] + '%', hostname, vc, vc)
                # print("sql_1: " + sql_1)
                UNIT.cursor.execute(sql_1)
                lst_tmp = UNIT.cursor.fetchall()
                lst_tmp = list(map(lambda x: (x[0], x[1], x[2]), lst_tmp))
                for temp in lst_tmp:
                    hostname_remote = temp[0]
                    bd_id_tmp = temp[1]
                    if bd_id_tmp == '':
                        ifd_tmp, unit_tmp = temp[2].split('.')
                        sql_2 = "select Hostname, IFD, Unit, SVLAN, CVLAN, " \
                                "IP, Vlan_mapping, Vlan_translate, Service from ifl " \
                                "where Hostname = '%s' and IFD = '%s' and Unit = '%s' " \
                                % (hostname_remote, ifd_tmp, unit_tmp)
                    else:
                        sql_2 = "select Hostname, IFD, Unit, SVLAN, CVLAN, " \
                                "IP, Vlan_mapping, Vlan_translate, Service from ifl " \
                                "where Hostname = '%s' and BD_ID = '%s'" \
                                % (hostname_remote, bd_id_tmp)
                    # print("sql_2 " + sql_2)
                    UNIT.cursor.execute(sql_2)
                    lst_row = UNIT.cursor.fetchall()
                    for row_tmp in lst_row:
                        unit_rmt = UNIT()
                        (unit_rmt.hostname_remote, unit_rmt.ifd,
                         unit_rmt.unit, unit_rmt.svlan, unit_rmt.cvlan,
                         unit_rmt.ip, unit_rmt.vlan_mapping,
                         unit_rmt.vlan_translate, unit_rmt.service) = row_tmp
                        self.list_unit_remote.append(unit_rmt)
        except MySQLdb.Error, e:
            print (e)
            print ("in list unit remote helper")
            UNIT.db.rollback()

    def showdata(self):
        attrs = vars(self)
        print ','.join("%s: %s" % item for item in attrs.items())