#!/bin/env python
#
# Example config output skeleton
# Note this doesn't actually do anything without modification
from m365digester.Base import Base
from m365digester.Lib import Defaults
from m365digester.OutputInterface import OutputInterface

import os


class ExampleOutputSimpleConfig(Base, OutputInterface):
    __rule_list = dict()
    __ext = 'config'
    __target_file_path = ''

    __header_file = None
    __footer_file = None

    def set_input(self, rule_list: dict) -> bool:
        # FIXME: Validate rule_list is viable?
        self.__rule_list = rule_list
        return True

    def set_target_file_path(self, target_file_path: str) -> bool:
        # FIXME: Validate filepath?
        self.__target_file_path = target_file_path
        return True

    def get_file_extension(self) -> str:
        return self.__ext

    def set_header(self, header_file: str):
        if os.path.isfile(header_file):
            self.__header_file = header_file
        else:
            raise FileNotFoundError(header_file)

    def set_footer(self, footer_file: str):
        if os.path.isfile(footer_file):
            self.__footer_file = footer_file
        else:
            raise FileNotFoundError(footer_file)

    def run(self) -> bool:
        """
        Output the ACL's in 'rule_list' to the 'target_file_path' in general CSV format
        """
        if not self.__rule_list:
            raise Exception('Rule list not set')

        if not self.__target_file_path:
            raise Exception('Target file path not set')

        self.info(f"Writing general csv file to: '{self.__target_file_path}'")

        linesep = self.config.get('linesep', Defaults.linesep)

        with open(self.__target_file_path, mode='w') as target_file_handle:

            # Prepend header if valid and required
            if self.__header_file:
                with open(self.__header_file) as header_file_handle:
                    for line in header_file_handle:
                        target_file_handle.write(line)

            # Append footer if valid and required
            if self.__footer_file:
                with open(self.__footer_file) as footer_file_handle:
                    for line in footer_file_handle:
                        target_file_handle.write(line)
