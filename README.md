# MMM-iCloudPhotos

A [MagicMirror²](https://github.com/MagicMirrorOrg/MagicMirror) companion module that does a **one-way sync** of an iCloud Photos album onto the Pi:

- originals only (no crop, resize, or orientation filter)
- adds new photos
- deletes local files that were removed from the album

It writes into [`MMM-ImagesPhotos`](https://github.com/sdetweil/MMM-ImagesPhotos) `uploads/` by default, so that module can display the slideshow.

Do **not** put your Apple password in `config.js`.

## Requirements

- Raspberry Pi (or other Linux box) with MagicMirror²
- Python 3.10+
- [MMM-ImagesPhotos](https://github.com/sdetweil/MMM-ImagesPhotos) or another photo module to display the images
- Your **Apple ID password** (not an app-specific password)
- Ability to complete 2FA once in a terminal

Chromium may not display HEIC. Prefer JPEG/PNG in a personal album, or convert separately. Classic Shared Albums are usually delivered as JPEG.

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

1. Edit **this module’s** `.env` (created from `.env.example`) in the MMM-iCloudPhotos directory. It is **not** `~/.env`:

   ```
   ~/MagicMirror/modules/MMM-iCloudPhotos/.env
   ```

   ```
   ICLOUD_USER=you@example.com
   ICLOUD_PASSWORD=your-apple-id-password
   ```

2. Complete 2FA in a real terminal. Use the **6-digit code on your iPhone/iPad/Mac**, not an SMS:

   ```bash
   cd ~/MagicMirror/modules/MMM-iCloudPhotos
   ./scripts/sync-once.sh --album YourAlbum --list
   ```

   `--list` prints personal albums and Shared Albums. Then sync once:

   ```bash
   ./scripts/sync-once.sh --album YourAlbum --output ../MMM-ImagesPhotos/uploads
   ```

   After this, a trusted session is stored under `tmp/pyicloud/` so MagicMirror can sync without a prompt.

## Config

Add **both** modules to `config/config.js`:

```js
{
  module: "MMM-iCloudPhotos",
  // omit position, or set showStatus: true to see last sync time
  config: {
    album: "YourAlbum",
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

## Both of you adding photos

Use a **classic iCloud Shared Album** so either of you can add photos from any Apple device. The Pi still signs in as **one** Apple ID (yours is fine). The other person does not need credentials on the Pi.

This is **not** the newer iOS 16+ **Shared Photo Library** (the family “one library” feature). That library cannot be listed as a named album here. If you already use Shared Photo Library, copy photos into a classic Shared Album or into a personal-library album instead.

1. On an iPhone: Settings → [your name] → iCloud → Photos → turn on **Shared Albums** (not Shared Library).
2. Photos → Albums → Shared Albums → New Shared Album (for example `YourAlbum`).
3. Invite the other person’s Apple ID. Enable **Subscribers Can Post**.
4. They accept the invite. Either of you can then add photos from any signed-in iPhone, iPad, or Mac.
5. On the Pi, confirm the name:

   ```bash
   ./scripts/sync-once.sh --list
   ```

   The album should appear under **Shared Albums**.
6. Set `config.album` to that exact name. Use `shared:YourAlbum` only if a personal album has the same name.

Apple compresses Shared Album photos (not full originals) and typically delivers JPEG, which Chromium on the Pi can display. That is fine for a slideshow; it is not a backup of the library.

## Configuration

| Option | Default | Description |
|---|---|---|
| `album` | `"YourAlbum"` | Album name (must match exactly). A personal album with that name is used if it exists; otherwise a Shared Album. Use `shared:NAME` if both exist. |
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

If Apple returns **account locked** / `-20209`, stop syncing. pyicloud often wraps that as `Invalid email/password combination` even when the password is right. Unlock at [iForgot](https://iforgot.apple.com) or [appleid.apple.com](https://appleid.apple.com), confirm iCloud works in a browser, update `.env` if you reset the password, delete `tmp/pyicloud/`, then retry **once**.

## Security

- Keep `.env` off git and off backups you share
- Use your main Apple ID password; app-specific passwords do not work with this login
- Session cookies live in `tmp/pyicloud/` — do not publish that folder
