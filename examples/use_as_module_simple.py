#!/usr/bin/env python3
# Part of m365-endpoint-api-digester
# Use as module example
import os
import logging
from m365digester.Defaults import Defaults
from m365digester.M365Digester import M365Digester
from m365digester.Outputs.GeneralCSV import GeneralCSV
from m365digester.Outputs.PuppetSquid import PuppetSquid

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

config = dict()
# Disable wildcard replacement of '*' with '.'
config.setdefault('wildcard_replace_enabled', False)
# Filter in all available categories
config.setdefault('categories_filter_include', Defaults.categories_filter_include_choices)

exit_code = 0

output_path = config.get('output_path', Defaults.output_path)
output_plugins = list()

try:
    output_plugins.append(PuppetSquid(config, root_logger))
    output_plugins.append(GeneralCSV(config, root_logger))
    app = M365Digester(config, root_logger)
    exit_code = app.main()
    if not exit_code:
        for output_plugin in output_plugins:
            prefix = config.get('output_file_prefix', Defaults.output_file_prefix)
            extension = output_plugin.get_file_extension()
            output_file_path = os.path.join(output_path, str(prefix + '.' + extension))

            output_plugin.set_input(app.rule_list)
            output_plugin.set_target_file_path(output_file_path)
            output_plugin.run()
except Exception as e:
    root_logger.error(f"Exception during execution: {e}")
    exit(exit_code if exit_code > 0 else 1)
