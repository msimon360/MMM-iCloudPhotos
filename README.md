# MMM-iCloudPhotos

A [MagicMirror²](https://github.com/MagicMirrorOrg/MagicMirror) companion module that does a **one-way sync** of an iCloud Photos album onto your device:

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
- Ability to complete 2FA in a terminal ( **NOTE:** session will expire in aproximently 2 months. See Session expiry below. )

Chromium may not display HEIC. Prefer JPEG/PNG in a personal album, or convert separately. Classic Shared Albums are usually delivered as JPEG. Look for an options button on the shared album and set format to most compatable.

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
    outputDir: "modules/MMM-ImagesPhotos/uploads",  // or similar path for your Photo module
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

## Multiple people can add photos

Use a **classic iCloud Shared Album** so anyone you authorize can add photos from any Apple device. The module still signs in as **one** Apple ID (yours is fine). The other people do not need credentials on your device.

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
| `album` | `"YourAlbum"` | Album used when `config/album-schedule.json` is not present. A personal album with that name is used if it exists; otherwise a Shared Album. Use `shared:NAME` if both exist. |
| `scheduleFile` | `config/album-schedule.json` | Schedule of personal-album names and the month and day each one starts. Relative paths are from the MagicMirror root. When this file exists, it chooses the album instead of `album`. |
| `outputDir` | `modules/MMM-ImagesPhotos/uploads` | Destination folder. Absolute, or relative to the MagicMirror root. This is the folder MMM-ImagesPhotos already displays. |
| `syncInterval` | `21600000` | Milliseconds between syncs |
| `runOnStart` | `true` | Sync when MagicMirror starts |
| `showStatus` | `false` | Show last sync status on the mirror |

## Update

```bash
cd ~/MagicMirror/modules/MMM-iCloudPhotos
git pull
./venv/bin/pip install -r requirements.txt
cd ~/MagicMirror/modules/MMM-ImagesPhotos
git pull
```

## How it works

`python/sync_album.py` uses [pyicloud](https://pypi.org/project/pyicloud/) 2.6+ (SRP login). It keeps a `.icloud-sync.json` manifest in the output folder and only deletes files this module previously downloaded.

The MagicMirror `node_helper` runs that script on a timer. It cannot complete 2FA by itself, which is why the first `sync-once.sh` run is required. After a successful sync it sends `MMM_IMAGESPHOTOS_REFRESH` so [MMM-ImagesPhotos](https://github.com/msimon360/MMM-ImagesPhotos) reloads the folder without a MagicMirror restart.

## Album schedule

On each sync interval the helper reads `config/album-schedule.json` (two directories above this module, the MagicMirror config directory in a normal install). That file is outside this git repo, so later edits are not replaced by `git pull`. `album-schedule.example.json` in this repo is a copy of the same shape. Copy it to `~/MagicMirror/config/album-schedule.json` and edit the copy.

The schedule repeats every year. Each entry is a personal-album name plus the month and day it starts. The active album is the one whose start date is today, or the most recent start date before today. Before the first start date in the year, the last start date from the previous year stays active. `"library": "personal"` asks only the personal library. A plain name is personal too. The sync does not add `shared:`. A name that already starts with `shared:` is still a Shared Album.

```json
{
  "repeat": "yearly",
  "library": "personal",
  "albums": [
    { "album": "Spring", "month": 3, "day": 20 },
    { "album": "Summer", "month": 6, "day": 21 },
    { "album": "Fall", "month": 9, "day": 22 },
    { "album": "Winter", "month": 12, "day": 21 }
  ]
}
```

Photos are written to `outputDir`, which should be the folder MMM-ImagesPhotos already shows. MMM-ImagesPhotos does not need its own album setting. After a successful sync it reloads that folder without a MagicMirror restart. When the active album changes, files this module previously downloaded are removed and replaced with the new album. If that personal album does not exist, or it exists but has no photos, the sync stops before deleting anything and the photos already in the folder stay on screen. A Shared Album with the same name is not used in its place. A broken schedule file also leaves those photos in place. The cookie-expiry pause still runs first: once the session cookie has expired, the helper does not sync, even if the schedule names a current album.

## Session expiry

Before each sync, `node_helper.js` asks `sessionExpiry.js` to read the trusted session in `tmp/pyicloud/`. It uses a live `*.cookiejar` whose name does not start with `BAK` or `youexample`. The date is the `expires` value of the `X-APPLE-WEBAUTH-HSA-TRUST` cookie. If that cookie is missing, it uses the latest `expires` in that jar. When more than one live jar has a date, it keeps the latest of those dates.

When a date is found, the module writes `config/icloud-session-expires.ics` (two directories above this module, which is the MagicMirror config directory in a normal install). The event title is exactly `iCloud Session Expires`. The event starts at the expiration instant in UTC and lasts one hour. The file is rewritten only when that date changes. There is no config option for the path or the title. This module does not edit `config.js`. To show the event on the mirror, add that file to the calendar module yourself.

If that expiration has been reached, the helper does not start a sync. The status line is `iCloud session expired. Sync paused until a new cookie file is written.` The timer keeps running and reads the cookiejar again each interval. Sync starts again when the cookie file is replaced or rewritten and the new expiration is still in the future. A rewrite that is still expired stays paused. Cookies are not deleted. If there is no dated cookie yet, no calendar file is written and this check does not block sync.

## Troubleshooting

`Session file does not exist` is **normal on the first run**. It is an INFO log from pyicloud, not a failed login. Wait for the 2FA prompt (or album list). After a successful login, `tmp/pyicloud/` is created and later runs stay quiet.

If Apple returns **account locked** / `-20209`, stop syncing. pyicloud often wraps that as `Invalid email/password combination` even when the password is right. Unlock at [iForgot](https://iforgot.apple.com) or [appleid.apple.com](https://appleid.apple.com), confirm iCloud works in a browser, update `.env` if you reset the password, delete `tmp/pyicloud/`, then retry **once**. Deleting that folder is only for this recovery. The session-expiry check never deletes cookies.

## Security

- Keep `.env` off git and off backups you share
- Use your main Apple ID password; app-specific passwords do not work with this login
- Session cookies live in `tmp/pyicloud/` — do not publish that folder
