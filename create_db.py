import psycopg2


class DB(object):
    def open(self):
        hostname = '127.0.0.1'
        username = 'parsing_admin'
        password = 'parsing_adminparsing_admin'
        database = 'parsing'
        port = "5444"
        self.connection = psycopg2.connect(host=hostname, user=username, password=password, dbname=database, port=port)
        self.cur = self.connection.cursor()

    def close(self):
        self.cur.close()
        self.connection.close()

    def drop_table(self):
        self.cur.execute(
            """DROP TABLE table_1"""
        )
        self.connection.commit()

    def create_tables(self):
        """create tables in the database if they are not contained"""

        self.cur.execute('''CREATE TABLE IF NOT EXISTS Item
                     (
                     id SERIAL PRIMARY KEY,
                     UID TEXT,
                     publication_text TEXT,
                     company_name TEXT,
                     address TEXT,
                     zip_code TEXT,
                     town TEXT,
                     journal_number TEXT,
                     journal_date TEXT,
                     publication_title TEXT,
                     url TEXT,
                     category TEXT,
                     subcategory TEXT,
                     publication_number TEXT,
                     publication_date TEXT
                     );''')

        self.connection.commit()


db = DB()
db.open()
db.create_tables()
db.close()
