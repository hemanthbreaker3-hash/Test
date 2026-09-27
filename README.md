<p align="center">
   <img src="docs/w-icon.svg" alt="HTR-X logo" width="160">
</p>

<h1 align="center">HTR-X</h1>

<p align="center">
   Telegram mirroring and leeching platform with a container-based runtime, a lightweight web UI, and a highly configurable transfer pipeline.
</p>

<p align="center">
   <a href="https://github.com/SilentDemonSD/WZML-X">
      <img src="https://img.shields.io/github/stars/SilentDemonSD/WZML-X?style=for-the-badge&logo=github&label=Stars" alt="Stars">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/search?l=python">
      <img src="https://img.shields.io/github/languages/top/SilentDemonSD/WZML-X?style=for-the-badge&logo=python&label=Python" alt="Python">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/blob/main/docker-compose.yml">
      <img src="https://img.shields.io/badge/Docker-Compose-2496ED?style=for-the-badge&logo=docker&logoColor=white" alt="Docker Compose">
   </a>

   <a href="https://t.me/WZML_X">
      <img src="https://img.shields.io/badge/Telegram-Community-26A5E4?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/blob/main/LICENSE">
      <img src="https://img.shields.io/github/license/SilentDemonSD/WZML-X?style=for-the-badge&label=License" alt="License">
   </a>

   <a href="https://github.com/SilentDemonSD/WZML-X/commits/main">
      <img src="https://img.shields.io/github/last-commit/SilentDemonSD/WZML-X?style=for-the-badge&label=Last%20Commit" alt="Last Commit">
   </a>
</p>

## Index

<details open>
   <summary>Table of Contents <kbd>Click Here</kbd></summary>

   - [At a Glance](#at-a-glance)
   - [Why Use It](#why-use-it)
   - [What It Covers](#what-it-covers)
   - [How It Runs](#how-it-runs)
   - [Deployment](#deployment)
   - [Configuration](#configuration)
   - [Project Layout](#project-layout)
   - [Documentation](#documentation)
   - [Support](#support)
   - [Credits](#credits)
   - [License](#license)
</details>

## At a Glance

| Area | Details |
|---|---|
| Runtime | Python Telegram bot + web UI |
| Deployment | Docker & Docker Compose or Systemd Service |
| Required config | `BOT_TOKEN`, `TELEGRAM_API`, `TELEGRAM_HASH`, `OWNER_ID`, `DATABASE_URL` |
| License | [LICENSE](LICENSE) |

## Why Use It

HTR-X is built for users who want a single bot stack that can mirror, leech, manage files, and expose a simple web-based selection flow without stitching together multiple tools. The README focuses on what you need to deploy it quickly, understand the moving parts, and tune the behavior safely.

## What It Covers

| Capability | Outcome |
|---|---|
| Mirroring | Send files to Telegram with a controllable pipeline |
| Leeching | Deliver files in the format you prefer, including document and media workflows |
| Advanced Merge Planner | Interactively reorder files, edit output filenames, and configure merge parameters before uploading |
| Pre-Upload Video Tools (`-ht`) | Trim media, extract video/audio/subtitles, swap tracks, and toggle merge mode on demand |
| File selection UI | Review and select torrent / NZB / upload contents before finalizing |
| Multi-source downloads | Use qBittorrent, Aria2, JDownloader, Mega, NZB, and yt-dlp integrations |
| Storage and upload paths | Push content to Google Drive, Rclone, Mega, and other supported routes |
| Automation | Limit tasks, tune queues, and manage startup updates from one config layer |

## How It Runs

Deploy with Docker or Systemd and provide the required configuration values. The container takes care of the runtime path, so users only need to build or start the image and set their settings.

<details>
   <summary>What you need <kbd>Click Here</kbd></summary>

   - Docker installed or a Linux VPS with Python 3.10+
   - Your Telegram bot token and Telegram API credentials
   - A MongoDB connection string
   - The optional service credentials you want to enable, such as Drive, Rclone, Mega, JDownloader, or SABnzbd
</details>

## Deployment

<details open>
   <summary>VPS Deployment via deploy.vps (One-Command Setup)</summary>

   Deploying on a VPS is streamlined with the automated `deploy.vps` script:

   1. **Connect to your VPS:**
      ```bash
      ssh root@your_vps_ip
      ```

   2. **Clone the repository:**
      ```bash
      git clone https://github.com/SilentDemonSD/WZML-X.git
      ```

   3. **Enter the project directory:**
      ```bash
      cd WZML-X
      ```

   4. **Give execute permission to `deploy.vps`:**
      ```bash
      chmod +x deploy.vps
      ```

   5. **Run `deploy.vps`:**
      ```bash
      ./deploy.vps
      ```

   6. **What the script installs and configures:**
      - System dependencies (`python3`, `pip`, `venv`, `ffmpeg`, `7z`, `aria2`, `rclone`, `qbittorrent-nox`, `git`, `curl`, `wget`, `lsof`, `procps`).
      - Sets up a Python virtual environment (`venv`) and installs project dependencies from `requirements.txt`.
      - Prepares required runtime directories (`downloads`, `thumbnails`, `tokens`, `rclone`, `cookies`, `Images`).
      - Configures and enables a systemd service (`htr_bot.service`) so the bot runs continuously.
      - Uses existing repository configuration without prompting to edit `config.py`.

   7. **Check if the bot is running:**
      ```bash
      systemctl status htr_bot
      ```

   8. **View logs:**
      ```bash
      journalctl -u htr_bot -f
      ```

   9. **Restart the bot:**
      ```bash
      systemctl restart htr_bot
      ```

   10. **Stop the bot:**
       ```bash
       systemctl stop htr_bot
       ```

   11. **Update and redeploy the project:**
       ```bash
       git pull
       ./deploy.vps
       ```

   12. **System Requirements:**
       - OS: Ubuntu 20.04/22.04 or Debian 11/12 recommended (Linux with `systemd`).
       - Privileges: `root` or `sudo` user.
       - Recommended Spec: Minimum 1 GB RAM (2 GB+ recommended for heavy FFmpeg operations).
</details>

<details>
   <summary>Docker & Docker Compose Deployment</summary>

   ```bash
   git clone https://github.com/SilentDemonSD/WZML-X.git
   cd WZML-X
   cp config_sample.py config.py
   # Edit config.py with your values if needed
   docker buildx compose up -d
   ```

   The bot runs behind a Cloudflare quick tunnel by default. Check the tunnel URL:

   ```bash
   docker compose logs tunnel
   ```

   You'll see a `https://*.trycloudflare.com` URL — that's your bot's web UI.

   To stop:

   ```bash
   docker buildx compose down
   ```
</details>

<details>
   <summary>Single Container (Manual)</summary>

   ```bash
   git clone https://github.com/SilentDemonSD/WZML-X.git
   cd WZML-X
   docker build -t htrx .
   docker run -p 8080:8080 htrx
   ```
</details>

## Configuration

Start with the required values:

- `BOT_TOKEN`
- `TELEGRAM_API`
- `TELEGRAM_HASH`
- `OWNER_ID`
- `DATABASE_URL`

Then tune the optional behavior from `config_sample.py`.

<details>
   <summary>Important user-facing settings</summary>

   | Setting | User impact |
   |---|---|
   | `DEFAULT_LANG` | Bot language |
   | `STATUS_LIMIT` | How much status data is shown |
   | `DEFAULT_UPLOAD` | Default upload target |
   | `LEECH_SPLIT_SIZE` | How large leech outputs are split |
   | `QUEUE_ALL`, `QUEUE_DOWNLOAD`, `QUEUE_UPLOAD` | Queue pressure and concurrency |
   | `SHOW_CLOUD_LINK` | Whether cloud links are shown to users |
   | `WEB_PINCODE` | Protects web access to file selection |
</details>

## Project Layout

| Path | Purpose |
|---|---|
| `bot/` | Bot core, handlers, listeners, and modules |
| `web/` | FastAPI app, templates, and the file selector UI |
| `gen_scripts/` | Setup helpers for sessions, tokens, and drive configuration |
| `plugins/` | Optional bot plugins |
| `qBittorrent/` | Default qBittorrent configuration |
| `sabnzbd/` | Default SABnzbd configuration |

## Credits

HTR-X is a fork of [mirror-leech-telegram-bot](https://github.com/anasty17/mirror-leech-telegram-bot). The base project belongs to [anasty17](https://github.com/anasty17) and upstream contributors.

## License

This project is distributed under the terms of the repository license. See [LICENSE](LICENSE) for the full text.
