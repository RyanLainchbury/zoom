# -*- coding: utf-8 -*-

"""
    zoom.database

    a database that does less
"""

import timeit
import collections


ARRAY_SIZE = 1000

ERROR_TPL = """
  statement: {!r}
  parameters: {}
  message: {}
"""


class UnkownDatabaseException(Exception):
    """exception raised when the database is unknown"""
    pass


class DatabaseException(Exception):
    """exception raised when a database server error occurs"""
    pass


class Result(object):
    """database query result"""
    # pylint: disable=too-few-public-methods

    def __init__(self, cursor, array_size=ARRAY_SIZE):
        self.cursor = cursor
        self.array_size = array_size

    def __iter__(self):
        while True:
            results = self.cursor.fetchmany(self.array_size)
            if not results:
                break
            for result in results:
                yield result

    def __len__(self):
        # deprecate? - not supported by all databases
        count = self.cursor.rowcount
        return count > 0 and count or 0

    def __str__(self):
        """nice for humans"""

        def is_numeric(value):
            """test if string contains only numeric values"""
            return str(value[1:-1]).translate({'.': None}).isdigit()

        labels = [' %s ' % i[0] for i in self.cursor.description]
        values = [[' %s ' % i for i in r] for r in self]
        allnum = [
            all(is_numeric(v[i]) for v in values)
            for i in range(len(labels))
        ]
        widths = [
            max(len(v[i]) for v in [labels] + values)
            for i in range(len(labels))
        ]
        fmt = ' ' + ' '.join([
            (allnum[i] and '%%%ds' or '%%-%ds') % w
            for i, w in enumerate(widths)
        ])
        lines = ['-' * (w) for w in widths]
        result = '\n'.join(
            (fmt % tuple(i)).rstrip() for i in [labels] + [lines] + values
        )
        return result

    def __repr__(self):
        """useful and unabiguous"""
        return repr(list(self))

    def first(self):
        """return first item in result"""
        for i in self:
            return i


class Database(object):
    # pylint: disable=trailing-whitespace
    # pylint: disable=too-many-instance-attributes
    """
    database object

        >>> import sqlite3
        >>> db = database('sqlite3', database=':memory:')
        >>> db('drop table if exists person')
        >>> db(\"\"\"
        ...     create table if not exists person (
        ...     id integer primary key autoincrement,
        ...     name      varchar(100),
        ...     age       smallint,
        ...     kids      smallint,
        ...     birthdate date,
        ...     salary    decimal(8,2)
        ...     )
        ... \"\"\")

        >>> db("insert into person (name, age) values ('Joe',32)")
        1

        >>> db('select * from person')
        [(1, 'Joe', 32, None, None, None)]

        >>> print(db('select * from person'))
          id   name   age   kids   birthdate   salary
         ---- ------ ----- ------ ----------- --------
           1   Joe     32   None   None        None

    """

    paramstyle = 'pyformat'


    def __init__(self, factory, *args, **keywords):
        """Initialize with factory method to generate DB connection
        (e.g. odbc.odbc, cx_Oracle.connect) plus any positional and/or
        keyword arguments required when factory is called."""
        self.__connection = None
        self.__factory = factory
        self.__args = args
        self.__keywords = keywords
        self.debug = False
        self.log = []
        self.rowcount = None
        self.lastrowid = None

    def __getattr__(self, name):
        if self.__connection is None:
            self.__connection = self.__factory(*self.__args, **self.__keywords)
        return getattr(self.__connection, name)

    def translate(self, command, *args):
        """translate sql dialects

        The Python db API standard does not attempt unify parameter passing
        styles for SQL arguments.  This translate routine attempts to do that
        for each database type.  For databases that use the preferred pyformat
        paramstyle nothing needs to be done.  Databases requiring other
        paramstyles should override this method to provide translate the
        command the the required style.
        """
        def issequenceform(obj):
            """test for a sequence type that is not a string"""
            if isinstance(obj, str):
                return False
            return isinstance(obj, collections.Sequence)

        if self.paramstyle == 'qmark':
            if len(args) == 1 and hasattr(args[0], 'items') and args[0]:
                placeholders = {key: ':%s' % key for key in args[0]}
                cmd = command % placeholders, args[0]
            elif len(args) >= 1 and issequenceform(args[0]):
                placeholders = ['?'] * len(args[0])
                cmd = command % tuple(placeholders), args
            else:
                placeholders = ['?'] * len(args)
                cmd = command % tuple(placeholders), args
            return cmd

        else:
            params = len(args) == 1 and \
                hasattr(args[0], 'items') and \
                args[0] or \
                args
            return command, params

    def _execute(self, cursor, method, command, *args):
        """execute the SQL command"""
        start = timeit.default_timer()
        command, params = self.translate(command, *args)
        try:
            method(command, params)
        except Exception as error:
            raise DatabaseException(ERROR_TPL.format(command, args, error))
        else:
            self.rowcount = cursor.rowcount
        finally:
            if self.debug:
                self.log.append('  SQL ({:5.1f} ms): {!r} - {!r}'.format(
                    (timeit.default_timer() - start) * 1000,
                    command,
                    args,
                ))

        if cursor.description:
            return Result(cursor)
        else:
            self.lastrowid = getattr(cursor, 'lastrowid', None)
            return self.lastrowid

    def execute(self, command, *args):
        """execute a SQL command with optional parameters"""
        cursor = self.cursor()
        return self._execute(cursor, cursor.execute, command, *args)

    def execute_many(self, command, sequence):
        """execute a SQL command with a sequence of parameters"""
        # pylint: disable=star-args
        cursor = self.cursor()
        return self._execute(cursor, cursor.executemany, command, *sequence)

    def __call__(self, command, *args):
        return self.execute(command, *args)

    def use(self, name):
        """use another database on the same instance"""
        # pylint: disable=star-args
        args = list(self.__args)
        keywords = dict(self.__keywords, db=name)
        return Database(self.__factory, *args, **keywords)
        
    def report(self):
        """produce a SQL log report"""
        if self.log:
            return '  Database Queries\n --------------------\n{}\n'.format(
                '\n'.join(self.log))
        return ''

    def get_tables(self):
        """get a list of database tables"""
        pass


class Sqlite3Database(Database):
    """Sqlite3 Database"""

    paramstyle = 'qmark'

    def __init__(self, *args, **kwargs):
        import sqlite3
        from decimal import Decimal

        keyword_args = dict(
            kwargs,
            detect_types=sqlite3.PARSE_DECLTYPES,
        )

        # add support for decimal types
        def adapt_decimal(value):
            """adapt decimal values to their string representation"""
            return str(value)
        def convert_decimal(bytetext):
            """convert bytesring representatinos of decimal values to actual
            Decimal values"""
            return Decimal(bytetext.decode())
        sqlite3.register_adapter(Decimal, adapt_decimal)
        sqlite3.register_converter('decimal', convert_decimal)

        # pylint: disable=star-args
        # I meant to do that
        Database.__init__(self, sqlite3.connect, *args, **keyword_args)

    def get_tables(self):
        """return table names"""
        cmd = 'select name from sqlite_master where type="table"'
        return [a[0] for a in self(cmd)]


class MySQLDatabase(Database):
    """MySQL Database"""

    paramstyle = 'pyformat'

    def __init__(self, *args, **kwargs):
        import pymysql

        keyword_args = dict(
            kwargs,
            charset='utf8'
        )

        # pylint: disable=star-args
        # I meant to do that
        Database.__init__(self, pymysql.connect, *args, **keyword_args)

    def get_tables(self):
        """return table names"""
        cmd = 'show tables'
        return [a[0] for a in self(cmd)]


def database(engine, *args, **kwargs):
    """create a database object"""
    # pylint: disable=invalid-name

    if engine == 'sqlite3':
        db = Sqlite3Database(*args, **kwargs)
        return db

    elif engine == 'mysql':
        db = MySQLDatabase(*args, **kwargs)
        db.autocommit(1)
        return db

    else:
        raise UnkownDatabaseException