import MySQLdb

import Database


class POLICY_MAP:
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, name, classname):
        self.name = name
        self.classname = classname
        self.cir = 0


    @staticmethod
    def query_policy_map(hostname):
        try:
            sql = "select Name, Class,CIR from policy_map " \
                  "where Hostname = '%s' and Class!= '' " % hostname
            POLICY_MAP.cursor.execute(sql)
            list_rows = POLICY_MAP.cursor.fetchall()
            list_policy_map = list(map(lambda x: POLICY_MAP.get_policer(x), list_rows))
            return list_policy_map
        except MySQLdb.Error, e:
            print (e)
            POLICY_MAP.db.rollback()
