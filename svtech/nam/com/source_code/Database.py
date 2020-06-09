import MySQLdb


class Database(object):
    db = MySQLdb.connect("localhost", "root", "Namvodich2212", "vnpt")
    cursor = db.cursor()

    def __init__(self):
        pass
