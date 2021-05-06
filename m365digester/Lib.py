import os
import uuid
import hashlib
import logging
import datetime
from enum import Enum
from m365digester import APP_NAME


class SQLiteContext(Enum):
    MEMORY = 0
    FILE = 1


class LineSeparator(Enum):
    OS_DEFAULT = 0
    LF = 1
    CRLF = 2

    def __str__(self):
        return self.name

    def chars(self) -> str:
        if self._value_ == self.LF.value:
            return f"\n"
        elif self._value_ == self.CRLF.value:
            return f"\r\n"
        return os.linesep

    @staticmethod
    def from_string(s: str):
        try:
            return LineSeparator[s]
        except Exception as e:
            logging.getLogger().warning(f"Unable to match requested line seperator '{s}' to known types. "
                                        f"Using os.linesep")
            return LineSeparator.OS_DEFAULT


class Defaults(object):

    linesep = LineSeparator.OS_DEFAULT
    linesep_choices = list(LineSeparator)

    m365_web_service_url = 'https://endpoints.office.com'

    categories_filter_include = ('Allow', 'Default')
    categories_filter_include_choices = ('Allow', 'Default', 'Optimize')

    address_filter_ipv4_enabled = True
    address_filter_ipv6_enabled = True
    address_filter_domains_enabled = True

    squid_src_acl_name = 'm365-proxy-users'

    # File system paths
    cwd = os.getcwd()
    pwd = os.path.dirname(os.path.realpath(__file__))
    app_started = datetime.datetime.now()

    log_levels = list(filter(lambda x: x not in ['NOTSET', 'WARN', 'FATAL'], logging._nameToLevel.keys()))
    log_level_console = logging.INFO
    log_level_file = logging.DEBUG
    log_dts = app_started.strftime('%Y%m%d%H%M%S')
    log_path = os.path.join(cwd, 'logs')
    log_file_name = f"{APP_NAME}-{log_dts}.log"
    log_file_path = os.path.join(cwd, log_file_name)
    data_cache_path = os.path.join(cwd, '.cache')
    output_path = cwd
    output_file_prefix = 'm365endpoint-output'
    output_file_extension = 'txt'

    output_type = 'generalcsv'
    output_types_available = ['generalcsv', 'puppetsquid', 'squidconfig']

    # Efficiency mode - outputs everything into a de-duplicated ACL set for domain, and ips
    collapse_acl_sets = True

    # Const for 'latest' ruleset complete from MS - example 'b10c5ed1-bad1-445f-b386-b919946339a7'
    m365_request_guid = str(uuid.UUID(hashlib.sha256(str(uuid.getnode()).encode('utf-8')).hexdigest()[::2]))
    m365_service_instance_name = 'Worldwide'
    m365_service_instance_options = ('Worldwide',
                                     'China',
                                     'Germany',
                                     'USGovDoD',
                                     'USGovGCCHigh')

    # What we consider a wildcard for domain names '*.something'
    wildcard_regex_pattern = '^(\*).'
    wildcard_replace_enabled = True

    # SQLite
    sqlitedb_context = SQLiteContext.MEMORY
    sqlitedb_context_file = f"{APP_NAME}.db"
    sqlitedb_context_memory = ":memory:"
    sqlitedb_column_address_name = "address"
    sqlitedb_column_service_area_name = "servicearea"
    sqlitedb_table_create = "CREATE TABLE IF NOT EXISTS acls (" \
                            "id INTEGER PRIMARY KEY AUTOINCREMENT," \
                            f"{sqlitedb_column_address_name} TEXT NOT NULL," \
                            f"{sqlitedb_column_service_area_name} TEXT NOT NULL);"
