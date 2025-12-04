#!/usr/bin/env python3
import os, requests, json, sys

# --- Environment setup ---
API = os.getenv("NETBOX_API", "http://netbox-docker-netbox-1:8080").rstrip("/")
TOKEN = os.getenv("NETBOX_TOKEN", "").strip()
quiet = "--quiet" in sys.argv  # suppress debug output for Jenkins

# --- Role filtering ---
roles = []
if "--roles" in sys.argv:
    try:
        roles_arg = sys.argv[sys.argv.index("--roles") + 1]
        roles = [r.strip().lower().replace(" ", "-") for r in roles_arg.split(",") if r.strip()]
    except IndexError:
        print("❌ Missing role list after --roles")
        sys.exit(1)
elif "--role" in sys.argv:
    # Backward compatible with single role flag
    try:
        single_role = sys.argv[sys.argv.index("--role") + 1]
        roles = [single_role.lower().replace(" ", "-")]
    except IndexError:
        print("❌ Missing role name after --role")
        sys.exit(1)

# --- Validate environment variables ---
if not API or not TOKEN:
    print("❌ Missing NETBOX_API or NETBOX_TOKEN environment variables.")
    sys.exit(1)

# --- HTTP headers ---
headers = {
    "Authorization": f"Token {TOKEN}",
    "Accept": "application/json"
}

# --- Helper to fetch all devices by role ---
def fetch_devices_by_role(role_slug):
    params = {"limit": 0, "role": role_slug}
    url = f"{API}/api/dcim/devices/"
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=20)
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error while fetching {role_slug}: {e}")
        return []
    if resp.status_code != 200:
        print(f"❌ HTTP {resp.status_code} for role '{role_slug}': {resp.text[:150]}")
        return []
    try:
        data = resp.json()
        return [d.get("name") for d in data.get("results", []) if d.get("name")]
    except ValueError:
        print(f"❌ Invalid JSON for role '{role_slug}'")
        return []

# --- Fetch devices ---
all_devices = []
if roles:
    if not quiet:
        print(f"🎯 Roles to query: {roles}")
    for role in roles:
        devices = fetch_devices_by_role(role)
        all_devices.extend(devices)
else:
    # no role filtering: fetch all devices
    try:
        resp = requests.get(f"{API}/api/dcim/devices/", headers=headers, params={"limit": 0}, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            all_devices = [d.get("name") for d in data.get("results", []) if d.get("name")]
        else:
            print(f"❌ HTTP {resp.status_code}: {resp.text[:150]}")
            sys.exit(1)
    except requests.exceptions.RequestException as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)

# --- Deduplicate ---
unique_devices = sorted(set(all_devices))

# --- Output ---
if quiet:
    print(json.dumps(unique_devices))
else:
    print(f"✅ Found {len(unique_devices)} unique devices:")
    print(json.dumps(unique_devices, indent=2))
