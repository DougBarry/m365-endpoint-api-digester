#!/bin/env python
#
# Outputs a partial YAML file, compatible with a puppet controlled SQUID proxy YAML for Heira
from m365digester.Base import Base
from m365digester.Defaults import Defaults
from m365digester.OutputInterface import OutputInterface


class PuppetSquid(Base, OutputInterface):

    __rule_list = dict()
    __target_file_path = ''

    def set_input(self, rule_list: dict) -> bool:
        # FIXME: Validate rule_list is viable?
        self.__rule_list = rule_list
        return True

    def set_target_file_path(self, target_file_path: str) -> bool:
        # FIXME: Validate filepath?
        self.__target_file_path = target_file_path
        return True

    def get_file_extension(self) -> str:
        return 'yaml'

    def run(self) -> bool:
        """
        Output the ACL's in 'rule_list' to the 'target_file_path' in YAML format, creating a partial YAML file
        """
        if not self.__rule_list:
            raise Exception('Rule list not set')

        if not self.__target_file_path:
            raise Exception('Target file path not set')

        squid_src_acl_name: str = self.config.get('squid_src_acl_name', Defaults.squid_src_acl_name)

        self.info(f"Writing Puppet Squid partial YAML file to: '{self.__target_file_path}'")

        with open(self.__target_file_path, mode='w') as target_file_handle:
            print("squid_http_access:", file=target_file_handle)

            for acl_list_name in self.__rule_list:
                if not isinstance(acl_list_name, str):
                    raise Exception(f"ACL List found in rule list if not expected type: string. "
                               f"Found '{acl_list_name.__class__.__name__}")

                if len(self.__rule_list[acl_list_name]) > 0:
                    print(f"  '{squid_src_acl_name} {acl_list_name}':", file=target_file_handle)
                    print("    'action': 'allow'", file=target_file_handle)
                    print(f"    'comment': 'Allow rule for {acl_list_name} ACL'", file=target_file_handle)

            print("", file=target_file_handle)
            print("squid_acls:", file=target_file_handle)

            for acl_list_name in self.__rule_list:
                print(f"  '{acl_list_name}':", file=target_file_handle)
                if 'domain' in acl_list_name:
                    print(f"    'type': 'dstdomain'", file=target_file_handle)
                    print(f"    'comment': 'M365 (Teams or OneDrive) destination domains ({acl_list_name})'",
                          file=target_file_handle)
                else:
                    print(f"    'type': 'dst'", file=target_file_handle)
                    print(f"    'comment': 'M365 (Teams or OneDrive) destination ip addresses ({acl_list_name})'",
                          file=target_file_handle)
                print(f"    'entries':", file=target_file_handle)
                for destination in self.__rule_list[acl_list_name]:
                    if not isinstance(destination, str):
                        raise Exception(f"ACL List destination found in rule list if not expected type: string. "
                                   f"Found '{destination.__class__.__name__}")

                    print(f"      - '{destination}'", file=target_file_handle)

                print("", file=target_file_handle)
