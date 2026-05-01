#!/usr/bin/env python3

# <xbar.title>Tomcat Run Check</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.author>Andrew McIntosh</xbar.author>
# <xbar.author.github>amcintosh</xbar.author.github>
# <xbar.desc>Indicate if tomcat is running locally.</xbar.desc>
# <xbar.dependencies>python</xbar.dependencies>

# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
# <swiftbar.environment>[HOMEBREW_NO_ANALYTICS=1, HOMEBREW_NO_AUTO_UPDATE=1]</swiftbar.environment>

import subprocess
from typing import Optional
import plugin

PLUGIN_ICON = "🐈"
TOMCAT_PROCESS_NAME = "catalina"


def get_tomcat_pid() -> Optional[int]:
  try:
    output = subprocess.check_output(["pgrep", "-o", "-f", TOMCAT_PROCESS_NAME])
    return int(output)
  except:
    return None


def main() -> None:
    tomcat_pid = get_tomcat_pid()

    if not tomcat_pid:
        return

    plugin.print_menu_item(PLUGIN_ICON)
    plugin.print_menu_separator()

    plugin.print_menu_item("Tomcat Is Running")


if __name__ == "__main__":
    main()
