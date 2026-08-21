# MMM-iCloudPhotos

A [MagicMirror²](https://github.com/MagicMirrorOrg/MagicMirror) companion module that does a **one-way sync** of an iCloud Photos album onto the Pi:

- originals only (no crop, resize, or orientation filter)
- adds new photos
- deletes local files that were removed from the album

It writes into [`MMM-ImagesPhotos`](https://github.com/sdetweil/MMM-ImagesPhotos) `uploads/` by default, so that module can keep displaying the slideshow.

Do **not** put your Apple password in `config.js`.

## Requirements

- Raspberry Pi (or other Linux box) with MagicMirror²
- Python 3.10+
- [MMM-ImagesPhotos](https://github.com/sdetweil/MMM-ImagesPhotos) if you want the photos on the mirror
- Your **Apple ID password** (not an app-specific password)
- Ability to complete 2FA once in a terminal

Chromium may not display HEIC. Prefer JPEG/PNG in the iCloud album, or convert separately.

## Installation

```bash
cd ~/MagicMirror/modules
git clone https://github.com/msimon360/MMM-iCloudPhotos
cd MMM-iCloudPhotos
bash scripts/install.sh
```

Also install the slideshow module if you do not already have it:

```bash
cd ~/MagicMirror/modules
git clone https://github.com/sdetweil/MMM-ImagesPhotos
cd MMM-ImagesPhotos
npm install
```

## First-time iCloud login (required)

1. Edit `.env` (created from `.env.example`):

   ```
   ICLOUD_USER=you@example.com
   ICLOUD_PASSWORD=your-apple-id-password
   ```

2. Complete 2FA in a real terminal. Use the **6-digit code on your iPhone/iPad/Mac**, not an SMS:

   ```bash
   cd ~/MagicMirror/modules/MMM-iCloudPhotos
   ./scripts/sync-once.sh --album DigiFrame --list
   ```

   `--list` prints album names. Then sync once:

   ```bash
   ./scripts/sync-once.sh --album DigiFrame --output ../MMM-ImagesPhotos/uploads
   ```

   After this, a trusted session is stored under `tmp/pyicloud/` so MagicMirror can sync without a prompt.

## Config

Add **both** modules to `config/config.js`:

```js
{
  module: "MMM-iCloudPhotos",
  // omit position, or set showStatus: true to see last sync time
  config: {
    album: "DigiFrame",
    outputDir: "modules/MMM-ImagesPhotos/uploads",
    syncInterval: 6 * 60 * 60 * 1000, // 6 hours
    runOnStart: true,
    showStatus: false
  }
},
{
  module: "MMM-ImagesPhotos",
  position: "bottom_center",
  config: {
    opacity: 0.9,
    animationSpeed: 500,
    updateInterval: 15000,
    sequential: false,
    maxHeight: "850px",
    maxWidth: "1000px"
  }
}
```

Restart MagicMirror (`pm2 restart mm` or your usual command).

## Configuration

| Option | Default | Description |
|---|---|---|
| `album` | `"DigiFrame"` | iCloud album name (must match exactly) |
| `outputDir` | `modules/MMM-ImagesPhotos/uploads` | Destination folder. Absolute, or relative to the MagicMirror root |
| `syncInterval` | `21600000` | Milliseconds between syncs |
| `runOnStart` | `true` | Sync when MagicMirror starts |
| `showStatus` | `false` | Show last sync status on the mirror |

## Update

```bash
cd ~/MagicMirror/modules/MMM-iCloudPhotos
git pull
./venv/bin/pip install -r requirements.txt
```

## How it works

`python/sync_album.py` uses [pyicloud](https://pypi.org/project/pyicloud/) 2.6+ (SRP login). It keeps a `.icloud-sync.json` manifest in the output folder and only deletes files this module previously downloaded.

The MagicMirror `node_helper` runs that script on a timer. It cannot complete 2FA by itself, which is why the first `sync-once.sh` run is required.

## Troubleshooting

`Session file does not exist` is **normal on the first run**. It is an INFO log from pyicloud, not a failed login. Wait for the 2FA prompt (or album list). After a successful login, `tmp/pyicloud/` is created and later runs stay quiet.

## Security

- Keep `.env` off git and off backups you share
- Use your main Apple ID password; app-specific passwords do not work with this login
- Session cookies live in `tmp/pyicloud/` — do not publish that folder
