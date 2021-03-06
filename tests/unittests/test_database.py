"""
    Test the database module
"""

# pylint: disable=missing-docstring
# method names are more useful for testing

# pylint: disable=invalid-name

import unittest
import sqlite3
import logging
from decimal import Decimal
from datetime import date, datetime

from zoom.database import database

import warnings
warnings.filterwarnings('ignore', '\(1051, "Unknown table.*')

logger = logging.getLogger(__name__)


class DatabaseTests(object):
    """test db module"""

    # pylint: disable=too-many-public-methods
    # It's reasonable in this case.
    def tearDown(self):
        self.db('drop table if exists dzdb_test_table')
        self.db.close()
        print(self.db.report())

    def test_RecordSet(self):
        db = self.db
        db("""create table dzdb_test_table (ID CHAR(10), AMOUNT
           NUMERIC(10,2),DTADD DATE,NOTES TEXT)""")
        db("""insert into dzdb_test_table values  ("1234",50,"2005-01-14","Hello there")""")
        db("""insert into dzdb_test_table values ("5678",60,"2035-01-24","New
           notes")""")
        recordset = db('select * from dzdb_test_table')
        for rec in recordset:
            self.assertEquals(rec, ("1234", 50, date(2005,1,14), "Hello there"))
            break

    def test_db_create_drop_table(self):
        db = self.db
        self.assert_('dzdb_test_table' not in db.get_tables())
        db("""
           create table dzdb_test_table (
             ID CHAR(10),
             AMOUNT NUMERIC(10,2),
             DTADD DATE,
             NOTES TEXT
           )
        """)
        self.assert_('dzdb_test_table' in db.get_tables())
        db('drop table dzdb_test_table')
        self.assert_('dzdb_test_table' not in db.get_tables())

    def test_get_tables(self):
        db = self.db
        n = 10
        for i in range(n):
            table_name = 'dzdb_test_table{}'.format(i)
            db('drop table if exists ' + table_name)
            self.assert_(table_name not in db.get_tables())
            db("""
               create table {} (
                 ID CHAR(10),
                 AMOUNT NUMERIC(10,2),
                 DTADD DATE,
                 NOTES TEXT
               )
            """.format(table_name))
            self.assert_(table_name in db.get_tables())

        for i in range(n):
            table_name = 'dzdb_test_table{}'.format(i)
            db('drop table ' + table_name)
            self.assert_(table_name not in db.get_tables())

    def test_db_insert_update_record(self):
        # pylint: disable=protected-access
        insert_test = """
            insert into dzdb_test_table 
            (id, name, dtadd, amount, notes)
            values (%s, %s, %s, %s, %s)
        """
        select_all = 'select count(*) from dzdb_test_table'

        db = self.db
        db('drop table if exists dzdb_test_table')
        db("""
            create table dzdb_test_table (
                id char(10),
                name char(25),
                amount numeric(10,2),
                dtadd date,
                notes text
            )
        """)
        dt = date(2005, 1, 2)
        db(insert_test, '1234', 'Joe', dt, 50, 'Testing')
        self.assertEqual(list(db(select_all))[0][0], 1)
        db(insert_test, '4321', 'Joe', dt, 10.20, 'Testing 2')
        self.assertEqual(list(db(select_all))[0][0], 2)
        db(insert_test, '4321', 'Joe', dt, None, 'Updated')
        self.assertEqual(list(db(select_all))[0][0], 3)

        response = db('select * from dzdb_test_table')
        print(response)
        self.assertEqual(
            list(db(
                'select * from dzdb_test_table'
            ))[2][4], "Updated")
        db('drop table dzdb_test_table')

    def test_last_rowid(self):
        db = self.db
        select_all = 'select count(*) from dz_test_contacts'
        db('drop table if exists dz_test_contacts')
        db(self.create_indexed_cmd)
        db("""insert into dz_test_contacts values
           (1,"testuser","pass","test@datazoomer.net")""")
        self.assertEqual(db.lastrowid, 1)
        db("""insert into dz_test_contacts values
           (4,"2testuser","pass","test@datazoomer.net")""")
        self.assertEqual(db.lastrowid, 4)
        db.execute_many(
            """insert into dz_test_contacts (userid, password, email) values
            (%s, %s, %s)""",
            [
                ('user3', 'pass3', 'user3@datazoomer.net'),
                ('user4', 'pass4', 'user4@datazoomer.net'),
                ('user5', 'pass5', 'user5@datazoomer.net'),
                ('user6', 'pass6', 'user6@datazoomer.net'),
            ])
        self.assertEqual(list(db(select_all))[0][0], 6)
        db('drop table dz_test_contacts')

    def test_record(self):
        db = self.db
        db("""create table dzdb_test_table (ID CHAR(10), AMOUNT
           NUMERIC(10,2), NOTES TEXT)""")
        db("""insert into dzdb_test_table values ("1234", 50, "Hello there")""")
        recordset = db('select * from dzdb_test_table')
        for rec in recordset:
            self.assertEqual(
                rec,
                ('1234', 50, "Hello there")
            )

    def test_metadata(self):
        db = self.db
        db("""create table dzdb_test_table (ID CHAR(10), AMOUNT
           NUMERIC(10,2), DTADD DATE, NOTES TEXT)""")
        db("""insert into dzdb_test_table values ("1234", 50, "2005-01-14",
           "Hello there")""")
        q = db('select * from dzdb_test_table')
        names = [f[0] for f in q.cursor.description]
        self.assertEqual(names, ['ID', 'AMOUNT', 'DTADD', 'NOTES'])
    
    def test_date_type(self):
        db = self.db
        db('create table dzdb_test_table (ID CHAR(10), AMOUNT NUMERIC(10,2), DTADD date, NOTES TEXT)')
        cmd = 'insert into dzdb_test_table values ("1234", 50, %s, "Hello there")'
        db(cmd, date(2005, 1, 14))
        recordset = db('select * from dzdb_test_table')
        for rec in recordset:
            self.assertEqual(
                rec,
                ('1234', 50, date(2005, 1, 14), "Hello there")
            )

    def test_decimal_type(self):
        db = self.db
        db(self.create_cmd)
        cmd = 'insert into dzdb_test_table values (%s, %s, %s, %s)'
        db(cmd, '1234', 50, Decimal('1.12'), 'Hello there')
        recordset = db('select * from dzdb_test_table')
        for rec in recordset:
            self.assertEqual(
                rec,
                ('1234', 50, Decimal('1.12'), "Hello there")
            )


class TestSqlite3Database(unittest.TestCase, DatabaseTests):

    def setUp(self):
        self.db = database('sqlite3', ':memory:')
        self.create_cmd  = """
            create table dzdb_test_table
            (
                ID CHAR(10),
                AMOUNT NUMERIC(10,2),
                salary decimal(10,2),
                NOTES TEXT
            )
        """
        self.create_indexed_cmd = """
            create table dz_test_contacts (
                contactid integer PRIMARY KEY AUTOINCREMENT,
                userid char(20),
                password char(16),
                email char(60)
            )
        """
        self.db.debug = True

class TestMySQLDatabase(unittest.TestCase, DatabaseTests):

    def setUp(self):
        self.db = database(
            'mysql',
            host='database',
            user='testuser',
            passwd='password',
            db='zoomtest'
        )
        self.create_cmd  = """
            create table dzdb_test_table
            (
                ID CHAR(10),
                AMOUNT NUMERIC(10,2),
                salary decimal(10,2),
                NOTES TEXT
            )
        """
        self.create_indexed_cmd = """
            create table dz_test_contacts (
                contactid integer PRIMARY KEY AUTO_INCREMENT,
                userid char(20),
                password char(16),
                email char(60)
            )
        """
        self.db('drop table if exists dzdb_test_table')
        self.db.debug = True


