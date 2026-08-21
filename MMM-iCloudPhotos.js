Module.register("MMM-iCloudPhotos", {
  defaults: {
    album: "DigiFrame",
    outputDir: null,
    syncInterval: 6 * 60 * 60 * 1000,
    showStatus: false,
    runOnStart: true,
  },

  start() {
    this.status = {
      lastSync: null,
      message: "Waiting for first sync…",
    };
    this.sendSocketNotification("ICLOUD_PHOTOS_CONFIG", this.config);
  },

  socketNotificationReceived(notification, payload) {
    if (notification !== "ICLOUD_PHOTOS_STATUS") {
      return;
    }
    this.status = payload;
    this.updateDom(250);
  },

  getStyles() {
    return ["MMM-iCloudPhotos.css"];
  },

  getDom() {
    const wrapper = document.createElement("div");
    wrapper.className = "mmm-icloud-photos";
    if (!this.config.showStatus) {
      wrapper.classList.add("hidden");
      return wrapper;
    }
    wrapper.innerText = this.status.message || "";
    if (this.status.lastSync) {
      const when = document.createElement("div");
      when.className = "dimmed small";
      when.innerText = this.status.lastSync;
      wrapper.appendChild(when);
    }
    return wrapper;
  },
});
