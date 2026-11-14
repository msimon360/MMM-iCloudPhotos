const fs = require("fs");
const path = require("path");

const TRUST_COOKIE = "X-APPLE-WEBAUTH-HSA-TRUST";
const EVENT_TITLE = "iCloud Session Expires";

function cookieDir(moduleRoot) {
  return path.join(moduleRoot, "tmp", "pyicloud");
}

function calendarPath(moduleRoot) {
  return path.resolve(moduleRoot, "..", "..", "config", "icloud-session-expires.ics");
}

function liveJars(moduleRoot) {
  const dir = cookieDir(moduleRoot);
  if (!fs.existsSync(dir)) {
    return [];
  }
  return fs
    .readdirSync(dir)
    .filter((name) => name.endsWith(".cookiejar"))
    .filter((name) => !name.startsWith("BAK"))
    .filter((name) => !name.toLowerCase().startsWith("youexample"))
    .map((name) => path.join(dir, name));
}

function parseExpires(value) {
  const ms = Date.parse(String(value).trim().replace(" ", "T"));
  return Number.isNaN(ms) ? null : ms;
}

function readJar(file) {
  const text = fs.readFileSync(file, "utf8");
  let trust = null;
  let latest = null;
  for (const line of text.split(/\r?\n/)) {
    if (!line.startsWith("Set-Cookie3:")) {
      continue;
    }
    const body = line.slice("Set-Cookie3:".length).trim();
    const eq = body.indexOf("=");
    const name = eq === -1 ? body : body.slice(0, eq);
    const match = body.match(/expires="([^"]+)"/);
    if (!match) {
      continue;
    }
    const ms = parseExpires(match[1]);
    if (ms === null) {
      continue;
    }
    if (name === TRUST_COOKIE) {
      trust = ms;
    }
    if (latest === null || ms > latest) {
      latest = ms;
    }
  }
  const stat = fs.statSync(file);
  const expiresMs = trust !== null ? trust : latest;
  return {
    expiresMs,
    signature: `${stat.ino}:${stat.mtimeMs}:${stat.size}:${expiresMs || ""}`,
  };
}

function readSession(moduleRoot) {
  const jars = liveJars(moduleRoot).map(readJar).filter((jar) => jar.expiresMs);
  if (!jars.length) {
    return { expiresMs: null, signature: "" };
  }
  jars.sort((a, b) => b.expiresMs - a.expiresMs);
  return jars[0];
}

function icsStamp(ms) {
  return new Date(ms).toISOString().replace(/[-:]/g, "").replace(/\.\d{3}Z$/, "Z");
}

function buildIcs(expiresMs) {
  const start = icsStamp(expiresMs);
  const end = icsStamp(expiresMs + 60 * 60 * 1000);
  return [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//MagicMirror//MMM-iCloudPhotos//EN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "BEGIN:VEVENT",
    "UID:icloud-session-expires@magicmirror.local",
    `DTSTAMP:${start}`,
    `DTSTART:${start}`,
    `DTEND:${end}`,
    `SUMMARY:${EVENT_TITLE}`,
    "END:VEVENT",
    "END:VCALENDAR",
    "",
  ].join("\r\n");
}

function writeCalendar(moduleRoot, expiresMs) {
  const dest = calendarPath(moduleRoot);
  if (!expiresMs) {
    return { path: dest, updated: false };
  }
  const next = buildIcs(expiresMs);
  let current = "";
  try {
    current = fs.readFileSync(dest, "utf8");
  } catch (err) {
    current = "";
  }
  if (current === next) {
    return { path: dest, updated: false, expiresMs };
  }
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.writeFileSync(dest, next);
  return { path: dest, updated: true, expiresMs };
}

module.exports = {
  EVENT_TITLE,
  calendarPath,
  readSession,
  writeCalendar,
};
