import json
import os
import re
import sqlite3
import tempfile
import urllib.request
from .Base import Base
from .Lib import Defaults, SQLiteContext


class M365Digester(Base):
    """App object"""

    __db = None
    __db_context_handle = None

    __rule_list = dict()
    __wildcard_adjustments = 0
    __duplicate_count = 0
    __domain_subset_duplicate_count = 0
    __excluded_count = 0

    @property
    def rule_list(self):
        return self.__rule_list

    def open_db(self, db_target: str) -> bool:
        """
        Open sqlite database connection
        """

        try:
            self.__db_context_handle = db_target
            self.__db = sqlite3.connect(self.__db_context_handle)
            self.debug(f"Opened SQLite3 Database file {self.__db_context_handle} connection, version {sqlite3.version}")
            return True
        except sqlite3.Error as e:
            self.error(f"Unable to open SQLite3 database file {self.__db_context_handle}, error: {e}")
            raise e

    def close_db(self):
        """
        Close sqlite database connection
        """
        self.__db.close()

    def remove_db(self) -> bool:
        """
        Delete temporary sqlite database file after usage
        """

        if self.db_is_in_memory():
            return True

        if self.config.get('keep_sqlitedb', False):
            self.info(f"Keeping SQLite db file: {self.__db_context_handle}.")
            return True

        try:
            os.remove(self.__db_context_handle)
            return True
        except Exception as e:
            self.warning(f"Unable to remove sqlite db file '{self.__db_context_handle}'. Error: {e}")
            return False

    def init_db(self) -> bool:
        sqlitedb_table_create = self.config.get('sqlitedb_table_create', Defaults.sqlitedb_table_create)
        try:
            c = self.__db.cursor()
            c.execute(sqlitedb_table_create)
            return True
        except sqlite3.Error as e:
            self.error(f"Unable to create table using query '{sqlitedb_table_create}'. Error: {e}")
            return False

    def db_is_in_memory(self):
        if self.config.get('sqlitedb_context', Defaults.sqlitedb_context) == SQLiteContext.MEMORY:
            return True
        return False

    def db_cursor(self):
        return self.__db.cursor()

    def db_commit(self):
        if self.db_is_in_memory():
            return
        else:
            self.__db.commit()

    def db_add_acl_to_rule_list(self, acl_address, service_area_name):
        """
        Adds rules (and their sources) to the rule database.
        This function does its best to not duplicate entries upon insertion, but it may not be perfect

        FIXME: This function only works with DNS entries, NOT IPv4/6 ADDRESSES. It will mangle an IPv4 ADDRESS with a
        wildcard in
        """

        if self.config.get('wildcard_replace_enabled', Defaults.wildcard_replace_enabled):
            wildcard_regex_pattern = self.config.get('wildcard_regex_pattern', Defaults.wildcard_regex_pattern)

            # Use a regex for wildcard analysis. This is slow (compared to a fancy lambda) but this is readable, and we
            # are not here for speed
            x = re.search(wildcard_regex_pattern, acl_address)

            # If the incoming acl_address contains a wildcard, replace it with a single dot - the SQUID way of handling
            # 'wildcards'
            if x:
                self.__wildcard_adjustments += 1
                old_address = acl_address
                pattern = re.compile(wildcard_regex_pattern)
                acl_address = pattern.sub('.', old_address)
                self.debug(f"ACL address '{old_address}' contains a wildcard. Altered to '{acl_address}'")

        # Check if the acl already exists in the rule set we are working on, if its there, count that we ignored a
        # duplicate, otherwise add to list
        sql_query = f"SELECT id, {Defaults.sqlitedb_column_address_name}, {Defaults.sqlitedb_column_service_area_name} FROM acls" \
                    f" WHERE {Defaults.sqlitedb_column_address_name} = ?;"
        c = self.db_cursor()
        c.execute(sql_query, (acl_address,))
        rows = c.fetchall()
        if len(rows) > 0:
            # Looks like there was a duplicate..
            existing_acl_service_area_name = rows[0][2]
            self.debug(
                f"Ignoring duplicate entry '{acl_address}' which would have been added to list '{service_area_name}'."
                f"Existing '{acl_address}' is in '{existing_acl_service_area_name}'")
            self.__duplicate_count += 1
            return -1
        c.close()

        sql_insert = f"INSERT OR IGNORE INTO acls(" \
                     f"{Defaults.sqlitedb_column_address_name}, " \
                     f"{Defaults.sqlitedb_column_service_area_name}) " \
                     f"VALUES (?,?);"
        c = self.db_cursor()
        c.execute(sql_insert, (acl_address, service_area_name))
        self.db_commit()
        return c.lastrowid

    def db_remove_acl_from_all_lists(self, acl_address):
        """
        Removes a rule from the rule database.
        """

        # Check if the rule is in there...
        sql_query = f"SELECT id, {Defaults.sqlitedb_column_address_name}, {Defaults.sqlitedb_column_service_area_name} FROM acls" \
                    f" WHERE {Defaults.sqlitedb_column_address_name} = ?;"
        c = self.db_cursor()
        c.execute(sql_query, (acl_address,))

        rows = c.fetchall()
        for row in rows:
            # Looks like it exists
            existing_acl_id = row[0]
            existing_acl_service_area_name = row[2]
            self.debug(f"Found address entry '{acl_address}' in service area '{existing_acl_service_area_name}'. Excluding..")

            sql_delete = "DELETE FROM acls WHERE id = ?;"
            c2 = self.db_cursor()
            c2.execute(sql_delete, (existing_acl_id,))
            self.__excluded_count += 1
            c2.close()

        self.db_commit()
        c.close()

        return

    def db_analyse_api_rule_lists(self, endpoint_set):
        """
        Analyse object 'endpoint_set' returned from M365 API, and create/update/extend dict-of-list 'rule_list'

        Filter results for Allow, Optimize, Default endpoints, and transform these into tuples with port and category
        ServiceArea is used to generate rule_set dictionary key, and if global collapse_acl_set is True,
        reduce number of dictionary keys to the minimum, effectively de-duplicating as much as possible at the expense
        of destination granularity
        """
        collapse_acl_sets = self.config.get('collapse_acl_sets', Defaults.collapse_acl_sets)
        categories_filter_include = self.config.get('categories_filter_include', Defaults.categories_filter_include)

        if self.config.get('address_filter_domains_enabled', Defaults.address_filter_domains_enabled):
            self.info("Analysing endpoints for domain names...")
            for endpointSet in endpoint_set:
                if endpointSet['category'] in categories_filter_include:
                    required = endpointSet['required'] if 'required' in endpointSet else False
                    if not required:
                        continue
                    urls = endpointSet['urls'] if 'urls' in endpointSet else []
                    service_area = str(endpointSet['serviceArea']) if 'serviceArea' in endpointSet else ''
                    if collapse_acl_sets:
                        service_area_name = f"M365-API-Source-domain"
                    else:
                        service_area_name = f"M365-API-Source-{service_area}-domain"
                    for url in urls:
                        self.db_add_acl_to_rule_list(str(url), service_area_name)

        if self.config.get('address_filter_ipv4_enabled', Defaults.address_filter_ipv4_enabled) \
                or self.config.get('address_filter_ipv6_enabled', Defaults.address_filter_ipv4_enabled):
            self.info("Analysing endpoints for IPs...")
            for endpointSet in endpoint_set:
                if endpointSet['category'] in categories_filter_include:
                    required = endpointSet['required'] if 'required' in endpointSet else False
                    if not required:
                        continue
                    ips = endpointSet['ips'] if 'ips' in endpointSet else []
                    # IPv4 strings have dots while IPv6 strings have colons
                    ip4s = [ip for ip in ips if '.' in ip]
                    ip6s = [ip for ip in ips if ':' in ip]
                    service_area = str(endpointSet['serviceArea']) if 'serviceArea' in endpointSet else ''
                    if collapse_acl_sets:
                        service_area_name = f"M365-API-Source-ip"
                    else:
                        service_area_name = f"M365-API-Source-{service_area}-ip"
                    for ip in ip4s:
                        self.db_add_acl_to_rule_list(str(ip), service_area_name)
                    for ip in ip6s:
                        self.db_add_acl_to_rule_list(str(ip), service_area_name)

    def db_get_count_acls_in_rule_list(self) -> int:
        """
        Get the total number of ACL's in the 'rule_list' db
        """
        c = self.db_cursor()
        c.execute("SELECT COUNT(*) FROM acls")
        result = c.fetchone()[0]
        return result

    def db_analyse_rule_lists_for_subdomain_errors(self):
        """
        Analyse rule database to remove subdomain overlaps
        """

        self.info("Analysing rules for subdomain overlaps")

        c = self.db_cursor()
        sql_query = f"SELECT id, " \
                    f"{Defaults.sqlitedb_column_address_name}, " \
                    f"{Defaults.sqlitedb_column_service_area_name} " \
                    f"FROM acls ORDER BY {Defaults.sqlitedb_column_service_area_name}"
        c.execute(sql_query)
        rows = c.fetchall()

        for row in rows:

            search_acl = ''

            # For every single ACL, check one isn't a subset of the other!
            acl_outer = str(row[1])
            if acl_outer.startswith('.'):
                search_acl = acl_outer
                sql_query2 = f"SELECT id, " \
                             f"{Defaults.sqlitedb_column_address_name}, " \
                             f"{Defaults.sqlitedb_column_service_area_name} " \
                             f"FROM acls WHERE {Defaults.sqlitedb_column_address_name} LIKE '%' || ?"
            else:
                search_acl = "." + acl_outer
                sql_query2 = f"SELECT id, " \
                             f"{Defaults.sqlitedb_column_address_name}, " \
                             f"{Defaults.sqlitedb_column_service_area_name} " \
                             f"FROM acls WHERE {Defaults.sqlitedb_column_address_name}=?;"

            c2 = self.db_cursor()
            c2.execute(sql_query2, (search_acl,))  # comma makes it a tuple... don't ask
            rows2 = c2.fetchall()
            for row2 in rows2:
                acl_inner = str(row2[1])
                if acl_inner != acl_outer:
                    acl_inner_id = str(row2[0])
                    sql_query3 = "DELETE FROM acls " \
                                 "WHERE id=?"
                    c3 = self.db_cursor()
                    c3.execute(sql_query3, (acl_inner_id,))
                    self.db_commit()
                    c3.close()
                    self.__domain_subset_duplicate_count += 1
                    self.debug(f"Removed subdomain overlap outer: '{acl_outer}', inner: '{acl_inner}'")
            c2.close()

        c.close()

    def db_get_unique_rule_sources(self):
        """
        Get unique source names from rule database
        """
        sql_query = f"SELECT DISTINCT {Defaults.sqlitedb_column_service_area_name} FROM acls;"
        c = self.db_cursor()
        c.execute(sql_query)
        rows = c.fetchall()
        c.close()
        return rows

    def db_get_rule_list(self):
        """
        Get complete rule set from rule database
        """
        local_rule_list = dict()

        sources_list = self.db_get_unique_rule_sources()

        for source in sources_list:
            if isinstance(source, tuple):
                source = str(source[0])
            sql_query = f"SELECT {Defaults.sqlitedb_column_address_name} " \
                        f"FROM acls " \
                        f"WHERE {Defaults.sqlitedb_column_service_area_name} = ? " \
                        f"ORDER BY address ASC;"
            c = self.db_cursor()
            c.execute(sql_query, (source,))
            addresses = c.fetchall()
            c.close()
            local_rule_list[source] = list()
            for address in addresses:
                address = str(address[0])
                local_rule_list[source].append(address)

        return local_rule_list

    def m365_web_service_get_rule_set(self, method_name, global_instance_name, client_request_id) -> dict:
        """
        Communicate with MS 365 Web Service to obtain json object with endpoint information
        Arguments 'clientRequestId' is a GUID. All zeros returns most recent changes only, hardcoded
        value of 'b10c5ed1-bad1-445f-b386-b919946339a7' should return complete set since 2018..

        Portions from https://geektechstuff.com/2018/07/06/microsoft-office-365-endpoints-v1-python/
        Portions from https://support.office.com/en-us/article/managing-office-365-endpoints-99cab9d4-ef59-4207-9f2b-3728eb46bf9a?ui=en-US&rs=en-US&ad=US#ID0EACAAA=4._Web_service
        """

        request_url_base: str = self.config.get('m365_web_service_url', Defaults.m365_web_service_url)
        self.info(f"Contacting M365 web service for ruleset: '{request_url_base}' "
                  f"using clientRequestId: '{client_request_id}'")
        request_path: str = request_url_base + \
                            '/' + method_name + \
                            '/' + global_instance_name + \
                            '?clientRequestId=' + \
                            client_request_id
        self.debug(f"Full M365 request path: '{request_path}'")
        request = urllib.request.Request(request_path)
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())

    def m365_web_service_get_version_data(self, client_request_id: str,
                                          global_instance_name: str = Defaults.m365_service_instance_name):

        request_url_base: str = self.config.get('m365_web_service_url', Defaults.m365_web_service_url)
        self.info(f"Contacting M365 web service for version data: '{request_url_base}'")
        request_path: str = request_url_base + '/version'
        if global_instance_name:
            request_path += '/' + global_instance_name
        request_path += '?clientRequestId=' + client_request_id
        self.debug(f"Full M365 request path: '{request_path}'")
        request = urllib.request.Request(request_path)
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode())

    def main(self) -> int:
        """Main function"""

        if self.config.get('sqlitedb_context', Defaults.sqlitedb_context):
            self.config.setdefault('sqlitedb_file_path',
                                   self.config.get('sqlitedb_context_memory', Defaults.sqlitedb_context_memory))
        else:
            self.config.setdefault('sqlitedb_file_path',
                                   self.config.get('sqlitedb_context_file', Defaults.sqlitedb_context_file))

        sqlitedb_context_handle: str = self.config.get('sqlitedb_file_path', None)
        # If no sqlite db output specified, generate a temp file to use?
        # FIXME:
        if not sqlitedb_context_handle:
            db_path = tempfile._get_default_tempdir()
            db_name = next(tempfile._get_candidate_names()) + ".db"
            sqlitedb_context_handle = os.path.join(db_path, db_name)

        try:
            self.open_db(sqlitedb_context_handle)
        except Exception as e:
            return self.error_quit(f"Unable to open sqlite database '{sqlitedb_context_handle}'. Error: {e}")

        self.init_db()

        m365_request_guid: str = self.config.get('m365clientRequestId_fullset',
                                                 Defaults.m365_request_guid)

        m365_instance: str = self.config.get('m365_instance', Defaults.m365_service_instance_name)

        # Call to M365 web service for rule set and decode JSON to object collection 'endpoint_set'
        try:
            endpoint_set = self.m365_web_service_get_rule_set('endpoints', m365_instance, m365_request_guid)
            # Analyse the 'endpoint_set' object collection, pass in reference to 'rule_list' to populate
            self.db_analyse_api_rule_lists(endpoint_set)
        except Exception as e:
            # If something goes wrong, pull the rip-cord
            return self.error_quit(f"Unable to retrieve endpoint set from M365 web service. Error: {e}")

        # Get stats on how many rules there are right now
        rule_count = self.db_get_count_acls_in_rule_list()
        self.info(f"Total known rules from MS API: {rule_count}")

        extra_known_domains = self.config.get('extra_known_domains', None)

        if extra_known_domains:
            extra_known_domains_list_name = self.config.get('extra_known_domains_list_name', 'M365-Extra-Domains')
            # Add UoGCloud domains to rule list
            for acl_address in extra_known_domains:
                try:
                    self.info(f"Adding extra known domain '{acl_address}' to '{extra_known_domains_list_name}'")
                    self.db_add_acl_to_rule_list(acl_address, extra_known_domains_list_name)
                except Exception as e:
                    self.error(f"Unable to add extra known domain to list. Error: {e.__class__.__name__}: {e}")

        exclude_addresses = self.config.get('exclude_addresses', None)

        if exclude_addresses:
            for acl_address in exclude_addresses:
                try:
                    self.info(f"Removing excluded address '{acl_address}' from consideration")
                    self.db_remove_acl_from_all_lists(acl_address)
                except Exception as e:
                    self.error(f"Unable to remove excluded address '{acl_address}', Error: {e.__class__.__name__}: {e}")

        # The API as of today 20210415 returns domains that are subdomains of high level ones, which Squid really
        # doesnt like
        self.__duplicate_count = 0
        self.db_analyse_rule_lists_for_subdomain_errors()

        # See how many rules got added (should be x+len(extra_known_domains) obviously)
        rule_count = self.db_get_count_acls_in_rule_list()
        self.info(f"Total known rules to generate from: {rule_count}")

        # Quick stats output
        self.info(f"Warning count: {self.warning_count},"
                  f" wildcard adjustment count: {self.__wildcard_adjustments},"
                  f" duplicates discarded count: {self.__duplicate_count},"
                  f" domain subset duplicate count: {self.__domain_subset_duplicate_count},"
                  f" excluded addresses counts: {self.__excluded_count}.")

        # List off rule set names
        self.info(f"Known source sets: ")
        sources = self.db_get_unique_rule_sources()
        for source in sources:
            if isinstance(source, tuple):
                source = str(source[0])
            self.info(f"{source}")

        self.__rule_list = self.db_get_rule_list()

        self.close_db()
        self.remove_db()

        # Success return code 0
        return 0
