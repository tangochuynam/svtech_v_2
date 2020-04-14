import datetime

import MySQLdb
import ipaddress as ip
import re
from jinja2 import Environment, FileSystemLoader

from Database import Database
from BGP import BGP
from DHCP import DHCP
from IFL import INTERFACE_UNIT
from StaticRoute import StaticRoute

from numpy.core import unicode

class SERVERGROUP:
    def __init__(self, name, list_helper, name_intf, list_interface):
        self.name = name
        self.list_helper = list_helper
        self.name_intf = name_intf
        self.list_interface = list_interface


class VRFWITHIPHEPLPER:
    db = Database.db
    cursor = Database.cursor

    def __init__(self):
        self.name = ""
        self.list_server_intf_group = []

    @staticmethod
    def query_vrf_with_iphelper(hostname):
        try:
            sql = "select Name from vrf where Hostname = '%s' and DHCP_Relay = true" % hostname
            VRFWITHIPHEPLPER.cursor.execute(sql)
            list_rows = VRFWITHIPHEPLPER.cursor.fetchall()
            list_vrf = list(map(lambda x: x[0], list_rows))

            list_vrf_with_ip_helper = []
            for vrf in list_vrf:
                vrf_with_helper = VRFWITHIPHEPLPER()
                vrf_with_helper.name = vrf
                sql_helper = "select IP_helper from ifl where Hostname = '%s' and VRF_Name = '%s' group by IP_helper" \
                             % (hostname, vrf)
                VRFWITHIPHEPLPER.cursor.execute(sql_helper)
                list_rows_helper = VRFWITHIPHEPLPER.cursor.fetchall()
                list_ip_helper = list(map(lambda x: x[0], list_rows_helper))

                dict_temp = VRFWITHIPHEPLPER.extract_server_group(list_ip_helper)

                sql_interface = "select ifl.IP_helper, ifd.MX_IFD, ifl.Unit1  from ifl inner join ifd " \
                                "on ifl.Hostname = ifd.Hostname and ifl.ifd = ifd.Name " \
                                "where ifl.VRF_Name = '%s' and ifl.Hostname = '%s' " % (vrf, hostname)
                VRFWITHIPHEPLPER.cursor.execute(sql_interface)
                list_rows_intf = VRFWITHIPHEPLPER.cursor.fetchall()
                vrf_with_helper.list_server_intf_group = VRFWITHIPHEPLPER.extract_interface_group(list_rows_intf, dict_temp)

                #for temp in vrf_with_helper.list_server_intf_group:
                #    print ("name_intf:" + temp.name_intf)
                ##    for interface_temp in temp.list_interface:
                #        print ("interface_name: " + interface_temp)
                list_vrf_with_ip_helper.append(vrf_with_helper)
            return list_vrf_with_ip_helper
        except MySQLdb.Error as e:
            print (e)
            VRFWITHIPHEPLPER.db.rollback()

    @staticmethod
    def query_vrf_with_iphelper_1(hostname, vrf):
        try:

            vrf_with_helper = VRFWITHIPHEPLPER()
            vrf_with_helper.name = vrf
            #Update last night
            sql_helper = "select IP_helper from ifl where Hostname = '%s' and VRF_Name = '%s' and IP_helper!='' " \
                         "group by IP_helper" \
                         % (hostname, vrf)
            VRFWITHIPHEPLPER.cursor.execute(sql_helper)
            list_rows_helper = VRFWITHIPHEPLPER.cursor.fetchall()
            list_ip_helper = list(map(lambda x: x[0], list_rows_helper))

            dict_temp = VRFWITHIPHEPLPER.extract_server_group(list_ip_helper)

            sql_interface = "select ifl.IP_helper, ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                            "on ifl.Hostname = ifd.Hostname and ifl.ifd = ifd.Name " \
                            "where ifl.VRF_Name = '%s' and ifl.Hostname = '%s' and ifd.MX_IFD!='';" % (vrf, hostname)
            VRFWITHIPHEPLPER.cursor.execute(sql_interface)
            list_rows_intf = VRFWITHIPHEPLPER.cursor.fetchall()
            vrf_with_helper.list_server_intf_group = VRFWITHIPHEPLPER.extract_interface_group(list_rows_intf,
                                                                                              dict_temp)
            # for temp in vrf_with_helper.list_server_intf_group:
            #    print ("name_intf:" + temp.name_intf)
            ##    for interface_temp in temp.list_interface:
            #        print ("interface_name: " + interface_temp)
            return vrf_with_helper
        except MySQLdb.Error as e:
            print (e)
            VRFWITHIPHEPLPER.db.rollback()

    @staticmethod
    def extract_interface_group(list_rows_intf, dict_temp):
        for row in list_rows_intf:
            keydict = row[0]
            if row[1] is None:
                print("ifd_null is: " + str(row[3]))
                raise ValueError(" MX_IFD is null")
            name = row[1] + '.' + str(row[2])
            if keydict in dict_temp:
                dict_temp[keydict].name_intf = 'interface-' + dict_temp[keydict].name
                dict_temp[keydict].list_interface.append(name)

        #for key, value in dict_temp.items():
            #print("key:" + key)
            #print("name_intf_in_extraact_interface_group:" + dict_temp[key].name_intf )
            #for inter_name in value.list_interface:
            #   print("inter_name_in_extract_interface_group:" + inter_name)
        list_intf_server_group = dict_temp
        return list_intf_server_group.values()

    @staticmethod
    def extract_server_group(list_ip_helper):
        dict_ip_helper = {}
        index = 1
        for ip_helper in list_ip_helper:
            key_dict = ip_helper
            # print ("key_dict_in_extract_server_group: " + key_dict)
            server_group = SERVERGROUP(str(index), key_dict.split(), "", [])
            dict_ip_helper[key_dict] = server_group
            index += 1
        return dict_ip_helper

    @staticmethod
    def writefile(list_vrf_with_ip_helper, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        vrf_with_helper = {'list_vrf_with_ip_helper': list_vrf_with_ip_helper}
        file_ouput = path_output + "/" + hostname
        with open(file_ouput, 'a') as f:
            f_txt = template_env.get_template(file_name).render(vrf_with_helper)
            f.write(f_txt)
        print("write successful")


class VRF:
    db = Database.db
    cursor = Database.cursor
    hostname = ""

    def __init__(self):
        self.name = ""
        self.name_out = ""
        self.rd = ""
        self.hostname = ""
        self.interface_unit = []
        self.list_dhcp = []
        self.vrf_with_ip_helper = VRFWITHIPHEPLPER()
        self.list_static_route = []
        self.list_bgp = []
        self.dhcp_relay = False
        self.dhcp_server = False
        self.static_routing = False
        self.bgp = False
        self.ospf = False
        self.frr = False
        self.exp_extcom = ''
        self.imp_extcom = ''
        self.description = ''

    @staticmethod
    def query_vrf_on_ifl():
        try:
            sql = "select VRF_Name FROM ifl where IP_helper != '' and Hostname like '%s'  group by VRF_Name;" % VRF.hostname
            VRF.cursor.execute(sql)
            list_rows = VRF.cursor.fetchall()

        except MySQLdb.Error as e:
            print (e)
            VRF.db.rollback()

    @staticmethod
    def get_list_dhcp(vrf_name):
        try:
            sql = "select Name, NW, GW, DNS from dhcp where Hostname = '%s' and VRF_Name = '%s';" % (VRF.hostname, vrf_name)
            VRF.cursor.execute(sql)
            list_rows = VRF.cursor.fetchall()
            #if list_rows is None:
             #   return []
            #else:
            list_dhcp = list(map(lambda x: VRF.create_data_dhcp(x), list_rows))
            return list_dhcp
        except MySQLdb.Error as e:
            print (e)
            VRF.db.rollback()

    @staticmethod
    def create_data_dhcp(dhcp_obj):
        dhcp = DHCP()
        dhcp.name = dhcp_obj[0]
        network = dhcp_obj[1]
        host, subnet = network.strip().split()
        subnet_mask = host + '/' + subnet
        network_ipv4 = ip.ip_network(unicode(subnet_mask))
        dhcp.network = str(network_ipv4)
        dhcp.gateway = dhcp_obj[2]
        dhcp.dns = dhcp_obj[3]
        dhcp.low = str(network_ipv4[2])
        dhcp.high = str(network_ipv4[-2])
        return dhcp


    @staticmethod
    def query_data(hostname):
        try:
            VRF.hostname = hostname
            print ("coming into SQL")
            list_hostname_write = []
            sql_query = "select * from vrf where Hostname = '%s'" % hostname
            VRF.cursor.execute(sql_query)
            # handle the data
            list_rows = VRF.cursor.fetchall()
            list_service = VRF.extract_data(list_rows)
            return list_service
        except MySQLdb.Error as e:
            print (e)
            # rollback in case there is any error
            VRF.db.rollback()

    @staticmethod
    def extract_data(list_rows):
        list_service = []
        print("number of vrf:" + str(len(list_rows)))

        for row in list_rows:
            data = VRF()
            name = row[0].decode()
            #print("line 236 trong vrf.py:", name)
            if ('(' in name) | (')' in name)| ('&' in name) | ('"' in name):
                data.name_out = '-'.join(re.split("[()&\"]", name))
            else:
                data.name_out = name
            data.name = name
            data.hostname = row[1]
            data.rd = row[2]
            data.dhcp_server = row[3]
            data.dhcp_relay = row[4]
            data.static_routing = row[5]
            data.bgp = row[6]
            data.ospf = row[7]
            data.frr = row[12]
            data.exp_extcom = row[13]
            data.imp_extcom = row[14]
            data.description = row[15]
            data.interface_unit = INTERFACE_UNIT.query_list_new_ifl_vrf(data.hostname, data.name)
            if data.dhcp_server:
                data.list_dhcp = VRF.get_list_dhcp(data.name)
            if data.dhcp_relay:
                data.vrf_with_ip_helper = VRFWITHIPHEPLPER.query_vrf_with_iphelper_1(data.hostname, data.name)
            if data.static_routing:
                data.list_static_route = StaticRoute.query_data(data.hostname, data.name)
            if data.bgp:
                data.list_bgp = BGP.query_data(data.hostname, data.name)
            #for server_intf_group in data.vrf_with_ip_helper.list_server_intf_group:
            #   print ("server_name: " + server_intf_group.name)
            #    for iphelper in server_intf_group.list_helper:
            #        print ("ip_helper: " + iphelper )
            list_service.append(data)
        return list_service

    @staticmethod
    def query_data_df(hostname):
        try:
            VRF.hostname = hostname
            print ("coming into SQL")
            list_hostname_write = []
            sql_query = "select Name,Classifier from vrf where Hostname = '%s' and Classifier!=''" % hostname
            VRF.cursor.execute(sql_query)
            # handle the data
            list_rows = VRF.cursor.fetchall()
            list_service = {x[0]: x[1] for x in list_rows}
            return list_service
        except MySQLdb.Error as e:
            print (e)
            # rollback in case there is any error
            VRF.db.rollback()

    @staticmethod
    def writefile(vrf_service_list, l2vpn_list, l2vpn_list_local, vrfie_list, list_all_extomm_from_VRFIE,
                  neighbor_list, list_ifd, list_policer, cfg_router, list_acl, lst_route_map, lst_extcomm_bgp,
                  lst_neighbor_group_rr, lst_neighbor_group_clients, lst_neighbor_group_option_b,
                  event_time, lst_log_server, list_lsp, lst_bgp_huawei,list_mgmt_acl,list_static_global,
                  dict_policy_map_used,list_ccc, dict_exp_isis, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        routing_instances = {'service_list': vrf_service_list, 'l2vpn_list': l2vpn_list, 'l2vpn_list_local': l2vpn_list_local,
                             'vrfie_list': vrfie_list, 'list_all_extcomm': list_all_extomm_from_VRFIE, 'neighbor_list': neighbor_list,
                             'list_ifd': list_ifd, 'list_policer': list_policer,
                             'cfg_router': cfg_router, 'list_acl': list_acl, "event_time": event_time,
                             'lst_route_map': lst_route_map, 'lst_extcomm_bgp': lst_extcomm_bgp,
                             'lst_neighbor_group_clients': lst_neighbor_group_clients,
                             'lst_neighbor_group_rr': lst_neighbor_group_rr,
                             'lst_neighbor_group_option_b': lst_neighbor_group_option_b,
                             'lst_log_server': lst_log_server,
                             'list_lsp': list_lsp,
                             'lst_bgp_huawei': lst_bgp_huawei,
                             'list_mgmt_acl': list_mgmt_acl,
                             'list_static_global': list_static_global,
                             'dict_policy_map_used':dict_policy_map_used,
                             'list_ccc':list_ccc,
                             'dict_exp_isis':dict_exp_isis}
        file_ouput = path_output + "/" + hostname + "-" + '-'.join(str(datetime.datetime.now()).split(":")) + ".txt"
        print('line 310 in vrf.py:',routing_instances)
        with open(file_ouput, 'w') as f:
            f_txt = template_env.get_template(file_name).render(routing_instances)
            f.write(f_txt)
        print("write successful")

    @staticmethod
    def writefile_local(vrf_service_list, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        routing_instances = {'service_list': vrf_service_list}
        file_ouput = path_output + "/" + hostname
        with open(file_ouput, 'a') as f:
            f_txt = template_env.get_template(file_name).render(routing_instances)
            f.write(f_txt)
        print("write successful")
