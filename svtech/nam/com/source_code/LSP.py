import MySQLdb

import Database


class LSP:
    hostname = ""
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, name="", dest="", pri_path="", bk_path="",
                 bk_path_org=False, bk_host_stb=False, admin_status=True, dest_name=""):
        self.name = name
        self.dest = dest
        self.pri_path = pri_path
        self.bk_path = bk_path
        self.bk_path_org = bk_path_org
        self.bk_host_stb = bk_host_stb
        self.admin_status = admin_status
        self.dest_name = dest_name
        self.number = ""
        self.lst_path_pri = []
        self.lst_path_second = []

    @staticmethod
    def query_data(hostname):
        try:
            LSP.hostname = hostname
            sql = "select Name, Dest, Path, Backup_path, Bk_path_org, Bk_host_stb, Admin_status from lsp where Hostname = '%s'" % LSP.hostname
            LSP.cursor.execute(sql)
            rows = LSP.cursor.fetchall()
            return list(map(lambda x: LSP.create_lsp_obj(x), rows))
        except MySQLdb.Error, e:
            print (e)

    @staticmethod
    def create_lsp_obj(x):
        lsp = LSP(name=x[0], dest=x[1], pri_path=x[2], bk_path=x[3], bk_path_org=x[4], bk_host_stb=x[5], admin_status=x[6])
        dest_name = ""
        # set des_name for lsp obj by query from IFL
        try:
            sql = "select Hostname from IFL " \
                  "where IFD = 'LoopBack' and IP like '%s'" % (lsp.dest + ' %')
            #print("Sql: " + str(sql))
            LSP.cursor.execute(sql)
            row = LSP.cursor.fetchall()
            if len(row) > 0:
                dest_name = row[0][0]
            else:
                raise ValueError('can not get dest_hostname in class LSP')
            lsp.dest_name = dest_name
            lsp.number = lsp.name.split('/')[2]
            lsp.get_list_path_pri()
            lsp.get_list_path_second()
        except MySQLdb.Error, e:
            print (e)
            LSP.db.rollback()
        finally:
            return lsp

    def get_list_path_pri(self):
        try:
            sql = "select Index_1, NH from path_detail where Hostname ='%s' and Name = '%s'" % (LSP.hostname, self.pri_path)
            LSP.cursor.execute(sql)
            rows = LSP.cursor.fetchall()
            if len(rows) > 0:
                lst_path_info_tmp = list(map(lambda x: Path_Info(x[0], x[1]), rows))
                lst_path_info = list(filter(lambda x: x.nh != self.dest,lst_path_info_tmp))
                lst_path_info.sort(key=lambda x: x.index)

                self.lst_path_pri = lst_path_info
            else:
                raise ValueError('pri_path not found in path_detail in class LSP')
        except MySQLdb.Error, e:
            print (e)
            LSP.db.rollback()

    def get_list_path_second(self):
        try:
            sql = "select Index_1, NH from path_detail where Hostname ='%s' and Name = '%s'" % (LSP.hostname, self.bk_path)
            LSP.cursor.execute(sql)
            rows = LSP.cursor.fetchall()
            if len(rows) > 0:
                lst_path_info_tmp = list(map(lambda x: Path_Info(x[0], x[1]), rows))
                lst_path_info = list(filter(lambda x: x.nh != self.dest, lst_path_info_tmp))
                lst_path_info.sort(key=lambda x: x.index)
                self.lst_path_second = lst_path_info
            else:
                print("second path not found ")
        except MySQLdb.Error, e:
            print (e)
            LSP.db.rollback()


class Path_Info:
    def __init__(self, index, nh):
        self.index = index
        self.nh = nh
