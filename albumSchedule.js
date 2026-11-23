const fs = require("fs");
const path = require("path");

const LIVE_SCHEDULE = path.join("config", "album-schedule.json");

function schedulePath(moduleRoot, config) {
  const configured = config && config.scheduleFile;
  if (configured) {
    return path.isAbsolute(configured)
      ? configured
      : path.resolve(moduleRoot, "..", "..", configured);
  }
  return path.resolve(moduleRoot, "..", "..", LIVE_SCHEDULE);
}

function dayKey(month, day) {
  return month * 100 + day;
}

function activeEntry(entries, now) {
  if (!Array.isArray(entries) || !entries.length) {
    return null;
  }
  const today = dayKey(now.getMonth() + 1, now.getDate());
  let current = null;
  let currentKey = -1;
  let latest = null;
  let latestKey = -1;
  entries.forEach((entry) => {
    const month = Number(entry && entry.month);
    const day = Number(entry && entry.day);
    const album = entry && String(entry.album || "").trim();
    if (!album || !Number.isInteger(month) || month < 1 || month > 12) {
      return;
    }
    if (!Number.isInteger(day) || day < 1 || day > 31) {
      return;
    }
    const key = dayKey(month, day);
    if (key >= latestKey) {
      latest = { album, month, day };
      latestKey = key;
    }
    if (key <= today && key >= currentKey) {
      current = { album, month, day };
      currentKey = key;
    }
  });
  return current || latest;
}

function scheduledAlbumName(album, library) {
  const name = String(album || "").trim();
  if (!name || name.startsWith("shared:") || name.startsWith("personal:")) {
    return name;
  }
  if (String(library || "personal").trim().toLowerCase() === "shared") {
    return `shared:${name}`;
  }
  return `personal:${name}`;
}

function readSchedule(file, now) {
  if (!fs.existsSync(file)) {
    return { file, found: false };
  }
  let parsed;
  try {
    parsed = JSON.parse(fs.readFileSync(file, "utf8"));
  } catch (err) {
    return { file, found: true, error: "Album schedule is not valid JSON" };
  }
  const entries = Array.isArray(parsed) ? parsed : parsed && parsed.albums;
  const library = Array.isArray(parsed) ? "personal" : parsed && parsed.library;
  const active = activeEntry(entries, now || new Date());
  if (!active) {
    return { file, found: true, error: "Album schedule has no usable start dates" };
  }
  return {
    file,
    found: true,
    album: active.album,
    syncAlbum: scheduledAlbumName(active.album, library),
    month: active.month,
    day: active.day,
  };
}

module.exports = {
  schedulePath,
  activeEntry,
  scheduledAlbumName,
  readSchedule,
};
