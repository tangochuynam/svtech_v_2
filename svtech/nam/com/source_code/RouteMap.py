import MySQLdb

import Database


class Sequence:
    def __init__(self, seq, lst_extcommn, lst_prefix, action):
        self.seq = seq
        self.lst_extcomm = lst_extcommn
        self.lst_prefix = lst_prefix
        self.action = action


class RouteMap:
    db = Database.Database.db
    cursor = Database.Database.cursor
    hostname = ""

    def __init__(self, name):
        self.name = name
        self.lst_seq = []

    @staticmethod
    def query_data(hostname):
        try:
            lst_route_map = []
            RouteMap.hostname = hostname
            sql = "select Name from route_map where Hostname = '%s' group by Name" % RouteMap.hostname
            RouteMap.cursor.execute(sql)
            rows = RouteMap.cursor.fetchall()
            if len(rows) > 0:
                lst_name = list(map(lambda x: x[0], rows))
                for name in lst_name:
                    route_map = RouteMap(name)
                    route_map.insert_info_to_seq()
                    lst_route_map.append(route_map)
            return lst_route_map
        except MySQLdb.Error, e:
            print (e)

    def insert_info_to_seq(self):
        try:
            sql = "select Seq, Extcomm,ACL,Action_1 from route_map where Hostname = '%s' and Name = '%s'" % (RouteMap.hostname, self.name)
            RouteMap.cursor.execute(sql)
            rows = RouteMap.cursor.fetchall()
            #print rows
            self.lst_seq = list(map(lambda x: Sequence(x[0], x[1].split(), RouteMap.convert_acl_to_pref(x[2]), x[3]), rows))
        except MySQLdb.Error, e:
            print (e)
            RouteMap.db.rollback()

    @staticmethod
    def get_lst_extcomm_bgp(hostname):
        try:
            lst_extcomm = []
            sql = "select Extcomm from route_map where Hostname = '%s'" % hostname
            RouteMap.cursor.execute(sql)
            rows = RouteMap.cursor.fetchall()
            if len(rows) > 0:
                lst_temp = list(map(lambda x: x[0], rows))
                for extcomm in lst_temp:
                    lst_extcomm = lst_extcomm + extcomm.strip().split()
                return list(set(lst_extcomm))
            else:
                return lst_extcomm
        except MySQLdb.Error, e:
            print (e)
            RouteMap.db.rollback()

    @staticmethod
    def convert_acl_to_pref(acl_name):
        try:
            lst_prefix = []
            #print acl_name
            if acl_name!='':
                sql = "select Prefix_Source from acl_detail where Hostname = '%s' and Name ='%s' " %(RouteMap.hostname, acl_name)

                RouteMap.cursor.execute(sql)
                rows = RouteMap.cursor.fetchall()

                if len(rows) > 0 :
                    lst_prefix = list(map(lambda x: [x[0].split()[0]+'/'+x[0].split()[1],x[0].split()[2].split('-')[0],
                                                      x[0].split()[2].split('-')[1]] if '-' in x[0]
                    else [x[0].split()[0]+'/'+x[0].split()[1]],rows))
                #print lst_prefix
            return lst_prefix
        except MySQLdb.Error, e:
            print (e)
            RouteMap.db.rollback()