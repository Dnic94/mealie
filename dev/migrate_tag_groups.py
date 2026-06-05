#!/usr/bin/env python3
"""
Mealie Tag Group Migration Script
==================================
Migrates tags from the "GroupName:TagName" workaround naming convention
to proper Tag Groups.

For every tag whose name contains a separator (default ":"):
  1. Creates a TagGroup for the prefix part if it doesn't already exist
  2. Assigns the tag to that group
  3. Renames the tag to just the suffix part

Example:  "Quelle:tiktok.com"  -> group "Quelle",  tag "tiktok.com"
          "Saison:Winter"      -> group "Saison",   tag "Winter"
          "Hauptzutat:Kaese"   -> group "Hauptzutat", tag "Kaese"

Tags without the separator are left completely untouched.

Usage
-----
  # Preview what would change (no modifications made):
  python migrate_tag_groups.py --url http://localhost:9000 --token TOKEN

  # Apply the migration:
  python migrate_tag_groups.py --url http://localhost:9000 --token TOKEN --apply

  # Authenticate with username/password instead of a token:
  python migrate_tag_groups.py --url http://localhost:9000 -u USER -p PASS --apply

  # Use a different separator (e.g. pipe):
  python migrate_tag_groups.py --url http://localhost:9000 --token TOKEN --separator "|" --apply

Requirements: pip install requests
"""

import argparse
import sys
from typing import Optional

try:
    import requests
except ImportError:
    print("ERROR: 'requests' is not installed. Run:  pip install requests", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# Colour palette assigned to newly created groups (cycles if > 10 groups)
# ---------------------------------------------------------------------------
_PALETTE = [
    "#1976D2",  # blue
    "#43A047",  # green
    "#E53935",  # red
    "#FB8C00",  # orange
    "#8E24AA",  # purple
    "#00897B",  # teal
    "#F4511E",  # deep-orange
    "#3949AB",  # indigo
    "#D81B60",  # pink
    "#00ACC1",  # cyan
    "#6D4C41",  # brown
    "#546E7A",  # blue-grey
]


# ---------------------------------------------------------------------------
# API client
# ---------------------------------------------------------------------------
class MealieClient:
    def __init__(self, base_url: str, token: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}", "Content-Type": "application/json"})

    # -- auth helper ---------------------------------------------------------

    @classmethod
    def from_credentials(cls, base_url: str, username: str, password: str) -> "MealieClient":
        resp = requests.post(
            f"{base_url.rstrip('/')}/api/auth/token",
            data={"username": username, "password": password},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        resp.raise_for_status()
        token = resp.json()["access_token"]
        return cls(base_url, token)

    # -- paginated fetch helpers ---------------------------------------------

    def _get_all(self, path: str) -> list[dict]:
        results: list[dict] = []
        page = 1
        while True:
            resp = self.session.get(f"{self.base_url}{path}", params={"page": page, "perPage": 100})
            resp.raise_for_status()
            data = resp.json()
            results.extend(data["items"])
            if page >= data["total_pages"] or not data["items"]:
                break
            page += 1
        return results

    def get_all_tags(self) -> list[dict]:
        return self._get_all("/api/organizers/tags")

    def get_all_tag_groups(self) -> list[dict]:
        return self._get_all("/api/organizers/tag-groups")

    # -- mutations -----------------------------------------------------------

    def create_tag_group(self, name: str, color: str, position: int) -> dict:
        resp = self.session.post(
            f"{self.base_url}/api/organizers/tag-groups",
            json={"name": name, "color": color, "position": position},
        )
        resp.raise_for_status()
        return resp.json()

    def update_tag(self, tag_id: str, new_name: str, tag_group_id: Optional[str]) -> dict:
        payload: dict = {"name": new_name}
        if tag_group_id is not None:
            payload["tagGroupId"] = tag_group_id
        resp = self.session.put(
            f"{self.base_url}/api/organizers/tags/{tag_id}",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()


# ---------------------------------------------------------------------------
# Migration logic
# ---------------------------------------------------------------------------
def analyse(tags: list[dict], groups: list[dict], separator: str) -> dict:
    """
    Returns a migration plan:
      {
        "groups_to_create":  { prefix: color },
        "tags_to_migrate":   [{ tag, new_name, group_name }],
        "conflicts":         [{ tag, new_name, existing_tag }],
        "skipped":           [tag],          # no separator, left untouched
      }
    """
    existing_group_names: dict[str, dict] = {g["name"]: g for g in groups}
    existing_tag_names: dict[str, dict] = {t["name"]: t for t in tags}

    prefixes_seen: list[str] = []  # keeps insertion order for colour assignment
    groups_to_create: dict[str, str] = {}  # prefix -> colour (assigned at end)
    tags_to_migrate: list[dict] = []
    conflicts: list[dict] = []
    skipped: list[dict] = []

    for tag in tags:
        name: str = tag["name"]
        if separator not in name:
            skipped.append(tag)
            continue

        # Split on the first separator only
        prefix, _, suffix = name.partition(separator)
        prefix = prefix.strip()
        suffix = suffix.strip()

        if not prefix or not suffix:
            skipped.append(tag)
            continue

        # Track which prefixes need new groups
        if prefix not in existing_group_names and prefix not in groups_to_create:
            prefixes_seen.append(prefix)
            groups_to_create[prefix] = ""  # colour filled in below

        # Check for name collision after rename
        if suffix in existing_tag_names and existing_tag_names[suffix]["id"] != tag["id"]:
            conflicts.append({"tag": tag, "new_name": suffix, "existing_tag": existing_tag_names[suffix]})
        else:
            tags_to_migrate.append({"tag": tag, "new_name": suffix, "group_name": prefix})

    # Assign colours - existing groups keep whatever colour they already have;
    # new groups get the next colour in the palette starting after how many
    # existing groups there are (so colours don't collide with existing ones).
    colour_offset = len(existing_group_names)
    for i, prefix in enumerate(prefixes_seen):
        groups_to_create[prefix] = _PALETTE[(colour_offset + i) % len(_PALETTE)]

    return {
        "groups_to_create": groups_to_create,
        "tags_to_migrate": tags_to_migrate,
        "conflicts": conflicts,
        "skipped": skipped,
    }


def print_plan(plan: dict, existing_groups: list[dict], separator: str) -> None:
    existing_group_names = {g["name"]: g for g in existing_groups}

    print("\n" + "=" * 60)
    print("MIGRATION PLAN")
    print("=" * 60)

    # Groups
    if plan["groups_to_create"]:
        print(f"\n  New tag groups to create ({len(plan['groups_to_create'])}):")
        for name, colour in sorted(plan["groups_to_create"].items()):
            print(f"    + {name!r}  (colour {colour})")
    else:
        print("\n  No new tag groups needed (all prefixes already exist).")

    existing_prefix_matches = set()
    for item in plan["tags_to_migrate"]:
        gname = item["group_name"]
        if gname in existing_group_names:
            existing_prefix_matches.add(gname)
    if existing_prefix_matches:
        print(f"\n  Existing groups that will receive tags ({len(existing_prefix_matches)}):")
        for name in sorted(existing_prefix_matches):
            g = existing_group_names[name]
            print(f"    = {name!r}  (id {g['id']})")

    # Tags to migrate
    print(f"\n  Tags to rename & assign ({len(plan['tags_to_migrate'])}):")
    by_group: dict[str, list] = {}
    for item in plan["tags_to_migrate"]:
        by_group.setdefault(item["group_name"], []).append(item)
    for group_name in sorted(by_group):
        print(f"\n    Group: {group_name!r}")
        for item in sorted(by_group[group_name], key=lambda x: x["new_name"]):
            old = item["tag"]["name"]
            new = item["new_name"]
            print(f"      {old!r}  ->  {new!r}")

    # Conflicts
    if plan["conflicts"]:
        print(f"\n  [!] CONFLICTS - these tags will be SKIPPED ({len(plan['conflicts'])}):")
        print("     A tag with the target name already exists.")
        for c in plan["conflicts"]:
            print(
                f"      {c['tag']['name']!r}  ->  {c['new_name']!r}"
                f"  (conflicts with existing tag id {c['existing_tag']['id']})"
            )

    # Skipped (no separator)
    print(f"\n  Tags without separator {separator!r} (untouched): {len(plan['skipped'])}")

    print("\n" + "=" * 60)
    total = len(plan["tags_to_migrate"]) + len(plan["conflicts"]) + len(plan["skipped"])
    print(
        f"  Summary: {len(plan['tags_to_migrate'])} to migrate, "
        f"{len(plan['conflicts'])} conflicts (skipped), "
        f"{len(plan['skipped'])} unaffected tags"
    )
    print("=" * 60 + "\n")


def run_migration(client: MealieClient, plan: dict, existing_groups: list[dict]) -> None:
    existing_group_map: dict[str, dict] = {g["name"]: g for g in existing_groups}

    # 1. Create missing groups
    created_groups: dict[str, dict] = {}
    if plan["groups_to_create"]:
        print(f"Creating {len(plan['groups_to_create'])} tag group(s)...")
        position = len(existing_group_map)
        for name, colour in sorted(plan["groups_to_create"].items()):
            print(f"  + Creating group {name!r} ({colour}) ... ", end="", flush=True)
            try:
                g = client.create_tag_group(name, colour, position)
                created_groups[name] = g
                position += 1
                print(f"OK  (id {g['id']})")
            except requests.HTTPError as exc:
                print(f"FAILED: {exc}")
                sys.exit(1)

    group_map = {**{g["name"]: g for g in existing_groups}, **created_groups}

    # 2. Rename & assign tags
    print(f"\nMigrating {len(plan['tags_to_migrate'])} tag(s)...")
    ok = 0
    failed = 0
    for item in sorted(plan["tags_to_migrate"], key=lambda x: x["tag"]["name"]):
        tag = item["tag"]
        new_name = item["new_name"]
        group = group_map[item["group_name"]]
        print(
            f"  {tag['name']!r}  ->  {new_name!r}  (group {item['group_name']!r}) ... ",
            end="",
            flush=True,
        )
        try:
            client.update_tag(tag["id"], new_name, group["id"])
            print("OK")
            ok += 1
        except requests.HTTPError as exc:
            print(f"FAILED: {exc}")
            failed += 1

    print(f"\nDone.  {ok} succeeded, {failed} failed.")
    if plan["conflicts"]:
        print(
            f"\n[!] {len(plan['conflicts'])} tag(s) were skipped due to name conflicts and must be resolved manually:"
        )
        for c in plan["conflicts"]:
            print(
                f"   {c['tag']['name']!r}  (id {c['tag']['id']})  ->  wanted {c['new_name']!r},"
                f" but that name is already taken by id {c['existing_tag']['id']}"
            )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Migrate Mealie tags from 'Group:Tag' naming to Tag Groups.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--url", required=True, help="Mealie base URL, e.g. http://localhost:9000")
    parser.add_argument("--token", help="Mealie API token")
    parser.add_argument("-u", "--username", help="Mealie username (alternative to --token)")
    parser.add_argument("-p", "--password", help="Mealie password (alternative to --token)")
    parser.add_argument(
        "--separator",
        default=":",
        help="Separator between group prefix and tag name (default: ':')",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply the migration. Without this flag only a dry-run preview is shown.",
    )
    args = parser.parse_args()

    # -- authenticate --------------------------------------------------------
    if args.token:
        client = MealieClient(args.url, args.token)
    elif args.username and args.password:
        print("Authenticating with username/password...")
        try:
            client = MealieClient.from_credentials(args.url, args.username, args.password)
            print("  Authenticated OK.\n")
        except requests.HTTPError as exc:
            print(f"  Authentication failed: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print("ERROR: Provide either --token or both --username and --password.", file=sys.stderr)
        parser.print_help()
        sys.exit(1)

    # -- fetch current state -------------------------------------------------
    print("Fetching tags...", end="", flush=True)
    try:
        tags = client.get_all_tags()
        print(f" {len(tags)} tags found.")

        print("Fetching tag groups...", end="", flush=True)
        groups = client.get_all_tag_groups()
        print(f" {len(groups)} groups found.")
    except requests.HTTPError as exc:
        print(f"\nFailed to fetch data: {exc}", file=sys.stderr)
        sys.exit(1)

    # -- analyse -------------------------------------------------------------
    plan = analyse(tags, groups, args.separator)
    print_plan(plan, groups, args.separator)

    if not plan["tags_to_migrate"] and not plan["groups_to_create"]:
        print("Nothing to do.")
        return

    # -- apply or dry-run ----------------------------------------------------
    if not args.apply:
        print("This was a DRY RUN. No changes were made.")
        print("Re-run with --apply to execute the migration.\n")
        return

    print("Applying migration...\n")
    run_migration(client, plan, groups)


if __name__ == "__main__":
    main()
