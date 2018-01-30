# -*- coding: utf-8 -*-

from __future__ import unicode_literals

import io
import logging
import subprocess
import sys
from os import path

import six

from test_project import settings

log = logging.getLogger(__name__)


def main():
    logging.basicConfig(
        format="%(levelname)-8s %(message)s",
        level=logging.DEBUG
    )

    db_setup = settings.DATABASES["amavis"]

    try:
        if "postgresql" in db_setup["ENGINE"]:
            init_postgresql(db_setup)
        elif "mysql" in db_setup["ENGINE"]:
            init_mysql(db_setup)
        else:
            raise SetupError(
                "%s database engine is not supported by modoboa-amavis"
                % db_setup["ENGINE"]
            )
    except SetupError as e:
        log.error(str(e))
        sys.exit(1)

    sys.exit(0)


def init_postgresql(db_setup):
    log.info("initialising amavis test database on PostgreSQL")
    command = [
        "env",
        "PGCLIENTENCODING=%s" % db_setup["OPTIONS"]["client_encoding"],
        "psql",
        "--host=%s" % db_setup["HOST"],
        "--username=%s" % db_setup["USER"],
    ]

    if len(db_setup["PASSWORD"]) > 0:
        command.append("--password=%s" % db_setup["PASSWORD"])

    try:
        port = int(db_setup["PORT"])
    except ValueError:
        pass
    else:
        command.append("--port=%d" % port)

    log.info("creating %s database for amavis" % db_setup["NAME"])
    query = db_setup["OPTIONS"].get("init_command", "") + "\n"
    query += """
        CREATE ROLE amavis;
        ALTER ROLE amavis SET client_encoding = 'UTF8';
        ALTER ROLE amavis SET default_transaction_isolation = 'read committed';
        ALTER ROLE amavis
        SET timezone = 'UTC';
    """
    query += "CREATE DATABASE %s WITH OWNER amavis ENCODING '%s';\n" % (
        db_setup["NAME"],
        db_setup["TEST"]["CHARSET"]
    )
    execute_command(command, query)
    log.info("%s database created for amavis" % db_setup["NAME"])

    log.info("load database schema for amavis")
    command.append("--dbname=%s" % db_setup["NAME"])
    query = db_setup["OPTIONS"].get("init_command", "") + "\n"
    query += get_schema("postgres")
    execute_command(command, query)
    log.info("loading database schema for amavis complete")


def init_mysql(db_setup):
    log.info("initialising amavis test database on MySQL/MariaDB")
    command = [
        "mysql",
        "--default-character-set=%s" % db_setup["OPTIONS"]["charset"],
        "--host=%s" % db_setup["HOST"],
        "--user=%s" % db_setup["USER"],
    ]

    if len(db_setup["PASSWORD"]) > 0:
        command.append("--password=%s" % db_setup["PASSWORD"])

    try:
        port = int(db_setup["PORT"])
    except ValueError:
        pass
    else:
        command.append("--port=%d" % port)

    log.info("creating %s database for amavis" % db_setup["NAME"])
    query = db_setup["OPTIONS"].get("init_command", "") + "\n"
    query += "CREATE DATABASE %s CHARACTER SET %s COLLATE %s;" % (
        db_setup["NAME"],
        db_setup["TEST"]["CHARSET"],
        db_setup["TEST"]["COLLATION"]
    )
    execute_command(command, query)
    log.info("%s database created for amavis" % db_setup["NAME"])

    log.info("load database schema for amavis")
    command.append("%s" % db_setup["NAME"])
    query = db_setup["OPTIONS"].get("init_command", "") + "\n"
    query += get_schema("mysql")
    execute_command(command, query)
    log.info("loading database schema for amavis complete")


def execute_command(command, query):
    try:
        log.debug("execute command:\n %s" % query)
        query = query.encode("utf8")
        popen_checkcall(command, data_in=query)
    except CalledProcessError as exc:
        six.raise_from(
            SetupError(
                "command failed with return code %d: %s"
                % (exc.returncode, command)
            ),
            exc
        )


def get_schema(engine):
    root_dir = path.abspath(path.join(path.dirname(__file__), ".."))
    sql_schema_file = path.join(root_dir, path.join(
        "test_data", ("amavis_%s_2.11.0.sql" % engine)
    ))
    log.debug("loading schema from %s" % sql_schema_file)
    with io.open(sql_schema_file, encoding="utf8") as sql_schema_fp:
        sql_schema = sql_schema_fp.read()
    return sql_schema


class SetupError(Exception):
    pass


def popen_checkcall(args, data_in=None):
    """
    Adapted from Py3 subprocess.checkcall().
    subprocess.run() where are thou? :( Py >=3.5 only)
    """
    try:
        if data_in is None:
            proc = subprocess.Popen(args)
        else:
            proc = subprocess.Popen(args, stdin=subprocess.PIPE)
            proc.communicate(input=data_in)
        returncode = proc.wait()
    except Exception as exc:
        proc.kill()
        proc.wait()
        raise

    if returncode:
        raise CalledProcessError(returncode, args)

    return 0


class CalledProcessError(Exception):

    def __init__(self, returncode, args):
        self.returncode = returncode
        self.cmd = args
        super(CalledProcessError, self).__init__()


if __name__ == "__main__":
    main()
