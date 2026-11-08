"""Read shared albums in the new CloudKit format (iOS 27 "Upgrade Shared Album"). Version 1.0.0

Upgraded shared albums are no longer served by the legacy ``sharedstreams`` service. They live in
CloudKit zones named ``SharedCollection-<UUID>``, where Apple rejects index queries
(400 BAD_REQUEST / "Index has invalid data"). The photos are read from the zone's change feed
(``/changes/zone``) instead, the same approach as in neuhausf/icloud_shared_photos (MIT, library.py).
Read only. Uses pyicloud internals (``library._client._client._http``): re-check after pyicloud updates.
"""
import logging

logger = logging.getLogger(__name__)
PREFIX = "SharedCollection-"
EXCLUDE_FLAGS = ("isDeleted", "isExpunged", "isHidden", "trashReason")


def _field(fields, name):
    v = fields.get(name)
    return v.get("value") if isinstance(v, dict) else None


def _changes(lib, types):
    zr = {"zoneID": dict(lib.zone_id), "desiredRecordTypes": types}
    http = lib._client._client._http
    out = []
    while True:
        d = http.post("/changes/zone", {"zones": [zr], "resultsLimit": 200})
        z = (d.get("zones") or [{}])[0]
        if z.get("serverErrorCode"):
            raise RuntimeError("%s: %s" % (z.get("serverErrorCode"), z.get("reason", "")))
        out += [r for r in z.get("records") or [] if isinstance(r, dict) and not r.get("deleted") and not r.get("serverErrorCode")]
        if not z.get("moreComing") or not z.get("syncToken"):
            return out
        zr["syncToken"] = z["syncToken"]


def title(lib):
    t = None
    for r in _changes(lib, ["cloudkit.share"]):
        v = (r.get("fields") or {}).get("cloudkit.title", {}).get("value")
        if isinstance(v, str) and v.strip():
            t = v.strip()
    return t


def photos(lib):
    rec = _changes(lib, ["CPLMaster", "CPLAsset"])
    masters = {r["recordName"]: r for r in rec if r.get("recordType") == "CPLMaster"}
    out = []
    for r in rec:
        if r.get("recordType") != "CPLAsset":
            continue
        f = r.get("fields") or {}
        if any(_field(f, x) for x in EXCLUDE_FLAGS):
            continue
        ref = _field(f, "masterRef")
        m = masters.get(ref.get("recordName")) if isinstance(ref, dict) else None
        if m is not None:
            out.append(lib.asset_type(lib.service, m, r))
    return out


def find(api, name):
    """Photos of the new-format shared album with this title, or None if there is none."""
    for key, lib in api.photos.libraries.items():
        if not str(key).startswith(PREFIX):
            continue
        try:
            matches = title(lib) == name
        except Exception as e:  # zone not readable: carry on with the legacy format as before
            logger.warning("Zone %s not readable: %s", key, e)
            continue
        if matches:
            found = photos(lib)  # errors must not be swallowed here, the sync would delete local photos
            logger.info("New-format shared album %s: %d photos", name, len(found))
            return found
    return None


def names(api):
    out = []
    for key, lib in api.photos.libraries.items():
        if str(key).startswith(PREFIX):
            try:
                out.append(title(lib) or str(key))
            except Exception as e:
                out.append("%s (error: %s)" % (key, e))
    return out


if __name__ == "__main__":
    # offline self-check
    class L:
        zone_id = {}
        service = None
        asset_type = staticmethod(lambda s, m, a: (m["recordName"], a["recordName"]))
    rec = [{"recordType": "CPLMaster", "recordName": "m1"}, {"recordType": "CPLMaster", "recordName": "m2"},
           {"recordType": "CPLAsset", "recordName": "a1", "fields": {"masterRef": {"value": {"recordName": "m1"}}}},
           {"recordType": "CPLAsset", "recordName": "a2", "fields": {"masterRef": {"value": {"recordName": "m2"}}, "isDeleted": {"value": 1}}},
           {"recordType": "CPLAsset", "recordName": "a3", "fields": {"masterRef": {"value": {"recordName": "x"}}}}]
    _changes = lambda lib, types: rec
    assert photos(L) == [("m1", "a1")]
    print("ok")
