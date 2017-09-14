import MySQLdb

"""
class COSINTERFACE:
    def __init__(self, name=''):
        self.name = name
        self.list_unit = []

    @staticmethod
    def query_data(db, cursor, hostname):
        try:

            sql = "select MX_IFD from ifd where Hostname = '%s' and Parent_link = '' " % hostname
            cursor.execute(sql)
            list_rows = cursor.fetchall()
            dict_mx_ifd = {x[0]:x for x in list_rows}
            dict_mx_ifd = list(map(lambda x: COSINTERFACE(x[0]), list_rows))
            
            sql_1 = "select cos_ifl.ifd, cos_ifl.unit, cos_ifl.unit1, ifd.MX_IFD from " \
                  "(select ifd, unit, unit1, Service_pol_in, Hostname from ifl where Hostname = '%s' and " \
                  "service !='CORE' and Service_pol_in !='' and Service_pol_in in " \
                  "(select Name from policy_map where hostname = '%s' and class ='class-default' and " \
                  "Set_prec_transmit !='')) as cos_ifl " \
                  "join ifd on cos_ifl.hostname = ifd.hostname and cos_ifl.ifd = ifd.name " \
                   % (hostname, hostname)
            cursor.execute(sql_1)
            list_rows = cursor.fetchall()
            # chia ra 2 truong hop, ifd != 'Vlan' and ifd = 'Vlan'
            list_cos_interface_diff_vlan  = list(filter(lambda x: x[0] != 'Vlan', list_rows))
            list_ifd_eq_vlan = list(filter(lambda x: x[0] == 'Vlan', list_rows))

        except MySQLdb.Error, e:
            print (e)
            db.rollback()
"""