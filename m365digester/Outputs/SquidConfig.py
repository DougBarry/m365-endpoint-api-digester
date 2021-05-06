#!/bin/env python
#
# Outputs a file intended for configuration, based on multiple parts and simple templates
import os

from m365digester.Base import Base
from m365digester.Lib import Defaults
from m365digester.OutputInterface import OutputInterface

from string import Template

class SquidConfig(Base, OutputInterface):

    __rule_list = dict()
    __ext = 'config'
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
        return self.__ext

    def _read_template(self, template_file_path: str) -> str:
        with open(template_file_path) as template_file_handle:
            return template_file_handle.read()

    def _render_template(self, template_file_path: str, template_substitutes: dict) -> str:
        return Template(self._read_template(template_file_path)).substitute(template_substitutes)

    def run(self) -> bool:
        """
        Output the ACL's in 'rule_list' to the 'target_file_path' in general CSV format
        """
        if not self.__rule_list:
            raise Exception('Rule list not set')

        if not self.__target_file_path:
            raise Exception('Target file path not set')

        template_file = self.config.get('output_template', None)

        if not template_file:
            raise Exception('Output template file path no set')

        if not os.path.isfile(template_file):
            raise FileNotFoundError(template_file)

        self.info(f"Writing squid config file to: '{self.__target_file_path}'")

        squid_src_acl_name: str = self.config.get('squid_src_acl_name', Defaults.squid_src_acl_name)

        template_config = dict()

        acl_set = ''
        rule_allow = ''

        linesep = self.config.get('linesep', Defaults.linesep).chars()

        for acl_list_name in self.__rule_list:
            if not isinstance(acl_list_name, str):
                raise Exception(f"ACL List found in rule list if not expected type: string. "
                                f"Found '{acl_list_name.__class__.__name__}")

            if len(self.__rule_list[acl_list_name]) > 0:
                rule_allow += f"http_access allow {squid_src_acl_name} {acl_list_name}{linesep}"

        for acl_list_name in self.__rule_list:
            for destination in self.__rule_list[acl_list_name]:
                acl_scope = 'dst'
                if 'domain' in acl_list_name.lower():
                    acl_scope = 'dstdomain'
                else:
                    acl_scope = 'dst'

                acl_set += f"acl {acl_list_name} {acl_scope} {destination}{linesep}"

        template_config.setdefault('acl_set', acl_set)
        template_config.setdefault('rule_allow', rule_allow)

        with open(self.__target_file_path, mode='w') as target_file_handle:
            target_file_handle.write(self._render_template(template_file, template_config))
