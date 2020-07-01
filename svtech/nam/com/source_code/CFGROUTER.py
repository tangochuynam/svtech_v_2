import MySQLdb
from jinja2 import Environment, FileSystemLoader
from Utils import Utils
from Database import Database


class CFGROUTER:
    db = Database.db
    cursor = Database.cursor
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
        self.dict_policy_map = {}

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
        except MySQLdb.Error as e:
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
        cfg_router.get_policy_map()

        return cfg_router

    def get_policy_map(self):
        try:
            sql = "select Name from policy_map " \
                  "where Hostname = '%s' and CIR= 0 group by Name" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            # print list_rows
            dict_policy_map = {x[0].decode(): POLICYMAP.insert_item(x[0], CFGROUTER.hostname) for x in list_rows}
            self.dict_policy_map = dict_policy_map
        except MySQLdb.Error as e:
            print (e)
            CFGROUTER.db.rollback()

    def get_irb_list(self):
        try:
            sql = "select Unit1 from ifl where Hostname = '%s' and (IFD ='Vlan' or IFD = 'BVI') and PIM = '1'" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_irb = list(map(lambda x: MXIFD_UNIT('irb', x[0]), list_rows))
        except MySQLdb.Error as e:
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
        except MySQLdb.Error as e:
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
        except MySQLdb.Error as e:
            print (e)
            CFGROUTER.db.rollback()

    def get_core_pim_list(self):
        try:
            '''
            sql = "select ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where (ifl.Service = 'CORE' or ifl.Service = 'L3' )and ifl.PIM = '1' and ifl.Routing_type='isis' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            '''
            sql = "select ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where (ifl.Service = 'CORE' or ifl.Service = 'L3' )and ifl.PIM = '1' and ifl.Hostname = '%s' group by ifd.MX_IFD"\
                  % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_core_pim = list(map(lambda x: MXIFD_UNIT(x[0] if x[0] is not None else x[2], x[1]), list_rows))
        except MySQLdb.Error as e:
            print (e)
            CFGROUTER.db.rollback()

    def get_core_igp_list(self):
        try:
            sql_default_metric = "select Metric from isis where hostname = '%s' and Name ='1' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql_default_metric)
            row = CFGROUTER.cursor.fetchall()
            if len(row) > 0:
                IGP_MXIFD_UNIT.default_metric = row[0][0]

            #sql = "select ifd.MX_IFD, ifl.Unit1, ifl.Intf_metric, ifd.Name from ifl inner join ifd " \
            #      "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
            #      "where ifl.Service = 'CORE' and ifl.Routing_type = 'isis' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            sql = "select ifd.MX_IFD, ifl.Unit1, ifl.Intf_metric, ifd.Name, ifl.ISIS_authen,ifl.LDP_SYNC from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where (ifl.Service = 'CORE' or ifl.Service = 'L3' ) and " \
                  "ifl.Routing_type = 'isis' and ifl.Hostname = '%s' " % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_core_igp = list(map(lambda x: IGP_MXIFD_UNIT(x[0] if x[0] is not None else x[3], x[1], x[2],x[4],x[5]), list_rows))

        except MySQLdb.Error as e:
            print (e)
            CFGROUTER.db.rollback()

    def get_tldp_list(self):
        try:
            sql = "select IP from tldp_peer where Hostname = '%s'" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_tldp = list(map(lambda x: x[0], list_rows))

        except MySQLdb.Error as e:
            print (e)
            CFGROUTER.db.rollback()

    def get_igmp_ifl_list(self):
        try:
            sql = "select ifd.MX_IFD, ifl.Unit1, ifd.Name from ifl inner join ifd " \
                  "on ifl.Hostname = ifd.Hostname and ifl.IFD = ifd.Name " \
                  "where ifl.Hostname = '%s' and IGMP = 1 group by ifd.MX_IFD" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            list_rows = CFGROUTER.cursor.fetchall()
            self.list_igmp_ifl = list(map(lambda x: MXIFD_UNIT(x[0] if x[0] is not None else x[2], x[1]), list_rows))

        except MySQLdb.Error as e:
            print(e)
            CFGROUTER.db.rollback()

    def get_as_number(self):
        try:
            sql = "select Local_AS from bgp where Hostname = '%s' and VRF_Name = '' group by Local_AS" % CFGROUTER.hostname
            CFGROUTER.cursor.execute(sql)
            row = CFGROUTER.cursor.fetchall()
            if len(row) > 0:
                self.as_number = row[0][0]
            else:
                print('Khong ton tai config bgp peer tren thiet bi ' + self.hostname)
                self.as_number=input('Nhap gia tri AS cua tinh:')
                #raise ValueError("select as_number in CFGROUTER Fail")
        except MySQLdb.Error as e:
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
    def __init__(self, mx_ifd, unit1, metric, isis_authen, ldp_sync ):
        self.mx_ifd = mx_ifd
        self.unit1 = unit1
        self.metric = metric
        self.isis_authen = isis_authen
        self.ldp_sync = ldp_sync


class POLICYMAP:
    db = Database.db
    cursor = Database.cursor

    def __init__(self, name=''):
        self.name = name
        self.mf_list = []
        self.acl_list = []
        self.df_action = ''
        self.df_fc = ''
        self.df_lp = ''
        self.family_type = ''

    def showdata(self):
        attrs = vars(self)
        print(','.join("%s: %s" % item for item in attrs.items()))

    @staticmethod
    def insert_item(info, hostname):
        # print info
        temp_policy_name = POLICYMAP(info)
        temp_policy_name.mf_list = temp_policy_name.get_mf_list(temp_policy_name.name, hostname)
        # print 'Gia tri MF:',temp_policy_name.mf_list
        temp_policy_name.acl_list = temp_policy_name.get_acl_list(temp_policy_name.name, hostname)
        # print 'Gia tri ACL:', temp_policy_name.acl_list
        return temp_policy_name

    @staticmethod
    def get_mf_list(info, hostname):
        try:
            sql = "select Name, Class, 8021p, DSCP, Set_1p, Set_dscp, Set_prec_transmit, Set_EXP,FC,LP "\
                    "from policy_map " \
                  "where Hostname = '%s' and CIR= 0 and Name = '%s' and ACL=''" % (hostname, info.decode())
            #print("line 262 trong cfgrouter.py:", sql)
            POLICYMAP.cursor.execute(sql)
            list_rows = POLICYMAP.cursor.fetchall()
            list_mf = []
            if len(list_rows) > 0:
                #print('MF:',list_rows)
                list_mf = list(map(lambda x: MF.insert_mf(x), list_rows))
            return list_mf
        except MySQLdb.Error as e:
            print(e)

    @staticmethod
    def get_acl_list(info, hostname):
        try:
            sql = "select Name, Class, ACL from policy_map " \
                  "where Hostname = '%s' and CIR= 0 and Name = '%s' and ACL!=''" % (hostname, info.decode())
            POLICYMAP.cursor.execute(sql)
            list_rows = POLICYMAP.cursor.fetchall()
            list_acl = []
            if len(list_rows) > 0:
                # print 'Gia tri Policy:', info, 'ACL:', list_rows
                list_acl = FF.insert_acl_list(list_rows[0][2], hostname)
            return list_acl
        except MySQLdb.Error as e:
            print (e)


class FF:
    db = Database.db
    cursor = Database.cursor

    def __init__(self, name='', Index_1=0, Action_1='', Protocol_1='', Prefix_Source=''
                 , S_Port='', Prefix_Dest='', D_Port=''):
        self.name = name
        self.Index_1 = Index_1
        self.Action_1 = Action_1
        self.Protocol_1 = Protocol_1
        self.Prefix_Source = Prefix_Source
        self.S_Port = S_Port
        self.Prefix_Dest = Prefix_Dest
        self.D_Port = D_Port

    def showdata(self):
        attrs = vars(self)
        print(','.join("%s: %s" % item for item in attrs.items()))

    @staticmethod
    def insert_acl(info):
        tmp_s_port = info[5].split()[1] if info[5]!='' else ''
        tmp_d_port = info[7].split()[1] if info[7]!='' else ''
        tmp_acl = FF(name=info[0], Index_1=info[1], Action_1=info[2], Protocol_1=info[3],
                     Prefix_Source=Utils.convert_subnet(info[4]),
                     S_Port=tmp_s_port, Prefix_Dest=Utils.convert_subnet(info[6]), D_Port=tmp_d_port)
        return tmp_acl

    @staticmethod
    def insert_acl_list(info, hostname):
        sql = "select Name,Index_1,Action_1,Protocol_1,Prefix_Source,S_Port,Prefix_Dest,D_Port " \
              "from acl_detail where hostname = '%s' and Name = '%s' " % (hostname, info)
        FF.cursor.execute(sql)
        list_rows = FF.cursor.fetchall()
        print('line 325 in CFGROUTER.py list_rows:',list_rows)
        tmp_acl_list = list(map(lambda x: FF.insert_acl(x), list_rows))
        return tmp_acl_list


class MF:
    db = Database.db
    cursor = Database.cursor

    def __init__(self, name, classname='', p1=0, dscp=0, set_1p=0, set_dscp='', set_ip_pre=0, set_exp=0, fc='',
                 lp=''):
        self.name = name
        self.classname = classname
        self.p1 = p1
        self.dscp = dscp
        self.set_1p = set_1p
        self.set_dscp = set_dscp
        self.set_ip_pre = set_ip_pre
        self.set_exp = set_exp
        self.fc = fc
        self.lp = lp

    def showdata(self):
        attrs = vars(self)
        print(','.join("%s: %s" % item for item in attrs.items()))

    @staticmethod
    def insert_mf(info):
        tmp_mf = MF(name=info[0], classname=info[1], p1=info[2], dscp=info[3], set_1p=info[4],
                    set_dscp=info[5], set_ip_pre=info[6], set_exp=info[7], fc=Utils.change_name_classifier(info[8]), lp=info[9])
        return tmp_mf