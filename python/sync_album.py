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


def load_dotenv(path):
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        os.environ.setdefault(key, value)


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
    api = IcloudPhotos(user, password)
    if args.list:
        print("Albums:")
        for album in api.get_albums():
            print(getattr(album, "name", album))
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
        print("Run with --list to see album names")
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
