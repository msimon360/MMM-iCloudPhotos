const { spawn } = require("child_process");
const fs = require("fs");
const path = require("path");
const NodeHelper = require("node_helper");

module.exports = NodeHelper.create({
  start() {
    this.config = null;
    this.timer = null;
    this.running = false;
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

  runSync() {
    if (this.running) {
      return;
    }
    const python = this.pythonBin();
    if (!fs.existsSync(python)) {
      this.setStatus("Run scripts/install.sh in MMM-iCloudPhotos first.");
      return;
    }
    const album = this.config.album;
    if (!album) {
      this.setStatus("Set config.album in config.js");
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
      env: process.env,
    });

    let stdout = "";
    let stderr = "";
    child.stdout.on("data", (chunk) => {
      stdout += chunk.toString();
    });
    child.stderr.on("data", (chunk) => {
      stderr += chunk.toString();
    });
    child.on("close", (code) => {
      this.running = false;
      const line = stdout
        .split("\n")
        .reverse()
        .find((row) => row.startsWith("SYNC_OK"));
      if (code === 0 && line) {
        this.setStatus(`Synced ${album}`, { lastSync: new Date().toISOString(), detail: line });
        return;
      }
      const err = (stderr || stdout).trim().split("\n").slice(-4).join(" ").slice(0, 280);
      this.setStatus(err || `Sync failed (exit ${code})`);
      console.error("MMM-iCloudPhotos sync failed:", err || stdout || stderr);
    });
  },
});
