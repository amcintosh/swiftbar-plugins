#!/usr/bin/env python3

# <xbar.title>Pager Duty Schedule</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.desc>Show pager duty schedule and oncall status.</xbar.desc>
# <xbar.author>Andrew McIntosh</xbar.author>
# <xbar.author.github>amcintosh</xbar.author.github>
# <xbar.dependencies>python</xbar.dependencies>
#
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
import configparser
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

import plugin

SECRETS_FILE = Path(__file__).resolve().parent.parent / ".secrets.ini"

PAGER_ICON = "📟"
OFFCALL_ICON = "🟢"
ONCALL_ICON = "🔴"
PAGER_DUTY_CLI = "/Users/amcintosh3/work/tools/pager-duty-cli/.venv/bin/pager-duty"


def main() -> None:
    secrets = configparser.ConfigParser()
    secrets.read(SECRETS_FILE)
    pager_duty_token = secrets.get("secrets", "pager_duty_token", fallback="")

    context_cmd = subprocess.run(
        [PAGER_DUTY_CLI, "oncall", "--json"],
        text=True,
        capture_output=True,
        env={**os.environ, "PAGER_DUTY_TOKEN": pager_duty_token},
    )

    if context_cmd.returncode == 1:
        plugin.print_menu_item("❌")
        plugin.print_menu_separator()
        plugin.print_menu_item(context_cmd.stderr or context_cmd.stdout)
        return

    pager_data = json.loads(context_cmd.stdout)

    plugin.print_menu_item(PAGER_ICON if pager_data.get("status") != "Oncall" else ONCALL_ICON)
    plugin.print_menu_separator()

    schedules = pager_data.get("schedules", [])
    grouped: dict[str, list] = {}
    for schedule in schedules:
        name = schedule.get("name")
        grouped.setdefault(name, []).append(schedule)

    for name, entries in grouped.items():
        plugin.print_menu_separator()
        group_status = ONCALL_ICON if any(entry.get("status") == "Oncall" for entry in entries) else OFFCALL_ICON
        url = entries[0].get("url", "")
        plugin.print_menu_action(f"{group_status} **{name}**", ["open", url], md=True)
        for entry in entries:
            start = datetime.fromisoformat(entry.get("start")).astimezone().strftime("%b %-d, %-I:%M %p")
            end = datetime.fromisoformat(entry.get("end")).astimezone().strftime("%b %-d, %-I:%M %p")
            plugin.print_menu_item(f"{start} - {end}")


if __name__ == "__main__":
    main()
