#!/bin/env python
#
# Outputs a general purpose CSV file
from m365digester.Base import Base
from m365digester.OutputInterface import OutputInterface


class GeneralCSV(Base, OutputInterface):

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
        return 'csv'

    def run(self) -> bool:
        """
        Output the ACL's in 'rule_list' to the 'target_file_path' in general CSV format
        """
        if not self.__rule_list:
            raise Exception('Rule list not set')

        if not self.__target_file_path:
            raise Exception('Target file path not set')

        self.info(f"Writing general csv file to: '{self.__target_file_path}'")

        with open(self.__target_file_path, mode='w') as target_file_handle:

            print(f"\"ACL_LIST_NAME\",\"DESTINATION\",\"ACL_TYPE\",\"COMMENT\"", file=target_file_handle)

            for service_area_name in self.__rule_list:
                acl_comment = ''
                acl_type = ''
                if 'domain' in service_area_name:
                    acl_type = 'domain'
                    acl_comment = f"M365 (Teams or OneDrive) destination domains ({service_area_name})"
                else:
                    acl_type = 'ip'
                    acl_comment = f"M365 (Teams or OneDrive) destination ip addresses ({service_area_name})"
                for acl_destination in self.__rule_list[service_area_name]:
                    if not isinstance(acl_destination, str):
                        raise Exception(f"ACL List destination found in rule list if not expected type: string. "
                                   f"Found '{acl_destination.__class__.__name__}")

                    print(f"\"{service_area_name}\",\"{acl_destination}\",\"{acl_type}\",\"{acl_comment}\"",
                          file=target_file_handle)
