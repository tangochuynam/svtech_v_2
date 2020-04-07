import MySQLdb

from Database import Database


class Router:
    db = Database.db
    cursor = Database.cursor

    def __init__(self):
        self.hostname = ""
        self.type = ""

    @staticmethod
    def get_host_name():
        try:
            print ("coming into SQL")
            # prepare SQL query to DO WITH a record into the database
            sql_query = "select Hostname from router"
            Router.cursor.execute(sql_query)
            # handle the data
            list_rows = Router.cursor.fetchall()
            list_hostname = list(map(lambda x: x[0], list_rows))
            return list_hostname
        except MySQLdb.Error as e:
            print (e)
            # rollback in case there is any error
            Router.db.rollback()

    def get_list_bdid(self):
        try:
            sql = ("select ifl.BD_ID from ifl "
                   "where ifl.Hostname ='%s' and ifl.Service = 'vpls' and ifl.BD_ID "
                   "not in (select l2vpn.bd_id from l2vpn where l2vpn.Hostname = '%s' )"
                   "group by BD_ID") % (self.hostname, self.hostname)
            Router.cursor.execute(sql)
            list_rows = Router.cursor.fetchall()
            list_temp = list(map(lambda x: x[0], list_rows))
            return list_temp
        except MySQLdb.Error as e:
            print(e)
            Router.db.rollback()

    def get_hostname_type(self):
        try:
            sql = "select Device from router where Hostname = '%s'" % self.hostname
            Router.cursor.execute(sql)
            row = Router.cursor.fetchall()
            self.type = row[0][0]
        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

    def get_list_bd_id_l2vpn(self):
        try:
            sql = "select BD_ID from ifl where Hostname = '%s' and (IFD ='Vlan' or IFD = 'BVI')" \
                  "and Stitching = '0' and BD_ID " \
                  "in ( select BD_ID from l2vpn where Hostname = '%s' and Type = 'vpls' group by BD_ID ) " % (self.hostname, self.hostname)
            Router.cursor.execute(sql)
            list_rows = Router.cursor.fetchall()
            return list(map(lambda x: x[0], list_rows))
        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

    def get_list_bd_id_igmp(self):
        try:
            sql = "select BD_ID from ifl where ifl.Hostname = '%s' and (IFD ='Vlan' or IFD = 'BVI') and ifl.PIM = 1" % self.hostname
            Router.cursor.execute(sql)
            list_rows = Router.cursor.fetchall()
            if len(list_rows) > 0:
                return list(map(lambda x: x[0], list_rows))
            else:
                return []
        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

    def get_iso_address(self):
        try:
            sql = "select isis_net.Net from router " \
                  "inner join (select isis.Hostname,isis.Net from isis where Name ='1') " \
                  "as isis_net on router.Hostname= isis_net.Hostname " \
                  "where router.Hostname = '%s'" % self.hostname
            Router.cursor.execute(sql)
            list_rows = Router.cursor.fetchall()
            return list_rows[0][0]
        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

    def get_isis_export(self):
        try:
            sql = "select Redistribute from isis where hostname ='%s' " % self.hostname
            Router.cursor.execute(sql)
            list_rows = Router.cursor.fetchall()
            if len(list_rows)>0:
                list_tmp = list_rows[0][0].split('|')
                #print list_tmp
                dict_exp = {'level-1': '', 'level-2': ''}
                for item in list_tmp:
                    if 'level-1' in item:
                        if dict_exp['level-1']=='':
                            dict_exp['level-1'] = item.split()[0]
                        else:
                            dict_exp['level-1'] = dict_exp['level-1'] + ' ' + item.split()[0]
                    elif item!='':
                        if dict_exp['level-2']=='':
                            dict_exp['level-2'] = item.split()[0]
                        else:
                            dict_exp['level-2'] = dict_exp['level-2'] + ' ' + item.split()[0]
                #print dict_exp
                return dict_exp
            else:
                return {}

        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

    def get_list_policy_cos(self):
        try:
            sql = "select Name from policy_map where hostname = '%s' and class ='class-default' and " \
                  "Set_prec_transmit != '' " % self.hostname
            Router.cursor.execute(sql)
            list_rows = Router.cursor.fetchall()
            return list(map(lambda x: x[0], list_rows))
        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

    def get_list_unit_vlan_policer(self):
        try:
            sql = "select Unit, Service_pol_in, Service_pol_out from ifl where Hostname = '%s' " \
                  "and (IFD ='Vlan' or IFD = 'BVI') " \
                  "and (Service_pol_in != '' or Service_pol_out != '')" % self.hostname
            Router.cursor.execute(sql)
            rows = Router.cursor.fetchall()
            return list(map(lambda x: UNIT_VLAN_POLICER(x[0], x[1], x[2]), rows))
        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

    def get_list_bd_id_ip(self):
        try:
            sql = "select BD_ID from ifl where hostname = '%s' and (IFD ='Vlan' or IFD = 'BVI') and BD_ID in " \
                  "(select BD_ID from ifl where hostname = '%s' group by BD_ID) and IP!='' and Service != 'CORE' " \
                    % (self.hostname, self.hostname)
            Router.cursor.execute(sql)
            list_rows = Router.cursor.fetchall()
            list_bd_id_ip = list(map(lambda x: x[0], list_rows))
            #dict_bd_id_router = {bd_id: True for bd_id in list_rows}
            return list_bd_id_ip
        except MySQLdb.Error as e:
            print (e)
            Router.db.rollback()

class UNIT_VLAN_POLICER:

    def __init__(self, unit, service_pol_in, service_pol_out):
        self.unit = unit
        self.service_pol_in = service_pol_in
        self.service_pol_out = service_pol_out
