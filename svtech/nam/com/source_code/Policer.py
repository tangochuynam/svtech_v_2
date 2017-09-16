import MySQLdb

import Database


class POLICER:
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, name, bandwidth, burst_size):
        self.name = name
        self.bandwidth = bandwidth
        self.burst_size = burst_size

    @staticmethod
    def query_policer(hostname):
        try:
            sql = "select Name, CIR from policy_map " \
                  "where Hostname = '%s' and Class = '' and CIR > 0" % hostname
            POLICER.cursor.execute(sql)
            list_rows = POLICER.cursor.fetchall()
            list_policer = list(map(lambda x: POLICER.get_policer(x), list_rows))
            return list_policer
        except MySQLdb.Error, e:
            print (e)
            POLICER.db.rollback()

    @staticmethod
    def get_policer(info):
        name = info[0]
        cir = info[1]
        bandwidth = cir
        burst_size = int(round(bandwidth * 0.1/8))
        return POLICER(name, bandwidth, burst_size)