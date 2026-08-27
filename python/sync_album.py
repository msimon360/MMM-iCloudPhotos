#! /usr/bin/env python3
"""One-way sync of an iCloud album to a local folder. No crop, resize, or filters."""

import argparse
import logging
import os
import sys
from pathlib import Path

MODULE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(MODULE_ROOT / "python"))

from icloud_photos import IcloudPhotos  # noqa: E402

logger = logging.getLogger("MMM-iCloudPhotos")


def _parse_env_value(value):
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
        return value[1:-1]
    return value


def load_dotenv(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        os.environ.setdefault(key, _parse_env_value(value))


def _exception_chain_text(exc):
    parts = []
    seen = set()
    current = exc
    while current is not None and id(current) not in seen:
        seen.add(id(current))
        parts.append(str(current))
        current = current.__cause__ or current.__context__
    return "\n".join(parts)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )
    # pyicloud logs "Session file does not exist" at INFO on first login.
    logging.getLogger("pyicloud.session").setLevel(logging.WARNING)
    logging.getLogger("pyicloud.base").setLevel(logging.WARNING)
    load_dotenv(MODULE_ROOT / ".env")

    parser = argparse.ArgumentParser(description="One-way iCloud album sync")
    parser.add_argument("user", nargs="?", help="icloud user (or ICLOUD_USER in .env)")
    parser.add_argument("password", nargs="?", help="password (or ICLOUD_PASSWORD in .env)")
    parser.add_argument("--album", help="icloud album name", default=os.environ.get("ICLOUD_ALBUM"))
    parser.add_argument("--output", help="local folder", default=os.environ.get("ICLOUD_OUTPUT"))
    parser.add_argument("--list", help="list albums and exit", action="store_true")
    args = parser.parse_args()

    user = args.user or os.environ.get("ICLOUD_USER")
    password = args.password or os.environ.get("ICLOUD_PASSWORD")
    if not user or not password:
        print("Set ICLOUD_USER and ICLOUD_PASSWORD in .env, or pass them as arguments.")
        sys.exit(1)

    print("Signing in to iCloud (first run creates a session; 2FA may follow)...")
    sys.stdout.flush()
    try:
        api = IcloudPhotos(user, password)
    except Exception as exc:
        text = _exception_chain_text(exc).lower()
        if "-20209" in text or "locked" in text or "iforgot" in text:
            print(
                "Apple has locked this Apple ID (error -20209).\n"
                "pyicloud may also say 'Invalid email/password combination' — that is the same lock,\n"
                "not proof that .env is wrong.\n\n"
                "1. Unlock at https://iforgot.apple.com or https://appleid.apple.com\n"
                "   and confirm you can sign in on a phone or icloud.com.\n"
                "2. If you reset the password, put the NEW password in .env.\n"
                "3. Delete tmp/pyicloud/ so a stale session is not reused.\n"
                "4. Wait before retrying. Do not run sync in a loop."
            )
            sys.exit(1)
        if "invalid email/password" in text:
            print(
                "iCloud rejected the username/password.\n"
                "If you just reset the Apple ID password, update ICLOUD_PASSWORD in .env.\n"
                "Use the real Apple ID password, not an app-specific password."
            )
            sys.exit(1)
        raise
    if args.list:
        personal = api.get_personal_album_names()
        shared = api.get_shared_album_names()
        print("Albums (personal):")
        if personal:
            for name in personal:
                print(name)
        else:
            print("(none)")
        print("Shared Albums:")
        if shared:
            for name in shared:
                print(name)
        else:
            print("(none)")
        return

    album = args.album
    if not album:
        print("Pass --album NAME or set ICLOUD_ALBUM in .env")
        sys.exit(1)

    output = args.output or str(MODULE_ROOT / "media" / album.replace("/", "_").strip())
    try:
        stats = api.sync_album(album, output)
    except KeyError as exception:
        print("Could not find album:", exception)
        print("Run with --list to see personal albums and Shared Albums.")
        print("If a personal album uses the same name, pass --album shared:NAME")
        sys.exit(1)

    logger.info(
        "Sync complete: %d remote, %d downloaded, %d already present, %d deleted, %d failed -> %s",
        stats["remote"],
        stats["downloaded"],
        stats["skipped"],
        stats["deleted"],
        stats["failed"],
        stats["folder"],
    )
    print(
        "SYNC_OK remote={remote} downloaded={downloaded} skipped={skipped} "
        "deleted={deleted} failed={failed} folder={folder}".format(**stats)
    )


if __name__ == "__main__":
    main()
