import MySQLdb
import ipaddress as ip
from Database import Database
from numpy.core import unicode


class ACL:
    db = Database.db
    cursor = Database.cursor

    def __init__(self, name):
        self.name = name
        self.prefix_list = []

    @staticmethod
    def query_acl(hostname):
        try:
            ACL.hostname = hostname
            list_acl_name = ACL.get_list_acl_name()
            list_acl = []
            for acl_name in list_acl_name:
                acl = ACL(acl_name)
                acl.get_list_prefix()
                list_acl.append(acl)
            return list_acl
        except MySQLdb.Error as e:
            print (e)
            ACL.db.rollback()

    @staticmethod
    def get_list_acl_name():
        try:
            sql = "select ACL from vrf_ie where Hostname = '%s' and ACL!='' group by ACL" % ACL.hostname
            ACL.cursor.execute(sql)
            list_rows = ACL.cursor.fetchall()
            return list(map(lambda x: x[0], list_rows))
        except MySQLdb.Error as e:
            print (e)
            ACL.db.rollback()

    def get_list_prefix(self):
        try:
            sql = "select Prefix_Source from acl_detail where Name ='%s' and Hostname = '%s'" % (self.name, ACL.hostname)
            ACL.cursor.execute(sql)
            list_rows = ACL.cursor.fetchall()
            self.prefix_list = list(map(lambda x: ACL.convert_ip(x), list_rows))
        except MySQLdb.Error as e:
            print (e)
            ACL.db.rollback()

    @staticmethod
    def convert_ip(info):
        ip_temp = info[0]
        if (ip_temp != '') and ('-' not in ip_temp):
            #print "Test gia tri ip_temp:", ip_temp
            host, subnet = ip_temp.strip().split()
            if subnet=='0':
                subnet ='32'
            subnet_mask = host + '/' + subnet
            network_ipv4 = ip.ip_network(unicode(subnet_mask))
            ip_temp = str(network_ipv4)
            return ip_temp
        else:
            return ip_temp

    @staticmethod
    def get_list_mgmt_acl(hostname):
        lst_mgmt_acl = []
        try:
            sql = "select Name from acl where Hostname = '%s' and Purpose = 'MGMT'" % hostname
            ACL.cursor.execute(sql)
            rows = ACL.cursor.fetchall()
            for row in rows:
                name = row[0]
                sql_1 = "select Prefix_Source from acl_detail " \
                        "where Hostname = '%s' and Name = '%s' and Action_1 = 'permit'" % (hostname, name)
                ACL.cursor.execute(sql_1)
                lst_ip = ACL.cursor.fetchall()
                for tmp_ip in lst_ip:
                    if tmp_ip[0] != '':
                        #lst_mgmt_acl.append('0.0.0.0/0')
                        lst_mgmt_acl.append(ACL.convert_ip(tmp_ip))
        except MySQLdb.Error as e:
            print (e)
            ACL.db.rollback()
        finally:
            return lst_mgmt_acl