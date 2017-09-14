import MySQLdb
import Database
class Server:
    hostname = ""
    db = Database.Database.db
    cursor = Database.Database.cursor

    def __init__(self, ip = "", purpose = ""):
        self.ip = ip
        self.purpose = purpose

    @staticmethod
    def get_list_log_server(hostname):
        try:
            sql = "select ip, Purpose from server where Hostname = '%s'" % hostname
            Server.cursor.execute(sql)
            rows = Server.cursor.fetchall()
            return list(map(lambda x: Server(x[0], x[1]), rows))
        except MySQLdb.Error, e:
            print (e)
            Server.db.rollback()