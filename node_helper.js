const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const NodeHelper = require("node_helper");
const sessionExpiry = require("./sessionExpiry");
const albumSchedule = require("./albumSchedule");

module.exports = NodeHelper.create({
  start() {
    this.config = null;
    this.timer = null;
    this.running = false;
    this.pausedSignature = null;
  },

  socketNotificationReceived(notification, payload) {
    if (notification !== "ICLOUD_PHOTOS_CONFIG") {
      return;
    }
    this.config = payload || {};
    if (this.timer) {
      clearInterval(this.timer);
    }
    const interval = this.config.syncInterval || 6 * 60 * 60 * 1000;
    if (this.config.runOnStart !== false) {
      this.runSync();
    }
    this.timer = setInterval(() => this.runSync(), interval);
  },

  outputDir() {
    if (this.config.outputDir) {
      return path.isAbsolute(this.config.outputDir)
        ? this.config.outputDir
        : path.resolve(this.path, "..", "..", this.config.outputDir);
    }
    return path.resolve(this.path, "..", "MMM-ImagesPhotos", "uploads");
  },

  pythonBin() {
    return path.join(this.path, "venv", "bin", "python");
  },

  setStatus(message, extra) {
    this.sendSocketNotification("ICLOUD_PHOTOS_STATUS", {
      message,
      lastSync: extra && extra.lastSync ? extra.lastSync : new Date().toISOString(),
      ...extra,
    });
  },

  refreshSessionCalendar() {
    const session = sessionExpiry.readSession(this.path);
    if (session.expiresMs) {
      const written = sessionExpiry.writeCalendar(this.path, session.expiresMs);
      if (written.updated) {
        console.log("MMM-iCloudPhotos session calendar updated", new Date(session.expiresMs).toISOString());
      }
    }
    return session;
  },

  runSync() {
    if (this.running) {
      return;
    }
    const session = this.refreshSessionCalendar();
    if (session.expiresMs && Date.now() >= session.expiresMs) {
      if (this.pausedSignature && this.pausedSignature !== session.signature) {
        console.log("MMM-iCloudPhotos cookie file changed, but the session is still expired");
      }
      this.pausedSignature = session.signature;
      this.setStatus("iCloud session expired. Sync paused until a new cookie file is written.");
      return;
    }
    if (this.pausedSignature && this.pausedSignature !== session.signature) {
      console.log("MMM-iCloudPhotos cookie file replaced. Resuming sync.");
    }
    this.pausedSignature = null;
    const python = this.pythonBin();
    if (!fs.existsSync(python)) {
      this.setStatus("Run scripts/install.sh in MMM-iCloudPhotos first.");
      return;
    }
    const chosen = albumSchedule.readSchedule(
      albumSchedule.schedulePath(this.path, this.config),
      new Date()
    );
    let album = this.config.album;
    if (chosen.found && chosen.error) {
      this.setStatus(`${chosen.error}. Leaving the current photos in place.`);
      console.error("MMM-iCloudPhotos", chosen.error);
      return;
    }
    if (chosen.syncAlbum) {
      album = chosen.syncAlbum;
      console.log("MMM-iCloudPhotos album schedule", chosen.album);
    }
    if (!album) {
      this.setStatus("Set config.album in config.js or add config/album-schedule.json");
      return;
    }

    this.running = true;
    this.setStatus(`Syncing “${album}”…`);
    const args = [
      path.join(this.path, "python", "sync_album.py"),
      "--album",
      album,
      "--output",
      this.outputDir(),
    ];
    const child = spawn(python, args, {
      cwd: this.path,
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("error", (err) => {
      console.error("MMM-iCloudPhotos sync spawn error:", err && err.message);
    });
    child.on("close", (code) => {
      this.running = false;
      const line = stdout
        .split("\n")
        .reverse()
        .find((row) => row.startsWith("SYNC_OK"));
      if (code === 0 && line) {
        console.log("MMM-iCloudPhotos", line);
        this.setStatus(`Synced ${album}`, { lastSync: new Date().toISOString(), detail: line });
        return;
      }
      const combined = `${stdout}\n${stderr}`;
      if (/Could not find album/i.test(combined)) {
        this.setStatus(`Album “${album}” was not found. Leaving the current photos in place.`);
        console.error("MMM-iCloudPhotos album was not found. Photos were left in place.");
        return;
      }
      const err = (stderr || stdout).trim().split("\n").slice(-4).join(" ").slice(0, 280);
      this.setStatus(err || `Sync failed (exit ${code})`);
      console.error("MMM-iCloudPhotos sync failed:", err || stdout || stderr);
    });
  },
});
