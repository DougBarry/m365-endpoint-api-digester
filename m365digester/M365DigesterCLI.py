#!/usr/bin/env python3
"""
Main executable for using M365 Endpoint API Digester from the command line
"""

__author__ = "Doug Barry"
__license__ = "MIT"

import os
import sys
import logging
from pprint import pformat
from argparse import ArgumentParser, RawTextHelpFormatter
from m365digester import APP_NAME, APP_VERSION, APP_BRANCH
from m365digester.Lib import Defaults, SQLiteContext, LineSeparator
from m365digester.M365Digester import M365Digester

from m365digester.Outputs.GeneralCSV import GeneralCSV
from m365digester.Outputs.PuppetSquid import PuppetSquid
from m365digester.Outputs.SquidConfig import SquidConfig


def main():
    """This is executed when you run from the command line"""

    config = dict()

    APP_PATH = os.path.dirname(os.path.realpath(__file__))

    platform_starter = f"./{sys.argv[0]}"
    if os.name.lower() in ['windows', 'nt']:
        platform_starter = f"python {os.path.basename(sys.argv[0])}"

    parser = ArgumentParser(prog=str(os.path.basename(sys.argv[0])),
                            description=f"{APP_NAME} V{APP_VERSION}-{APP_BRANCH}{os.linesep}"
                                        f"An application and module to assist in retrieval and digestion of rules for "
                                        f"Micrsoft 365 service endpoints, for conversion into formats for proxy "
                                        f"servers, firewalls and other network infrastructure devices.",
                            formatter_class=RawTextHelpFormatter,
                            epilog=f"EXAMPLE:{os.linesep}"
                                   f"{platform_starter} {os.linesep}"
                                   f"\t--log-level-console debug {os.linesep}"
                                   f"\t-l ./m365-digester.log {os.linesep}"
                                   f"\t-k {os.linesep}"
                                   f"\t-j ./m365-digester.db {os.linesep}"
                                   f"\t-z Allow Default Optimize {os.linesep}"
                                   f"\t-m {os.linesep}"
                                   f"\t-e testcompany-files.sharepoint.com testcompany-cloud.microsoft.com *.live.com {os.linesep}"
                                   f"\t-p rules-today {os.linesep}"
                                   f"\t-t squid {os.linesep}"
                                   f"\t--output-template ./squidconfig.template {os.linesep}"
                                   f"\t-C",
                            usage=f"{platform_starter} [options]")

    parser.add_argument('-v', "--version", action="version",
                        version="%(prog)s (version {version})".format(version=APP_VERSION))

    logging_group = parser.add_argument_group('Logging', 'Logging functionality')

    logging_group.add_argument('--log-level-file', choices=Defaults.log_levels,
                               dest='log_level_file', type=str.upper,
                               default=os.environ.get('LOG_LEVEL_FILE', Defaults.log_level_file),
                               help=f"Default: {logging.getLevelName(Defaults.log_level_file)}")

    logging_group.add_argument('--log-level-console', choices=Defaults.log_levels,
                               dest='log_level_console', type=str.upper,
                               default=os.environ.get('LOG_LEVEL_CONSOLE', Defaults.log_level_console),
                               help=f"Default: {logging.getLevelName(Defaults.log_level_console)}")

    logging_group.add_argument('-l', '--log-file-output', dest='log_file_path',
                               default=os.environ.get('LOG_FILE_PATH'),
                               help=f"Defaults: Inactive if not specified")

    sqlitedb_group = parser.add_argument_group('SQLite', 'SQLite database')

    sqlitedb_group.add_argument('-k', '--keep-sqlitedb', dest='keep_sqlitedb',
                                default=os.environ.get('SQLITEDB_KEEP', False), action='store_true',
                                help="Default: False (SQLite db not kept)")

    sqlitedb_group.add_argument('-j', '--sqlitedb-file-path', dest='sqlitedb_file_path',
                                default=os.environ.get('SQLITEDB_FILE_PATH', None))

    wildcard_group = parser.add_argument_group('Wildcards', 'Wildcard handling')

    wildcard_enabled_group = wildcard_group.add_mutually_exclusive_group()

    wildcard_enabled_group.add_argument('-W', '--disable-wildcards', dest='wildcard_replace_enabled',
                                        action='store_false',
                                        default=os.environ.get('WILDCARDS_DISABLED', Defaults.wildcard_replace_enabled),
                                        help=f"Default: {'Wildcards enabled' if Defaults.wildcard_replace_enabled else 'Wildcards disabled'}")

    wildcard_group.add_argument('-w', '--wildcard-pattern', dest='wildcard_regex_pattern',
                                default=os.environ.get('WILDCARD_PATTERN', Defaults.wildcard_regex_pattern),
                                help=f"Default: '{Defaults.wildcard_regex_pattern}'")

    acl_group = parser.add_argument_group('ACLs', 'ACL handling')

    acl_group.add_argument('-C', '--collapse-acls-disable', dest='collapse_acl_sets',
                           action='store_false',
                           default=os.environ.get('ACL_COLLAPSE_DISABLED', Defaults.collapse_acl_sets),
                           help=f"Default: {'Collapsing of ACLs enabled' if Defaults.collapse_acl_sets else 'Collapsing of ACLs disabled'}")

    acl_group.add_argument('-z', '--categories-include', dest='categories_filter_include', nargs="+",
                           default=os.environ.get('CATEGORIES_INCLUDE', Defaults.categories_filter_include),
                           choices=Defaults.categories_filter_include_choices,
                           help=f"Default: '{' '.join(Defaults.categories_filter_include)}'")

    acl_group.add_argument('-q', '--disable-domains', dest='address_filter_domains_enabled',
                           action='store_false',
                           default=os.environ.get('DOMAINS_DISABLED', Defaults.address_filter_domains_enabled),
                           help=f"Default: {'Domains enabled' if Defaults.address_filter_domains_enabled else 'Domains disabled'}")

    acl_group.add_argument('-n', '--disable-ipv4', dest='address_filter_ipv4_enabled',
                           action='store_false',
                           default=os.environ.get('IPV4_DISABLED', Defaults.address_filter_ipv4_enabled),
                           help=f"Default: {'IPv4 enabled' if Defaults.address_filter_ipv4_enabled else 'IPv4 disabled'}")
    acl_group.add_argument('-m', '--disable-ipv6', dest='address_filter_ipv6_enabled',
                           action='store_false',
                           default=os.environ.get('IPV6_DISABLED', Defaults.address_filter_ipv6_enabled),
                           help=f"Default: {'IPv6 enabled' if Defaults.address_filter_ipv6_enabled else 'IPv6 disabled'}")

    m365_group = parser.add_argument_group('M365', 'Microsoft 365')

    m365_group.add_argument('-i', '--client-request-id', dest='m365_request_guid',
                            default=os.environ.get('M365_REQUEST_ID', Defaults.m365_request_guid),
                            help=f"Default: (Generated for this host): {Defaults.m365_request_guid}")

    m365_group.add_argument('-s', '--service-instance', dest='m365_service_instance_name',
                            choices=Defaults.m365_service_instance_options,
                            default=os.environ.get('M365_SERVICE_INSTANCE', Defaults.m365_service_instance_name),
                            help=f"Default: {Defaults.m365_service_instance_name}")

    acl_group.add_argument('-e', '--extra-known-domains', dest='extra_known_domains', nargs="+",
                           default=os.environ.get('EXTRA_KNOWN_DOMAINS', None),
                           help="Default: Empty. Use for your tenancy domain names or other extras including overrides."
                                " Separate with spaces, do not use quotations, wildcards permitted,"
                                " ie: '-e mycompany-files.sharepoint.net *.live.com'")

    file_group = parser.add_argument_group('IO', 'File IO')

    file_group.add_argument('-u', '--output-path', dest='output_path',
                            default=os.environ.get('OUTPUT_PATH', Defaults.output_path),
                            help=f"Default: './'. Mutually exclusive with -o")

    file_group.add_argument('-p', '--output-prefix', dest='output_file_prefix',
                            default=os.environ.get('OUTPUT_PREFIX', Defaults.output_file_prefix),
                            help=f"Default: '{Defaults.output_file_prefix}'. Mutually exclusive with -o")

    file_group.add_argument('-o', '--output-file', dest='output_file',
                            default=os.environ.get('OUTPUT_FILE', None),
                            help=f"Default: '{Defaults.output_file_prefix}.EXT' "
                                 f"where EXT is decided by output type. Mutually exclusive with -p and -u")

    file_group.add_argument('-t', '--output-type', dest='output_type', choices=Defaults.output_types_available,
                            default=os.environ.get('OUTPUT_TYPE', Defaults.output_type),
                            help=f"Default: {Defaults.output_type}")

    file_group.add_argument('--output-template', dest='output_template',
                            default=os.environ.get('OUTPUT_TEMPLATE', None),
                            help="Default: None. Not used by all output types")

    file_group.add_argument('--linesep', dest='linesep', type=LineSeparator.from_string,
                            default=os.environ.get('LINESEP', Defaults.linesep),
                            choices=list(LineSeparator), help="Default: OS_DEFAULT (os.linesep)")

    args = parser.parse_args()
    # args = parser.parse_args(['-h'])
    # FIXME: Debugging
    #     args = parser.parse_args(
    #         ['--log-level-console', 'debug', '-C', '-l', './m365-digester.log', '-k', '-j',
    #             './m365-digester.db', '-z', 'Allow', 'Default', 'Optimize', '-m', '-e'
    #             , 'testcompany-files.sharepoint.com', 'testcompany-cloud.microsoft.com', '*.live.com', '-p', 'today', '-t',
    #             'csv']
    #     )

    """Set up logging"""

    root_logger = logging.getLogger('m365digester')
    root_logger.setLevel(logging.DEBUG)
    log_formatter = logging.Formatter("%(asctime)s [%(levelname)-4.4s] %(message)s")
    console_log_handler = logging.StreamHandler(sys.stdout)

    # FIXME: Messy
    if isinstance(args.log_level_console, str):
        level = None
        if args.log_level_console.upper() in Defaults.log_levels:
            try:
                level = logging._nameToLevel[args.log_level_console.upper()]
            except:
                pass
        if level is None:
            log_level_console = Defaults.log_level_console
        else:
            log_level_console = level
    elif isinstance(args.log_level_console, int):
        log_level_console = args.log_level_console
    else:
        log_level_console = Defaults.log_level_console

    try:
        console_log_handler.setLevel(log_level_console)
    except Exception as e:
        if log_level_console:
            print(f"Unable to set console logging level to '{str(log_level_console)}', error: {e}")
        else:
            print(f"Unable to set console logging level, error: {e}")
        exit(1)

    console_log_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_log_handler)

    root_logger.debug(f"Command line arguments: {*sys.argv,}")

    if args.log_file_path:
        try:
            file_log_handler = logging.FileHandler(args.log_file_path)
        except Exception as e:
            if args.log_file_path:
                print(f"Unable to set logging output file to '{str(args.log_file_path)}', error: {e}")
            else:
                print(f"Unable to set logging output file, error: {e}")
            exit(1)

        try:
            file_log_handler.setLevel(args.log_level_file)
        except Exception as e:
            if args.log_level_file:
                print(f"Unable to set file logging level to '{str(args.log_level_file)}', error: {e}")
            else:
                print(f"Unable to set file logging level, error: {e}")
            exit(1)

        file_log_handler.setFormatter(log_formatter)
        root_logger.addHandler(file_log_handler)

    root_logger.info(f"{APP_NAME} V{APP_VERSION}-{APP_BRANCH}")

    config.update(vars(args))

    if config.get('keep_sqlitedb', False):
        if config.get('sqlitedb_file_path', None):
            config.setdefault('sqlitedb_context', SQLiteContext.FILE)
        else:
            root_logger.warning(
                f"Option to keep SQLite database specified, but SQLite database is in memory. No effect.")
            config.setdefault('sqlitedb_context', SQLiteContext.MEMORY)
            config['keep_sqlitedb'] = False

    output_plugin = None
    output_type = config.get('output_type', Defaults.output_type)

    if output_type == 'puppetsquid':
        output_plugin = PuppetSquid(config, root_logger)
    elif output_type == 'squidconfig':
        output_plugin = SquidConfig(config, root_logger)
    else: # output_type == 'generalcsv':
        output_plugin = GeneralCSV(config, root_logger)

    exit_code = 0

    root_logger.debug(f"Config: {pformat(config)}")

    app = M365Digester(config, root_logger)

    try:
        exit_code = app.main()
    except Exception as e:
        root_logger.error(f"Exception during M365 API digester execution: {e}")
        exit(exit_code if exit_code > 0 else 1)

    if not exit_code:
        if not app.rule_list:
            root_logger.warning('No rule list returned through this configuration')
        else:
            if len(app.rule_list) == 0:
                root_logger.warning('Rule list returned through this configuration contains zero entries')
            else:
                if output_plugin:
                    try:
                        output_file = config.get('output_file', None)
                        if not output_file:
                            prefix = config.get('output_file_prefix', Defaults.output_file_prefix)
                            extension = output_plugin.get_file_extension()
                            output_path = config.get('output_path', Defaults.output_path)
                            output_file = os.path.join(output_path, str(prefix + '.' + extension))

                        output_plugin.set_input(app.rule_list)
                        output_plugin.set_target_file_path(output_file)
                        output_plugin.run()
                    except Exception as e:
                        root_logger.error(f"Exception during output plugin execution: {e.__class__.__name__} {e}")
                        exit_code = 1

    exit(exit_code)


if __name__ == "__main__":
    main()
