import json
import logging
import os
import sys

from pyicloud import PyiCloudService
from tqdm import tqdm

logger = logging.getLogger(__name__)


class IcloudPhotos:
    def __init__(self, user, password):
        self.api = self._connect(user, password)

    @staticmethod
    def _connect(user, password):
        cookie_directory = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
            "tmp",
            "pyicloud",
        )
        os.makedirs(cookie_directory, exist_ok=True)
        api = PyiCloudService(user, password, cookie_directory=cookie_directory)

        if getattr(api, "requires_2fa", False):
            # Constructor already pushed a trusted-device code. Calling
            # request_2fa_code() again would force SMS verification.
            if not sys.stdin.isatty():
                raise RuntimeError(
                    "iCloud 2FA is required. Run scripts/sync-once.sh in a terminal once, "
                    "enter the 6-digit code from an Apple device, then restart MagicMirror."
                )
            print("Two-factor authentication required.")
            print("Wait for this prompt, then enter the 6-digit code shown on your iPhone/iPad/Mac.")
            print("That is the Apple popup code, not an SMS.")
            sys.stdout.flush()
            code = input("Enter the 6-digit Apple device code: ").strip()
            if hasattr(api, "_set_two_factor_delivery_state"):
                api._set_two_factor_delivery_state("trusted_device")
            if not api.validate_2fa_code(code):
                print("Failed to verify verification code")
                sys.exit(1)
            if hasattr(api, "is_trusted_session") and not api.is_trusted_session:
                result = api.trust_session()
                print("Session trust result:", result)
        elif getattr(api, "requires_2sa", False):
            if not sys.stdin.isatty():
                raise RuntimeError(
                    "iCloud two-step authentication is required. Run scripts/sync-once.sh in a terminal once."
                )
            print("Two-step authentication required. Your trusted devices are:")
            devices = api.trusted_devices
            for i, device in enumerate(devices):
                print(
                    "  %s: %s"
                    % (
                        i,
                        device.get("deviceName", "SMS to %s" % device.get("phoneNumber")),
                    )
                )
            device_idx = int(input("Which device would you like to use? [0]: ") or "0")
            device = devices[device_idx]
            if not api.send_verification_code(device):
                print("Failed to send verification code")
                sys.exit(1)
            code = input("Please enter validation code: ").strip()
            if not api.validate_verification_code(device, code):
                print("Failed to verify verification code")
                sys.exit(1)

        return api

    def list_album(self, album):
        return list(self.api.photos.albums[album])

    def get_albums(self):
        return self.api.photos.albums

    @staticmethod
    def _asset_id(photo):
        return str(getattr(photo, "id", None) or getattr(photo, "asset_id", None) or photo.filename)

    @staticmethod
    def _safe_filename(photo, used):
        name = os.path.basename(getattr(photo, "filename", None) or "") or (
            "%s.bin" % IcloudPhotos._asset_id(photo)
        )
        name = name.replace("\x00", "").strip() or ("%s.bin" % IcloudPhotos._asset_id(photo))
        stem, ext = os.path.splitext(name)
        candidate = name
        n = 2
        while candidate in used:
            candidate = "%s_%d%s" % (stem, n, ext)
            n += 1
        used.add(candidate)
        return candidate

    def sync_album(self, album, folder):
        os.makedirs(folder, exist_ok=True)
        manifest_path = os.path.join(folder, ".icloud-sync.json")
        try:
            with open(manifest_path, "r", encoding="utf-8") as fh:
                manifest = json.load(fh)
        except (OSError, ValueError):
            manifest = {"album": album, "files": {}}
        old_files = manifest.get("files") or {}

        photos = self.list_album(album)
        used_names = set()
        new_files = {}
        downloaded = 0
        skipped = 0
        failed = 0

        for photo in tqdm(photos, desc="Syncing photos", unit="photo"):
            asset_id = IcloudPhotos._asset_id(photo)
            filename = IcloudPhotos._safe_filename(photo, used_names)
            dest = os.path.join(folder, filename)
            previous = old_files.get(asset_id) or {}
            expected_size = getattr(photo, "size", None)
            if os.path.isfile(dest) and expected_size and os.path.getsize(dest) == expected_size:
                new_files[asset_id] = {"filename": filename, "size": expected_size}
                skipped += 1
                continue
            data = photo.download()
            if hasattr(data, "raw"):
                data = data.raw.read()
            if not data:
                logger.error("Download failed for %s", filename)
                failed += 1
                continue
            with open(dest, "wb") as fh:
                fh.write(data)
            new_files[asset_id] = {"filename": filename, "size": len(data)}
            downloaded += 1
            old_name = previous.get("filename")
            if old_name and old_name != filename:
                leftover = os.path.join(folder, old_name)
                if os.path.isfile(leftover):
                    os.remove(leftover)

        deleted = 0
        for asset_id, meta in old_files.items():
            if asset_id in new_files:
                continue
            filename = (meta or {}).get("filename")
            if not filename:
                continue
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                os.remove(path)
                deleted += 1

        with open(manifest_path, "w", encoding="utf-8") as fh:
            json.dump({"album": album, "files": new_files}, fh, indent=2)
        return {
            "album": album,
            "folder": folder,
            "remote": len(photos),
            "downloaded": downloaded,
            "skipped": skipped,
            "deleted": deleted,
            "failed": failed,
        }
