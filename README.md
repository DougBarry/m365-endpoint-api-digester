m365-endpoint-api-digester
====
## An Microsoft 365 endpoint API utility
For information see: https://docs.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-ip-web-service?view=o365-worldwide  

```The Office 365 IP Address and URL web service helps you better identify and differentiate Office 365 network traffic, making it easier for you to evaluate, configure, and stay up to date with changes```

An extension of offically provided start scripts at: https://docs.microsoft.com/en-us/microsoft-365/enterprise/microsoft-365-ip-web-service?view=o365-worldwide#example-python-script  

---

## Motivation
This script began as part of a requirement to produce a [Squid3](http://www.squid-cache.org/) based proxy running on [Puppet](https://puppet.com/) manage infrastrcutrue, with the sole purpose of proxying [MS Teams](https://en.wikipedia.org/wiki/Microsoft_Teams) and [MS OneDrive](https://en.wikipedia.org/wiki/Microsoft_OneDrive) connections to [M365](https://en.wikipedia.org/wiki/Microsoft_365) from networks that were not permitted to be on a routable network, nor were they permitted to have generic proxied internet access in the interests of security. The first iteration of this script produced [YAML](https://en.wikipedia.org/wiki/YAML) only, and had little configurability. [Squid3](http://www.squid-cache.org/) uses [Splay Trees](https://en.wikipedia.org/wiki/Splay_tree), which does not work well when trying to translate the rules provided by the M365 Endpoint API ([see here](http://lists.squid-cache.org/pipermail/squid-users/2015-August/004937.html)), so a primitive 'collapser' is included, to reduce the rule sets produced to their minimum, and thus keep Squid happy.  

---

## Configuration
Uses the standard 'logging' module from Python ~2+ for log levels:
- CRITICAL
- ERROR
- WARNING
- INFO
- DEBUG

### Options
Parameters can be set in several ways
- Environment variables
- Command line
- As part of a python Dict() (when used as a module)

### Parameters
| Short | Long  | ENVVAR | Type | Default | Information  |
|---|---|---|---|---|---|
| -v | --version | N/A | Semantic version | | Return version information |
| | --log-level-file | LOG_LEVEL_FILE | Log Level | DEBUG | Set the log level for file output |
| | --log-level-console | LOG_LEVEL_CONSOLE | Log Level | INFO | Set the log level for console output |
| -l | --log-file-output | LOG_FILE_PATH | File path and name | None | Log file target |
| -k | --keep-sqlitedb | SQLITEDB_KEEP | Switch (Bool) | False | If set, any SQLite databases used on disk will not be deleted at the termination of this application |
| -j | --sqlitedb-file-path | SQLITEDB_FILE_PATH | File path and name | ./{APP_NAME}.db | If set, all SQLite operations will be performed on this file on disk, not in memory |
| -W | --disable-wildcards | WILDCARDS_DISABLED | Bool | False | Prevent the replacement of wildcards eg: '*.domain.com' with single prefix dots '.' |
| -w | --wildcard-pattern | WILDCARD_PATTERN | String (regex) | '^(\*).' | Regex to use for the detection and replacement of wildcards |
| -C | --collapse-acls-disable | ACL_COLLAPSE_DISABLED | Switch (Bool) | True | If disabled, ACLs will not be reduced to a smaller set based on inner/outer subdomain tree positioning |
| -z | --categories-include | CATEGORIES_INCLUDE | Domain List (space seperator) | Allow Default | List of catergories from API to process |
| -q | --disable-domains | DOMAINS_DISABLED | Switch (Bool) | Disable processing of domain names from API | False | Prevent processing of domains from the API, they will not be included in output |
| -n | --disable-ipv4 | IPV4_DISABLED | Switch (Bool) | Disable processing of IPv4 addresses from API | False | Prevent processing of IPv4 addresses from the API, they will not be included in output |
| -m | --disable-ipv6 | IPV6_DISABLED | Switch (Bool) | Disable processing of IPv6 addresses from API | False | Prevent processing of IPv6 addresses from the API, they will not be included in output |
| -i | --client-request-id | M365_REQUEST_ID | String (GUID) | Automatically generated from host NIC MAC | Request ID to use with M365 API |
| -s | --service-instance | M365_SERVICE_INSTANCE | String (Choice) | Worldwide | Specify M365 service instance API type |
| -e | --extra-known-domains | EXTRA_KNOWN_DOMAINS | Domain/Address List (space seperator) | Not specified | Use for your tenancy domain names or other extras including overrides, do not use quotations, wildcards permitted, ie: '-e mycompany-files.sharepoint.net *.live.com |
| -u | --output-path | OUTPUT_PATH | File path without name | './' | Path on disk to place output file. Mutually exclusive with -o |
| -p | --output-prefix | OUTPUT_PREFIX | File name only without extension | '{APP_NAME}' | Filename without extension for output file |
| -o | --output-file | OUTPUT_FILE | File name and path | Unset | Full path and filename for output file. Mutually exclusive with -u and -p |
| -t | --output-type | OUTPUT_TYPE | String (Choice) | yaml | Output file type, from: [ CSV YAML ] |

---

### Use as a Docker container
**NOTE: This container is not yet published, but the included** ``Dockerfile`` **has been tested locally and does work.**
```bash
docker run -v /host/output/target:/output:rw dougbarry/m365digester:latest -l /output/m365digester.log -k -j /output/m365digester.db -z Allow Default Optimize -m -e testcompany-files.sharepoint.com testcompany-cloud.microsoft.com *.live.com -o /output/puppet-squid-snippet.yml
```

### Use via docker-compose
```yaml
services:
  m365digester:
    image: dougbarry/m365digester:latest
    environment:
      - "M365_REQUEST_ID=b10c5ed1-bad1-445f-b386-b919946339a7"
      - "OUTPUT_PATH=/output"
    volumes:
      - /host/path/output:/output:rw
```

---

### Use as command line application:
```bash
./m365digester-cli -l ./m365-digester.log -k -j ./m365-digester.db -z Allow Default Optimize -m -e testcompany-files.sharepoint.com testcompany-cloud.microsoft.com *.live.com -o puppet-squid-snippet.yml
```

### Use as module:
Default config in ```M365Digester/Defaults.py```  
Examples in ```examples/```  

### Minimum viable use as module:

```python
#!/usr/bin/env python3
import pprint
from m365digester.M365Digester import M365Digester

app = M365Digester()
app.main()
pprint.pprint(app.rule_list)
```

### Module usage with argument parsing
See ``M365Digester/M365DigesterCli.py``

### Custom M365 domains in module

```python
from m365digester.M365Digester import M365Digester

...
config = dict()
config.setdefault('extra_known_domains', [
    'mytenancy.sharepoint.com',
    'mytenancy-files.sharepoint.com',
    'mytenancy-my.sharepoint.com',
    'mytenancy-myfiles.sharepoint.com',
    # really just for *.officeapps.live.com but squids splay trees dont like it
    '.live.com'
])
...
app = M365Digester(config, my_logger)
...
```
## Contributing
If you have any issues or suggestions, [please submit an issue on GitHub](https://github.com/DougBarry/m365-endpoint-api-digester/issues). **All contributions considered and welcomed**

## License
[MIT License](https://github.com/DougBarry/m365-endpoint-api-digester/blob/main/LICENSE)