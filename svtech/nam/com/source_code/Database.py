import MySQLdb


class Database(object):
    db = MySQLdb.connect("localhost", "root", "123456", "vnpt")
    cursor = db.cursor()

    def __init__(self):
        pass
