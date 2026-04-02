#!/usr/bin/env python3

# <xbar.title>HSX Market Calendar</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.desc>Show HSX market openings, IPOs, and adjustments.</xbar.desc>
# <xbar.author>Andrew McIntosh</xbar.author>
# <xbar.author.github>amcintosh</xbar.author.github>
# <xbar.dependencies>python</xbar.dependencies>
#
# <swiftbar.hideRunInTerminal>true</swiftbar.hideRunInTerminal>
# <swiftbar.hideDisablePlugin>true</swiftbar.hideDisablePlugin>
# <swiftbar.hideSwiftBar>true</swiftbar.hideSwiftBar>
import base64
import json
import subprocess
from pathlib import Path
from typing import Dict, List
import plugin


HSX_ICON_PATH = Path(__file__).resolve().parent / "hsx.ico"
OFFCALL_ICON = "🟢"
ONCALL_ICON = "🔴"
HSX_CLI = "/Users/amcintosh3/Personal/hsx-cli/.venv/bin/hsx"

CATEGORY_IPO = "ipo"
CATEGORY_CASHOUT = "cashout"
CATEGORY_STARBOND = "starbond"
CATEGORY_OPENING = "opening"
CATEGORY_DELISTING = "delisting"
CATEGORY_DERIVATIVE_HALT = "derivative_halt"

CATEGORY_LABELS = {
    CATEGORY_IPO: "IPO",
    CATEGORY_CASHOUT: "Cash-outs",
    CATEGORY_STARBOND: "StarBond Adjustments",
    CATEGORY_OPENING: "Wide Releases / Openings",
    CATEGORY_DELISTING: "Delistings",
    CATEGORY_DERIVATIVE_HALT: "Derivative Halts",
}


def _print_section(name: str, items: List[Dict[str, str]]):
    if items:
        plugin.print_menu_item(CATEGORY_LABELS[name])
    for item in items:
        plugin.print_menu_action(f"{item["name"]} ({item["symbol"]})", ["open", item["url"]])
    if items:
        plugin.print_menu_separator()


def main() -> None:
    context_cmd = subprocess.run(
        [HSX_CLI, "calendar", "--json"],
        text=True,
        capture_output=True
    )

    if context_cmd.returncode == 1:
        plugin.print_menu_item("❌")
        plugin.print_menu_separator()
        plugin.print_menu_item(context_cmd.stderr or context_cmd.stdout)
        return

    calendar_data = json.loads(context_cmd.stdout)

    icon_b64 = base64.b64encode(HSX_ICON_PATH.read_bytes()).decode()
    plugin.print_menu_item("", image=icon_b64)
    plugin.print_menu_separator()

    _print_section(CATEGORY_IPO, calendar_data.get(CATEGORY_IPO))
    _print_section(CATEGORY_STARBOND, calendar_data.get(CATEGORY_STARBOND))
    _print_section(CATEGORY_CASHOUT, calendar_data.get(CATEGORY_CASHOUT))
    _print_section(CATEGORY_DERIVATIVE_HALT, calendar_data.get(CATEGORY_DERIVATIVE_HALT))
    _print_section(CATEGORY_OPENING, calendar_data.get(CATEGORY_OPENING))
    _print_section(CATEGORY_DELISTING, calendar_data.get(CATEGORY_DELISTING))


if __name__ == "__main__":
    main()
