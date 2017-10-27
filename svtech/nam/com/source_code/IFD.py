import MySQLdb
import ipaddr
from jinja2 import Environment, FileSystemLoader
import Database
from Utils import Utils
import netaddr
from CFGROUTER import POLICYMAP

class IFD:
    db = Database.Database.db
    cursor = Database.Database.cursor
    iso_address = ""
    list_bd_id_igmp = []
    list_bd_id_l2vpn = []
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
        self.type = type_tmp
        self.list_unit = []
        self.admin_status = admin_status
        # add new attribute
        self.native_vlan = native_vlan
        self.flag_core = False
        self.list_bd_id_dup = []
        self.flag_ccc = False

    @staticmethod
    def set_class_paras(iso_address, list_bd_id_igmp, list_bd_id_l2vpn,
                            list_unit_vlan_policer, list_bd_id_ip, router_type, lst_dhcp_relay):
        IFD.iso_address = iso_address
        IFD.list_bd_id_igmp = list_bd_id_igmp
        IFD.list_bd_id_l2vpn = list_bd_id_l2vpn
        IFD.list_unit_vlan_policer = list_unit_vlan_policer
        IFD.list_bd_id_ip = list_bd_id_ip
        IFD.router_type = router_type
        IFD.lst_dhcp_relay = lst_dhcp_relay

    @staticmethod
    def query_data(hostname, flag_create_notation, dict_policy_map, dict_policy_map_used, irb_df_dict):
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
                ifd.insert_unit(dict_policy_map, dict_policy_map_used, irb_df_dict)

            # convert list_ifd to new list_ifd with new flex_service (relation parent_link in this list)
            list_ifd = list(map(lambda x: x.get_new_ifd_with_flex_service(list_ifd), list_ifd))
            return list_ifd
        except MySQLdb.Error, e:
            print (e)
            IFD.db.rollback()

    @staticmethod
    def query_data_df(hostname, vrf_df_dict):
        try:
            IFD.hostname = hostname
            dict_irb = {}
            for key in vrf_df_dict:
                sql = "select Unit from ifl " \
                      "where Hostname = '%s' and VRF_Name = '%s' and IFD='Vlanif" % (hostname,key)
                IFD.cursor.execute(sql)
                list_rows = IFD.cursor.fetchall()
                dict_irb[list_rows[0]] = list_rows[1]
            return dict_irb
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
            unit.classifier = Utils.change_name_classifier(info[26])
            unit.df_classifier = Utils.change_name_classifier(info[27])
            unit.arp_exp = info[28]/60
            if (unit.ip == '') and (info[29]):
                unit.trust_1p = info[29]
            if unit.bd_id in ifd.list_bd_id_dup:
                unit.bd_dup_notation=True
            # only get the unit from IFD.list_unit_vlan_policer
            unit.get_spi_spo(IFD.list_unit_vlan_policer)
            #unit.get_dhcpGW_Vlan_Unit(IFD.lst_dhcp_relay)
            # flag_create_notation is used or not
            if IFD.flag_create_notation:
                unit.get_list_unit_remote(ifd.name, IFD.hostname)
            # set flag_core for ifd
            if unit.service == 'CORE':
                if ifd.flag_core == False:
                    ifd.flag_core = True
            # print ("ifd: " + ifd.name + " mx_ifd: " + ifd.mx_ifd + " unit: " + str(unit.unit1) + " spi_in: " + unit.service_pol_in + " spo: " + unit.service_pol_out )
            return unit
        else:
            return None

    @staticmethod
    def find_mx_ifd(info,hostname):
        try:

            sql = "select IFD.mx_ifd,IFL.Unit1 from ifl inner join ifd on ifd.name=ifl.ifd and ifd.hostname=ifl.hostname " \
                  "where (left('%s',position('.' in '%s')-1)= ifl.IFD) and " \
                  "(right('%s',length('%s')-position('.' in '%s')) = " \
                  "Convert(ifl.Unit,CHAR(45))) and ifl.hostname='%s'" % (info,info,info,info,info,hostname)
            IFD.cursor.execute(sql)
            list_rows = IFD.cursor.fetchall()
            new_ifl=list_rows[0][0]+'.'+str(list_rows[0][1])
            return new_ifl
        except MySQLdb.Error, e:
            print (e)
            IFD.db.rollback()

    @staticmethod
    def insert_policy_map_used(tmp_unit, dict_policy_map, dict_policy_map_used):
        tmp_policy_map = POLICYMAP()
        if tmp_unit.service=='vpls':
            #print 'Tao policy map cho vpls',tmp_unit.unit1 , tmp_unit.ifd
            #print tmp_unit.ff_in, (tmp_unit.ff_in in dict_policy_map) , (tmp_unit.ff_in not in dict_policy_map_used)
            if (tmp_unit.ff_in in dict_policy_map) and ((tmp_unit.ff_in + '/vpls') not in dict_policy_map_used):
                #print 'Dang policy map cho vpls'
                tmp_policy_map = POLICYMAP(tmp_unit.ff_in)
                tmp_policy_map.df_fc = Utils.change_name_classifier(tmp_unit.df_classifier)
                tmp_policy_map.df_lp = 'low'
                tmp_policy_map.mf_list = dict_policy_map[tmp_unit.ff_in].mf_list
                tmp_policy_map.acl_list = dict_policy_map[tmp_unit.ff_in].acl_list
                tmp_policy_map.family_type = 'vpls'
                dict_policy_map_used[tmp_unit.ff_in+'/vpls'] = tmp_policy_map
            if (tmp_unit.ff_out in dict_policy_map) and ((tmp_unit.ff_out + '/vpls') not in dict_policy_map_used):
                tmp_policy_map = POLICYMAP(tmp_unit.ff_out)
                tmp_policy_map.df_fc = Utils.change_name_classifier(tmp_unit.df_classifier)
                tmp_policy_map.df_lp = 'low'
                tmp_policy_map.mf_list = dict_policy_map[tmp_unit.ff_out].mf_list
                tmp_policy_map.acl_list = dict_policy_map[tmp_unit.ff_out].acl_list
                tmp_policy_map.family_type = 'vpls'
                dict_policy_map_used[tmp_unit.ff_out + '/vpls'] = tmp_policy_map
        elif tmp_unit.service=='l2circuit':
            #print 'Tao policy map cho l2circuit',tmp_unit.unit1 , tmp_unit.ifd
            if (tmp_unit.ff_in in dict_policy_map) and ((tmp_unit.ff_in + '/l2circuit') not in dict_policy_map_used):
                #print 'Dang tao policy map cho l2circuit'
                tmp_policy_map = POLICYMAP(tmp_unit.ff_in)
                tmp_policy_map.df_fc = Utils.change_name_classifier(tmp_unit.df_classifier)
                tmp_policy_map.df_lp = 'low'
                tmp_policy_map.mf_list = dict_policy_map[tmp_unit.ff_in].mf_list
                tmp_policy_map.acl_list = dict_policy_map[tmp_unit.ff_in].acl_list
                tmp_policy_map.family_type = 'l2circuit'
                dict_policy_map_used[tmp_unit.ff_in] = tmp_policy_map
            if (tmp_unit.ff_out in dict_policy_map) and (tmp_unit.ff_out not in dict_policy_map_used):
                tmp_policy_map = POLICYMAP(tmp_unit.ff_out)
                tmp_policy_map.df_fc = Utils.change_name_classifier(tmp_unit.df_classifier)
                tmp_policy_map.df_lp = 'low'
                tmp_policy_map.mf_list = dict_policy_map[tmp_unit.ff_out].mf_list
                tmp_policy_map.acl_list = dict_policy_map[tmp_unit.ff_out].acl_list
                tmp_policy_map.family_type = 'l2circuit'
                dict_policy_map_used[tmp_unit.ff_out + '/l2circuit'] = tmp_policy_map
        else:
            #print 'Tao policy map cho l3', tmp_unit.unit1, tmp_unit.ifd
            if (tmp_unit.ff_in in dict_policy_map) and ((tmp_unit.ff_in + '/inet') not in dict_policy_map_used):
                print 'Dang tao policy map cho l3'
                tmp_policy_map = POLICYMAP(tmp_unit.ff_in)
                tmp_policy_map.df_fc = Utils.change_name_classifier(tmp_unit.df_classifier)
                tmp_policy_map.df_lp = 'low'
                tmp_policy_map.mf_list = dict_policy_map[tmp_unit.ff_in].mf_list
                tmp_policy_map.acl_list = dict_policy_map[tmp_unit.ff_in].acl_list
                tmp_policy_map.family_type = 'inet'
                dict_policy_map_used[tmp_unit.ff_in+ '/inet'] = tmp_policy_map
            if (tmp_unit.ff_out in dict_policy_map) and ((tmp_unit.ff_out+ '/inet') not in dict_policy_map_used):
                tmp_policy_map = POLICYMAP(tmp_unit.ff_out)
                tmp_policy_map.df_fc = Utils.change_name_classifier(tmp_unit.df_classifier)
                tmp_policy_map.df_lp = 'low'
                tmp_policy_map.mf_list = dict_policy_map[tmp_unit.ff_out].mf_list
                tmp_policy_map.acl_list = dict_policy_map[tmp_unit.ff_out].acl_list
                tmp_policy_map.family_type = 'inet'
                tmp_policy_map.showdata()
                dict_policy_map_used[tmp_unit.ff_out+ '/inet'] = tmp_policy_map

    @staticmethod
    def convert_info_unit1(info, ifd, dict_policy_map, dict_policy_map_used, irb_df_dict):

        ip_helper_tmp = info[19]
        if (ifd.name != 'Vlanif') | (ip_helper_tmp == ''):
            unit = UNIT(info[0], info[1], info[2], info[3], info[4], info[5],
                        info[6], info[7], info[8], info[9], info[10], info[11], info[12])
            # convert ip
            network = info[13]
            if network != '':
                unit.ip = UNIT.insert_list_ip(info,IFD.hostname)
                #print ifd.name, unit.ip,network
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
            unit.classifier = Utils.change_name_classifier(info[26])
            unit.df_classifier = Utils.change_name_classifier(info[27])
            if (ifd.name != 'Vlanif') and (unit.unit in irb_df_dict) and (unit.df_classifier == ''):
                unit.classifier = irb_df_dict[unit.unit]
            unit.arp_exp = info[28] / 60
            if (unit.ip == '') and (info[29]):
                unit.trust_1p = info[29]
            #print 'info[36]:',info[36]
            unit.trust_upstream = info[36]
            unit.routing_type = info[37]
            if unit.bd_id in ifd.list_bd_id_dup:
                unit.bd_dup_notation = True
            # only get the unit from IFD.list_unit_vlan_policer
            unit.get_spi_spo(IFD.list_unit_vlan_policer)
            # unit.get_dhcpGW_Vlan_Unit(IFD.lst_dhcp_relay)
            # flag_create_notation is used or not
            if IFD.flag_create_notation:
                unit.get_list_unit_remote(ifd.name, IFD.hostname)
            # set flag_core for ifd
            if unit.service == 'CORE':
                if ifd.flag_core == False:
                    ifd.flag_core = True
            IFD.insert_policy_map_used(unit, dict_policy_map, dict_policy_map_used)
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

    def insert_unit(self, dict_policy_map, dict_policy_map_used, irb_df_dict):
        try:
            #print("insert_unit_to " + "ifd_mxifd: " + ifd.mx_ifd + " flag_default: " + str(ifd.flag_default) + " flag_l2circuit: "
            #      + str(ifd.flag_default_l2circuit) + " flag_vpls: " + str(ifd.flag_default_vpls)
            #      + " flag_svlan_untagged: " + str(ifd.flag_svlan_untagged) + " parent_link: " + ifd.parent_link)

            sql = "select Unit1, Description, Service, SVLAN, CVLAN, Vlan_mapping, " \
                  "Vlan_translate, Vlan_map_svlan, Vlan_map_cvlan, Service_pol_in, Service_pol_out, " \
                  "MTU, BD_ID, IP, Split_horizon, FF_in, " \
                  "MPLS, Admin_status, Switch_mode, IP_helper, " \
                  "VRF_Name, IGMP, VSI_encap, Unit, FF_out, DHCP_GW, " \
                  "Classifier, DF_classifier,ARP_exp,Trust_8021p,VRRP_group,VRRP_vip,VRRP_prio,VRRP_delay,VRRP_track," \
                  "VRRP_reduce,Trust_upstream,Routing_type " \
                  "from ifl " \
                  "where Hostname = '%s' and IFD = '%s'" % (IFD.hostname, self.name)
            IFD.cursor.execute(sql)
            list_rows = IFD.cursor.fetchall()

            sql = "select BD_ID,count(BD_ID) from ifl where hostname='%s' and " \
                  "IFD = '%s' and BD_ID!='' group by BD_ID" % (IFD.hostname,self.name)
            IFD.cursor.execute(sql)
            list_rows_1 = IFD.cursor.fetchall()
            #print list_rows_1
            self.check_ccc_eth()
            if self.flag_ccc:
                self.list_unit = [UNIT()]
            else:
                self.list_bd_id_dup = list(map(lambda x: x[0], list(filter(lambda x: x[1] > 1, list_rows_1))))
                #print self.list_bd_id_dup

                list_unit_temp = list(map(lambda x: IFD.convert_info_unit1(x, self, dict_policy_map, dict_policy_map_used, irb_df_dict), list_rows))
                # filter nhung phan tu None trong list_unit_temp
                self.list_unit = list(filter(lambda x: x is not None, list_unit_temp))
                # bo sung vao list_unit truong hop loopback cho dhcp relay
                #self.insert_to_list_unit_dhcp_relay()
                #check special case (ccc)


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

    def check_ccc_eth(self):
        try:
            sql_ccc_eth = "select IFD from ifl where Hostname = '%s' and IFD = '%s' and Service = 'ccc' " \
                      % (IFD.hostname,self.name)
            IFD.cursor.execute(sql_ccc_eth)
            list_rows = IFD.cursor.fetchall()
            if len(list_rows)>0:
                self.flag_ccc = True

        except MySQLdb.Error, e:
            print (e)
            IFD.db.rollback()

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
        #self.ip = ""
        self.ip =[]
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
        self.classifier = ''
        self.df_classifier = ''
        self.arp_exp=0
        self.trust_1p = False
        self.bd_dup_notation=False
        self.trust_upstream = False
        self.routing_type = ''

    @staticmethod
    def insert_list_ip(info,hostname):
        temp_list_ip = info[13].split('/')
        list_ip = list(map(lambda x: UNIT_IP(Utils.convert_ip(x)), temp_list_ip))
        #print 'Kiem tra:',list_ip

        if info[30]!='':
            temp_list_group = info[30].split('/')
            temp_list_vip = info[31].split('/')
            temp_list_pri = info[32].split('/')
            temp_list_holdtime = info[33].split('/')
            temp_list_track = info[34].split('/')
            temp_list_reduce = info[35].split('/')
            #if info[0] == 2642:
                #print temp_list_group,temp_list_vip,temp_list_pri,temp_list_holdtime,temp_list_track,temp_list_reduce
            for item_vrrp in temp_list_group:
                temp_vrrp_group = VRRP()
                temp_vrrp_group.group_id = item_vrrp
                temp_list_vip_filter = list(filter(lambda x: x.startswith(item_vrrp + '_'), temp_list_vip))
                #print ' Gia tri vip filter:',temp_list_vip_filter
                #print temp_list_vip_filter
                #print temp_list_vip_filter
                if len(temp_list_vip_filter) > 0:
                    #print 'Dang xu ly:',temp_list_vip_filter[0].split('_')[1]
                    temp_vrrp_group.vip.append(temp_list_vip_filter[0].split('_')[1])
                #print 'Da xu ly:',temp_vrrp_group.group_id,temp_vrrp_group.vip
                temp_list_pri_filter = list(filter(lambda x: x.startswith(item_vrrp), temp_list_pri))
                if len(temp_list_pri_filter)>0:
                    temp_vrrp_group.vrrp_pri = temp_list_pri_filter[0].split('_')[1]
                else:
                    temp_vrrp_group.vrrp_pri = '100'
                temp_list_hold_filter = list(filter(lambda x: x.startswith(item_vrrp), temp_list_holdtime))
                if len(temp_list_hold_filter) > 0:
                    temp_vrrp_group.vrrp_holdtime = temp_list_hold_filter[0].split('_')[1]
                else:
                    temp_vrrp_group.vrrp_holdtime = '0'
                temp_list_track_filter = list(filter(lambda x: x.startswith(item_vrrp), temp_list_track))
                if len(temp_list_track_filter) > 0:
                    temp_vrrp_group.vrrp_track_intf = IFD.find_mx_ifd(temp_list_track_filter[0].split('_')[1],hostname)
                temp_list_reduce_filter = list(filter(lambda x: x.startswith(item_vrrp), temp_list_reduce))
                if len(temp_list_reduce_filter) > 0:
                    temp_vrrp_group.vrrp_reduce = temp_list_track_filter[0].split('_')[1]
                for item_ip in list_ip:
                    ip = netaddr.IPNetwork(item_ip.ip)
                    #print 'IP:',ip
                    #print 'Network:',ip.network
                    #print 'Broadcast:',ip.broadcast
                    #temp_vrrp_group.showdata()
                    #print temp_list_vip
                    for item_vip in temp_list_vip_filter:

                        if (netaddr.IPAddress(item_vip.split('_')[1]) >= netaddr.IPAddress(ip.network)) \
                                and (netaddr.IPAddress(item_vip.split('_')[1])< ip.broadcast):
                            item_ip.vrrp_group.append(temp_vrrp_group)
                            #print item_ip.ip
                            #item_ip.vrrp_group

           # for item_ip in list_ip:
                #print item_ip.ip
                #for item_group in item_ip.vrrp_group:
                    #item_group.showdata()
        return list_ip

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


class UNIT_IP:
    def __init__(self, ip=''):
        self.ip = ip
        self.vrrp_group = []



class VRRP:
    def __init__(self):
        self.group_id =''
        self.vip = []
        self.vrrp_pri = ''
        self.vrrp_holdtime = 0
        self.vrrp_track_intf = ''
        self.vrrp_reduce = 0

    def showdata(self):
        attrs = vars(self)
        print ','.join("%s: %s" % item for item in attrs.items())