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
import hashlib
import json
import os
import re
import shutil
import sqlite3
import subprocess
import tempfile
import urllib.request
import urllib.error
from itertools import groupby
from pathlib import Path
import plugin
import sys

CODE_ASSIST_PORTAL_URL = "https://codeassist-admin-portal.app.intuit.com/code-assist-market-ui/marketplace?view=products"
TOTAL_BUDGET = 500

CODE_USAGE_CLI = "tokscale@latest"

CLAUDE_AI_BASE_URL = "https://claude.ai/api"
CLAUDE_SESSION_KEY_ENV = "CLAUDE_SESSION_KEY"
CHROME_COOKIE_PATHS = [
    Path.home() / "Library/Application Support/Google/Chrome/Default/Cookies",
    Path.home() / "Library/Application Support/Google/Chrome/Profile 1/Cookies",
    Path.home() / "Library/Application Support/BraveSoftware/Brave-Browser/Default/Cookies",
    Path.home() / "Library/Application Support/Microsoft Edge/Default/Cookies",
    Path.home() / "Library/Application Support/Arc/User Data/Default/Cookies",
]
CLAUDE_AI_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://claude.ai/",
}


def _chrome_safe_storage_key() -> bytes | None:
    result = subprocess.run(
        ["security", "find-generic-password", "-s", "Chrome Safe Storage", "-w"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        return None
    return hashlib.pbkdf2_hmac("sha1", result.stdout.strip().encode(), b"saltysalt", 1003, dklen=16)


def _decrypt_chrome_cookie(encrypted: bytes, derived_key: bytes) -> str | None:
    if not encrypted.startswith(b"v10"):
        return None
    result = subprocess.run(
        ["openssl", "enc", "-aes-128-cbc", "-d", "-nosalt", "-nopad",
         "-K", derived_key.hex(), "-iv", (b" " * 16).hex()],
        input=encrypted[3:], capture_output=True,
    )
    if result.returncode != 0:
        return None
    raw = result.stdout
    match = re.search(rb"sk-ant-[A-Za-z0-9_\-]+", raw[:-raw[-1]])
    return match.group().decode() if match else None


def get_claude_session_key() -> str | None:
    key = os.environ.get(CLAUDE_SESSION_KEY_ENV)
    if key:
        return key
    derived_key = _chrome_safe_storage_key()
    if not derived_key:
        return None
    for cookie_path in CHROME_COOKIE_PATHS:
        if not cookie_path.exists():
            continue
        tmp = Path(tempfile.mktemp(suffix=".db"))
        try:
            shutil.copy2(cookie_path, tmp)
            conn = sqlite3.connect(tmp)
            row = conn.execute(
                "SELECT encrypted_value FROM cookies "
                "WHERE host_key LIKE '%claude.ai%' AND name='sessionKey' LIMIT 1"
            ).fetchone()
            conn.close()
            if row:
                session_key = _decrypt_chrome_cookie(bytes(row[0]), derived_key)
                if session_key:
                    return session_key
        except Exception:
            pass
        finally:
            tmp.unlink(missing_ok=True)
    return None


def _claude_api_get(endpoint: str, session_key: str) -> dict:
    req = urllib.request.Request(
        f"{CLAUDE_AI_BASE_URL}{endpoint}",
        headers={"Content-Type": "application/json", "Cookie": f"sessionKey={session_key}", **CLAUDE_AI_HEADERS},
    )
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode())


def get_claude_app_cost(claude_code_cost: float) -> float | None:
    """Return the claude.ai app spend (total API spend minus claude code spend), or None on failure."""
    session_key = get_claude_session_key()
    if not session_key:
        return None
    try:
        account = _claude_api_get("/account", session_key)
        memberships = account.get("memberships", [])
        if not memberships:
            return None
        org_id = memberships[0]["organization"]["uuid"]
        usage = _claude_api_get(f"/organizations/{org_id}/usage", session_key)
        extra = usage.get("extra_usage", {})
        if not extra or not extra.get("is_enabled"):
            return None
        total_cents = extra.get("used_credits", 0)
        return max(0.0, total_cents / 100 - claude_code_cost)
    except Exception:
        return None


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

    claude_code_cost = sum(
        e["cost"] for e in usage_data.get("entries", [])
        if e.get("client", "").lower() == "claude" and e["cost"] > 0
    )
    claude_app_cost = get_claude_app_cost(claude_code_cost)
    claude_app_entries = (
        [{"client": "claude", "model": "claude app", "cost": claude_app_cost}]
        if claude_app_cost is not None and claude_app_cost > 0
        else []
    )

    total_cost = usage_data["totalCost"] + sum(e["cost"] for e in fixed_entries) + sum(e["cost"] for e in claude_app_entries)
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
        [e for e in usage_data.get("entries", []) if e["cost"] > 0] + claude_app_entries,
        key=lambda e: (e["client"], e["model"] == "claude app", e["model"])
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
