import Database
import os
from ACL import ACL
from IFD import IFD
from L2VPN import L2VPN
from Policer import POLICER
from Router import Router
from L2VPN import NEIGHBOR
from VRF import VRF
from Server import Server
from VRFIE import VRFIE
from CFGROUTER import CFGROUTER
from RouteMap import RouteMap
from BGP import BGP
from IFL import IFL
from LSP import LSP
from StaticRoute import StaticRoute
import time
import random


class Main:

    def __init__(self):
        # open database connection
        self.db = Database.Database.db
        # prepare a cursor object using cursor() method
        self.cursor = Database.Database.cursor
        self.path_input = "configuration_template"
        self.path_output = "configuration_created"
        #self.path_input = "/Users/tnhnam/Desktop/du an anh P/template"
        #self.path_output = "/Users/tnhnam/Desktop/du an anh P/router_config"

    def main(self):

        # flag de tim interface dau xa
        flag_create_notation = False
        listRouter = Router.get_host_name()
        file_name_1 = "router_config_asr.conf"
        file_name_2 = "router_config.conf"
        file_name_3 = "router_config_npe.conf"

        hostname_list = ['R7609-ADV-UPE-01','R7609-BTH-UPE-01','R7609-CCH-UPE-01','R7609-CLO-UPE-01',
                         'R7609-HBT-UPE-01','R7609-HVU-UPE-01','R7609-KHW-UPE-01','R7609-TDU-UPE-01',
                         'R7609-TMU-UPE-01','R7609-TTM-UPE-01']

        hostname_list_temp = ['R7606-HMO-UPE-01', 'R7606-THP-UPE-01', 'R7606-TLC-UPE-01', 'R7606-TTR-UPE-01',
                              'R7609-ANT-UPE-01', 'R7609-APD-UPE-01', 'R7609-BMY-UPE-01', 'R7609-BNA-UPE-01',
                              'R7609-PTA-UPE-01', 'R7609-QTR-UPE-01', 'R7609-TCH-UPE-01', 'R7609-TTN-UPE-01']

        list_big_router = ['R7609-TQD-UPE-01', 'R7609-TTD-UPE-01', 'R7609-TBI-UPE-01', 'R7609-HBT-UPE-01', 'R7609-HBT-UPE-02']
        list_NPE = [ 'R7609-CCH-NPE-01','R7609-TMU-NPE-01','R7609-TDU-NPE-01','R7609-BTH-NPE-01',
                     'R7609-CLO-NPE-01','R7609-BQU-NPE-01','R7609-TTM-NPE-01','R7609-LQD-NPE-01','R7609-HVU-NPE-01',
                     'R7609-KHW-NPE-01']
        list_asr = ['ASR9912-TBI-P-01','ASR9912-TBI-P-02','ASR9912-HBT-P-01','ASR9912-HBT-P-02','ASR9912-GDI-P-01','ASR9912-GDI-P-02']
        check_continute = 'y'
        #'THA02SSN','LSN99LLI'
        #'LSN00LLI','THA00THA'
        for hostname in ['THA02SSN']:
            print ("hostname: " + hostname)
            router = Router()
            router.hostname = hostname
            router.get_hostname_type()
            # ADD new code HERE
            lst_log_server = Server.get_list_log_server(hostname)
            list_lsp = LSP.query_data(hostname)

            list_unit_vlan_policer = router.get_list_unit_vlan_policer()
            list_bd_id_ip = router.get_list_bd_id_ip()
            #print ("list_bdid")
            #print (list_bd_id_ip)

            # interface
            list_bd_id = router.get_list_bdid()
            list_bd_id_l2vpn = router.get_list_bd_id_l2vpn()
            list_bd_id_igmp = router.get_list_bd_id_igmp()
            iso_address = router.get_iso_address()

            #23/9 isis export
            dict_exp_isis = router.get_isis_export()

            # add new list_dhcp_relay to support for insert unit to IFD
            lst_dhcp_relay = IFL.query_dhcp_relay(hostname)
            IFD.set_class_paras(iso_address, list_bd_id_igmp, list_bd_id_l2vpn,
                                list_unit_vlan_policer, list_bd_id_ip, router.type, lst_dhcp_relay)

            #list_ifd = IFD.query_data(hostname, flag_create_notation)

            #bo sung ngay 18/9 :chua chay

            list_policer = POLICER.query_policer(hostname)
            cfg_router = CFGROUTER().query_cfg_router(hostname, router.type)

            #move from line 82 to line 89 at Sep-22
            dict_policy_map_used = {}
            list_ifd = IFD.query_data(hostname, flag_create_notation, cfg_router.dict_policy_map, dict_policy_map_used)
            #list static route global 18/9
            list_static_global = StaticRoute.query_data(hostname, '')
            # L3VPN
            vrf_service_list = VRF.query_data(hostname)
            vrfie_list = VRFIE.query_data(vrf_service_list)
            list_all_extomm_from_VRFIE = VRFIE.get_all_extcomm(vrfie_list)

            # get_list_acl
            list_acl = ACL.query_acl(hostname)
            # add new code in huawei
            list_mgmt_acl = ACL.get_list_mgmt_acl(hostname)

            neighbor_list = NEIGHBOR.query_data(hostname, list_ifd)
            # L2VPN
            l2vpn_list = L2VPN.query_data(hostname, list_ifd, router.type)
            l2vpn_list_local = L2VPN.query_vlan_local(hostname, list_bd_id_ip)

            #bo sung ngay 22/9
            list_ccc = L2VPN.query_data_ccc(hostname,list_ifd,router.type)
            # RouteMap
            lst_route_map = RouteMap.query_data(hostname)
            lst_extcomm_bgp = RouteMap.get_lst_extcomm_bgp(hostname)

            # BGP
            BGP.set_router_type(router.type)
            lst_neighbor_group_rr = BGP.get_lst_neighbor_group_bgp(hostname, '0')
            lst_neighbor_group_clients = BGP.get_lst_neighbor_group_bgp(hostname, '1')
            lst_neighbor_group_option_b = BGP.get_lst_neighbor_group_bgp(hostname)
            # add new code in huawei
            lst_bgp_huawei = BGP.query_bgp_HW(hostname)

            # for ifd in list_ifd:
            #     for unit in ifd.list_unit:
            #         if unit.unit1 == 2410:
            #             print(" unit_ip : " + str(unit.ip))
            #print dict_policy_map_used
            #for temp_policy in dict_policy_map_used:
            #    print '---',temp_policy,'----'
            #    dict_policy_map_used[temp_policy].showdata()
            #    if len(dict_policy_map_used[temp_policy].mf_list)>0:
            #        print 'MF list:'
            #        for item_mf in dict_policy_map_used[temp_policy].mf_list:
            #            item_mf.showdata()
            #    if len(dict_policy_map_used[temp_policy].acl_list)>0:
            #        print 'ACL list:'
            #        for item_acl in dict_policy_map_used[temp_policy].acl_list:
            #            item_acl.showdata()
            event_time = "23:" + str(random.randint(0, 59)) + ":" + str(random.randint(0, 59)) + " +0700"
            VRF.writefile(vrf_service_list, l2vpn_list, l2vpn_list_local, vrfie_list,
                          list_all_extomm_from_VRFIE, neighbor_list, list_ifd, list_policer,
                          cfg_router, list_acl, lst_route_map, lst_extcomm_bgp,
                          lst_neighbor_group_rr, lst_neighbor_group_clients, lst_neighbor_group_option_b,
                          event_time, lst_log_server, list_lsp, lst_bgp_huawei,
                          list_mgmt_acl,list_static_global,dict_policy_map_used,list_ccc, dict_exp_isis,
                         file_name_2, self.path_input, self.path_output, hostname)
            #check_continute = raw_input("Do you want to continute: ")
            #if check_continute != 'y':
            #    break


        # execute SQL query using execute() method.
        # cursor.execute("SELECT VERSION()")

        # Fetch a single row using fetchone() method.
        # data = cursor.fetchone()

        # print("Database version : %s " % data)

        # commit your changes in the database
        self.db.commit()

        # disconnect from server
        self.db.close()


# execute the program

start_time = time.time()
Main().main()
print ("time_execution: " + str(time.time() - start_time))
