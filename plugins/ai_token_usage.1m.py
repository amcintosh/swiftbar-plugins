#!/usr/bin/env python3

# <xbar.title>AI Token Usage</xbar.title>
# <xbar.version>v1.0</xbar.version>
# <xbar.desc>Show token usage from various clients for the month.</xbar.desc>
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
from itertools import groupby
from pathlib import Path
import plugin
import sys

CODE_ASSIST_PORTAL_URL = "https://codeassist-admin-portal.app.intuit.com/code-assist-market-ui/marketplace?view=products"
TOTAL_BUDGET = 500

CODE_USAGE_CLI = "tokscale@latest"


def get_image_path(size: str):
    return Path(__file__).resolve().parent.parent / "assets" / f"beaker_{size}.png"


def check_error(cmd):
    if cmd.returncode == 1:
        plugin.print_menu_item("❌")
        plugin.print_menu_separator()
        plugin.print_menu_item(cmd.stderr or cmd.stdout)
        sys.exit()


def main() -> None:
    check_error(subprocess.run(
        ["npx", CODE_USAGE_CLI, "graph", "--month"],
        text=True,
        capture_output=True
    ))

    context_cmd = subprocess.run(
        ["npx", CODE_USAGE_CLI, "--month", "--json"],
        text=True,
        capture_output=True
    )
    check_error(context_cmd)

    usage_data = json.loads(context_cmd.stdout)

    fixed_costs_path = Path(__file__).resolve().parent.parent / ".ai_fixed_costs.json"
    fixed_entries = []
    if fixed_costs_path.exists():
        fixed_costs = json.loads(fixed_costs_path.read_text())
        fixed_entries = [{"client": client, "model": "Fixed", "cost": cost} for client, cost in fixed_costs.items()]

    total_cost = usage_data["totalCost"] + sum(e["cost"] for e in fixed_entries)
    total_cost_percent = total_cost / TOTAL_BUDGET * 100

    if total_cost_percent < 25:
        icon = get_image_path("new")
    elif total_cost_percent < 50:
        icon = get_image_path("25")
    elif total_cost_percent < 75:
        icon = get_image_path("50")
    elif total_cost_percent < 90:
        icon = get_image_path("75")
    else:
        icon = get_image_path("full")

    plugin.print_menu_item(f"{total_cost_percent:.0f}%", image=base64.b64encode(icon.read_bytes()).decode())
    plugin.print_menu_separator()

    plugin.print_menu_action(
        f"${total_cost:.2f} / ${TOTAL_BUDGET} budget",
        ["open", CODE_ASSIST_PORTAL_URL]
    )
    plugin.print_menu_separator()

    entries = sorted(
        [e for e in usage_data.get("entries", []) if e["cost"] > 0],
        key=lambda e: (e["client"], e["model"])
    ) + fixed_entries
    for client, group in groupby(entries, key=lambda e: e["client"]):
        client_entries = list(group)
        client_total = sum(e["cost"] for e in client_entries)
        plugin.print_menu_action(f"{client} - ${client_total:.2f}", ["open", CODE_ASSIST_PORTAL_URL])
        for entry in client_entries:
            plugin.print_menu_item(f"{entry["model"]} - ${entry["cost"]:.2f}")
        plugin.print_menu_separator()


if __name__ == "__main__":
    main()
