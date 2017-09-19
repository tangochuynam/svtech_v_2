import MySQLdb

import Database


class POLICY_MAP:
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, name, classname='',acl='',cir=0,p1=0,dscp=0,set_1p=0,set_dscp='',set_ip_pre=0,set_exp=0,fc='',
                 lp=''):
        self.name = name
        self.classname = classname
        self.acl = acl
        self.cir = cir
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
        print ','.join("%s: %s" % item for item in attrs.items())

    @staticmethod
    def query_policy_map(hostname):
        try:
            sql = "select Name from policy_map " \
                  "where Hostname = '%s' and Class!= '' group by Name" % hostname
            POLICY_MAP.cursor.execute(sql)
            list_rows = POLICY_MAP.cursor.fetchall()
            #print list_rows
            list_policy_map = {x[0]:POLICY_MAP.get_policy_map(x[0],hostname) for x in list_rows}

            return list_policy_map
        except MySQLdb.Error, e:
            print (e)
            POLICY_MAP.db.rollback()

    @staticmethod
    def get_policy_map(policy_name,hostname):
        sql = "select Name, Class,ACL,CIR,8021p,DSCP," \
             "Set_1p,Set_dscp,Set_prec_transmit,Set_EXP," \
             "FC,LP from policy_map " \
             "where Hostname = '%s' and Class!= '' and Name = '%s'" %(hostname,policy_name)
        POLICY_MAP.cursor.execute(sql)
        list_rows = POLICY_MAP.cursor.fetchall()
        #print list_rows
        list_policy_class_tmp = list(map(lambda x: POLICY_MAP.convert_policy_map(x),list_rows))
        #for item in list_policy_class_tmp:
        #    item.showdata()
        return list_policy_class_tmp

    @staticmethod
    def convert_policy_map(info):
        policy_map_tmp = POLICY_MAP(info[0],info[1],info[2],info[3],info[4],info[5],info[6],info[7],info[8],
                                    info[9],info[10],info[11])
        return policy_map_tmp

