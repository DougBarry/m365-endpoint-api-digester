#!/usr/bin/env python3
# Part of m365-endpoint-api-digester
# Use as module example minimal
import pprint
from m365digester.M365Digester import M365Digester
app = M365Digester()
app.main()
pprint.pprint(app.rule_list)
