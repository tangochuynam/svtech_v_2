import MySQLdb
from jinja2 import Environment, FileSystemLoader

import Database


class CFGROUTER:
    db = Database.Database.db
    cursor = Database.Database.cursor
    hostname = ""
    router_type = ""
    def __init__(self):
        self.hostname = ""
        self.source_ip = ""
        self.as_number = ""
        self.ntp2 = False
        self.ntp5 = False
        self.list_irb = []
        self.list_core_mpls = []
        self.list_core_rsvp = []
        self.list_core_pim = []
        self.list_core_igp = []
        self.list_tldp = []
        self.list_igmp_ifl = []

    @staticmethod
    def query_cfg_router(hostname, router_type):
        try:
            CFGROUTER.hostname = hostname
            CFGROUTER.router_type = router_type
            sql = "select ifl.Hostname, ifl.IP from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where ifl.IFD = 'Loopback' and ifl.Unit1 = '0' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            one_row = CFGROUTER.cursor.fetchall()
            cfg_router = list(map(lambda x: CFGROUTER.create_cfg_router(x), one_row))
            return cfg_router[0]
        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    @staticmethod
    def create_cfg_router(info):
        cfg_router = CFGROUTER()
        if CFGROUTER.router_type == 'HW':
            arr_temp = info[0]
            name_convert = ''
            if arr_temp[3:5] == '00':
                name_convert = 'MX2010'
            else:
                name_convert = 'MX960'

            cfg_router.hostname = name_convert + '-' + arr_temp

        cfg_router.source_ip = info[1].split()[0]
        last_octet_ip = cfg_router.source_ip.split('.')[3]
        #print("last_octet_ip: " + last_octet_ip)
        if int(last_octet_ip) < 127:
            cfg_router.ntp2 = True
        else:
            cfg_router.ntp5 = True

        cfg_router.get_irb_list()
        cfg_router.get_core_mpls_list()
        cfg_router.get_core_rsvp_list()
        cfg_router.get_core_pim_list()
        cfg_router.get_core_igp_list()
        cfg_router.get_tldp_list()
        cfg_router.get_igmp_ifl_list()
        cfg_router.get_as_number()
        return cfg_router

    def get_irb_list(self):
        try:
            sql = "select Unit1 from ifl where Hostname = '%s' and (IFD ='Vlan' or IFD = 'BVI') and PIM = '1'" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_irb = list(map(lambda x: MXIFD_UNIT('irb', x[0]), list_rows))
        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    def get_core_mpls_list(self):
        try:
            sql = "select ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where ifl.Service = 'CORE' and ifl.MPLS = '1' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_core_mpls = list(map(lambda x: MXIFD_UNIT(x[0] if x[0] is not None else x[2], x[1]), list_rows))
        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    def get_core_rsvp_list(self):
        try:
            sql = "select ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where ifl.Service = 'CORE' and ifl.RSVP = '1' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_core_rsvp = list(map(lambda x: MXIFD_UNIT(x[0] if x[0] is not None else x[2], x[1]), list_rows))
        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    def get_core_pim_list(self):
        try:
            sql = "select ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where ifl.Service = 'CORE' and ifl.PIM = '1' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_core_pim = list(map(lambda x: MXIFD_UNIT(x[0] if x[0] is not None else x[2], x[1]), list_rows))
        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    def get_core_igp_list(self):
        try:
            sql_default_metric = "select Metric from isis where hostname = '%s' and Name ='1' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql_default_metric)
            row = CFGROUTER.cursor.fetchall()
            if len(row) > 0:
                IGP_MXIFD_UNIT.default_metric = row[0][0]

            sql = "select ifd.MX_IFD, ifl.Unit1, ifl.Intf_metric, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where ifl.Service = 'CORE' and ifl.Routing_type = 'isis' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_core_igp = list(map(lambda x: IGP_MXIFD_UNIT(x[0] if x[0] is not None else x[3], x[1], x[2]), list_rows))

        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    def get_tldp_list(self):
        try:
            sql = "select IP from tldp_peer where Hostname = '%s'" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_tldp = list(map(lambda x: x[0], list_rows))

        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    def get_igmp_ifl_list(self):
        try:
            sql = "select ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where ifl.Hostname = '%s' and IGMP = 1 " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_igmp_ifl = list(map(lambda x: MXIFD_UNIT(x[0] if x[0] is not None else x[2], x[1]), list_rows))

        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    def get_as_number(self):
        try:
            sql = "select Local_AS from bgp where Hostname = '%s' and VRF_Name = '' group by Local_AS" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            row = CFGROUTER.cursor.fetchall()
            if len(row) > 0:
                self.as_number = row[0][0]
            else:
                raise ValueError("select as_number in CFGROUTER Fail")
        except MySQLdb.Error, e:
            print (e)
            CFGROUTER.db.rollback()

    @staticmethod
    def writefile(cfg_router, file_name, path_input, path_output, hostname):
        template_env = Environment(autoescape=False, loader=FileSystemLoader(path_input), trim_blocks=False)
        base_config = {'cfg_router': cfg_router}
        file_ouput = path_output + "/" + hostname
        with open(file_ouput, 'w') as f:
            f_txt = template_env.get_template(file_name).render(base_config)
            f.write(f_txt)
        print("write successful")


class MXIFD_UNIT:
    def __init__(self, mx_ifd, unit1):
        self.mx_ifd = mx_ifd
        self.unit1 = unit1


class IGP_MXIFD_UNIT:

    #default_metric = 0
    def __init__(self, mx_ifd, unit1, metric ):
        self.mx_ifd = mx_ifd
        self.unit1 = unit1
        self.metric = metric
