import MySQLdb

from Database import Database
import Utils

class INTERFACE_UNIT:

    db = Database.db
    cursor = Database.cursor

    def __init__(self, mx_ifd, unit1, bd_id, stitching):
        if mx_ifd is None:
            self.mx_ifd = ''
        else:
            self.mx_ifd = mx_ifd
        self.name = self.mx_ifd + "." + str(unit1)
        self.bd_id = bd_id
        self.stitching = stitching
        self.ip_helper_list = []
        self.unit1 = unit1

    @staticmethod
    def query_data(hostname, bd_id, list_ifd):
        try:
            sql_query = ("select ifd.MX_IFD, ifl.Unit1, ifl.BD_ID, ifl.Stitching, ifl.IP from ifl inner join ifd "
                         "on ifl.IFD = IFD.Name and ifl.Hostname = ifd.Hostname "
                         "where ifl.Hostname = '%s' and IFL.BD_ID = '%s'and ifd.MX_IFD!=''"
                         "group by ifd.MX_IFD") % \
                        (hostname, bd_id)
            INTERFACE_UNIT.cursor.execute(sql_query)
            list_rows = INTERFACE_UNIT.cursor.fetchall()
            #if bd_id == 'VLAN-2501':
            #    print('line 32 in ifl.py:',list_rows,bd_id)
            data = INTERFACE_UNIT.extract_data(list_rows, list_ifd)
            #print('line 36 in ifl.py:',data)
            return data
        except MySQLdb.Error as e:
            print(e)
            INTERFACE_UNIT.db.rollback()

    @staticmethod
    def extract_data(list_rows, list_ifd):
        return list(map(lambda x: INTERFACE_UNIT.change_unit1_interface_unit(x, list_ifd), list_rows))

    @staticmethod
    def query_data_new_ifl(ifd, unit, list_ifd, service_name):
        try:
            #print("ifd: " + ifd + " unit: " + unit)
            # sql = ("select ifd.MX_IFD, ifl.Unit1 from ifl inner join ifd "
            #        "on ifl.IFD = ifd.Name and ifl.Hostname = ifd.Hostname "
            #        "where ifl.Hostname='%s' and ifl.IFD='%s' and ifl.Unit = '%s' and ifd.MX_IFD!='';") % \
            #       (hostname, ifd, unit)
            # INTERFACE_UNIT.cursor.execute(sql)
            # row = INTERFACE_UNIT.cursor.fetchall()
            row = INTERFACE_UNIT.get_service_list(list_ifd, service_name, (ifd, unit))
            if len(row) > 0:
                mx_ifd_temp = row[0][0]
                #print ("name_mx_ifd: " + mx_ifd_temp)
                ifd_filter = list(filter(lambda x: x.mx_ifd == mx_ifd_temp,  list_ifd))
                #print 'Gia tri IFD_FILTER:',ifd_filter
                if ifd_filter[0].flag_default & ifd_filter[0].flag_default_l2circuit:
                    return row[0][0] + ".0"
                else:
                    return row[0][0] + "." + str(row[0][1])
            else:
                return ''
        except MySQLdb.Error as e:
            print(e)
            INTERFACE_UNIT.db.rollback()

    @staticmethod
    def query_list_new_ifl_vrf(hostname, vrf_name):
        try:
            sql = ("select ifd.MX_IFD, ifl.Unit1, ifl.IP_helper from ifl inner join ifd "
                   "on ifl.IFD = ifd.Name and ifl.Hostname = ifd.Hostname "
                   "where ifl.Hostname='%s' and ifl.VRF_Name='%s' and ifd.MX_IFD !='' group by ifd.MX_IFD;") % \
                  (hostname, vrf_name)
            INTERFACE_UNIT.cursor.execute(sql)
            list_rows = INTERFACE_UNIT.cursor.fetchall()
            return list(map(lambda x: Utils.Utils.convert(x), list_rows))
        except MySQLdb.Error as e:
            print(e)
            INTERFACE_UNIT.db.rollback()


    @staticmethod
    def convert(x):
        interface_unit = INTERFACE_UNIT(x[0], x[1], "", "")
        interface_unit.ip_helper_list = x[2].split(' ')
        return interface_unit



    @staticmethod
    def change_unit1_interface_unit(x, list_ifd):
        mx_ifd_temp = x[0]
        unit1 = x[1]
        # print ("type: " +str(type(x)))
        #print ("line 98 in ifl.py mx_ifd: " + mx_ifd_temp+ str(unit1))
        ifd_filter = list(filter(lambda ifd: ifd.mx_ifd == mx_ifd_temp, list_ifd))
        #print("line 100 in ifl.py ifd_filter: ",ifd_filter)
        if ifd_filter[0].flag_default & ifd_filter[0].flag_default_vpls:
            unit1 = 0
        return INTERFACE_UNIT(x[0], unit1, x[2], x[3])

    @staticmethod
    def get_service_list(list_ifd, service, info):
        service_list = []
        if service == 'vrf':
            for ifd in list_ifd:
                units = list(filter(lambda unit: unit.vrf_name == info, ifd.list_unit))
                service_list.extend(list(map(lambda unit: (ifd.mx_ifd, unit.unit1, unit.ip_helper), units)))
            service_list = list(map(lambda x: Utils.Utils.convert(x), service_list))
        elif service == 'l2vpn':
            for ifd in list_ifd:
                units = list(filter(lambda unit: unit.bd_id == info, ifd.list_unit))
                service_list.extend(list(map(lambda unit: (ifd.mx_ifd, unit.unit1, unit.bd_id, unit.stitching, unit.ip), units)))
            service_list = INTERFACE_UNIT.extract_data(service_list, list_ifd)
        elif service == 'ccc':
            for ifd in list_ifd:
                units = list(filter(lambda unit: unit.service.startswith("ccc") and unit.ccc_name == info, ifd.list_unit))
                service_list.extend(list(map(lambda unit: (ifd.mx_ifd, unit.unit1), units)))
        elif service == 'neighbor':
            for ifd in list_ifd:
                #units = list(filter(lambda unit: unit.ifd == info[0] and unit.unit == info[1], ifd.list_unit))
                units = list(filter(lambda unit: unit.old_ifl[0] == info[0]+'.'+str(info[1]), ifd.list_unit))
                service_list.extend(list(map(lambda unit: (ifd.mx_ifd, unit.unit1), units)))
        else:
            raise ValueError(f"service: {service} is not defined")
        return service_list


class IFL:
    db = Database.db
    cursor = Database.cursor

    def __init__(self, ip="", unit="", bd_id="", vrf_name="", ip_helper=""):
        self.ip = ip
        self.unit = unit
        self.bd_id = bd_id
        self.vrf_name = vrf_name
        self.ip_helper = ip_helper
        # self.description = ""
        # self.service = ""
        # self.routing_type = ""
        # self.isis_circuit_type = ""
        # self.routing_intf_type = ""
        # self.intf_metric = 0
        # self.rsvp = False
        # self.pim = False
        # self.mpls = False
        # self.svlan = 0
        # self.cvlan = 0
        # self.vlan_mapping = ""
        # self.vlan_translate = ""
        # self.vlan_map_svlan = ""
        # self.vlan_map_cvlan = ""
        # self.split_horizon = False
        # self.servie_pol_in = ""
        # self.servie_pol_out = ""
        # self.xconnect = ""

    @staticmethod
    def query_dhcp_relay(hostname):
        try:
            sql = "select IP, Unit, BD_ID, VRF_Name, IP_helper from ifl" \
                  " where Hostname = '%s' and IFD = 'Vlanif' and IP_helper != ''" % hostname
            IFL.cursor.execute(sql)
            rows = IFL.cursor.fetchall()
            return list(map(lambda x: IFL(x[0], x[1], x[2], x[3], x[4]), rows))
        except MySQLdb.Error as e:
            print (e)
            IFL.db.rollback()