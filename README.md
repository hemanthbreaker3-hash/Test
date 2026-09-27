# 🚀 HTR - Advanced Telegram Mirror, Leech & Media Management Bot

<p align="center">
  <b>High-performance, feature-packed Telegram Mirror & Leech Bot with Advanced Merge Planner, Video Tools, FFmpeg Processing, and Multi-Cloud Upload Support.</b>
</p>

---

## 🌟 Overview

**HTR** (formerly WZML-X) is an all-in-one automation platform designed for high-speed file downloading, merging, media editing, and uploading across Telegram and cloud storage platforms. Built with Python, Pyrogram, and FFmpeg, HTR provides a seamless web-based selection flow and rich interactive Telegram UI controls.

---

## 🔥 Key Features

- **🚀 Multi-Engine Downloads:** Direct HTTP/HTTPS, Aria2, qBittorrent, JDownloader, SABnzbd (NZB), Mega, Seedr Cloud, AllDebrid, and Telegram links.
- **🎬 Advanced Merge Planner:** Interactive Telegram & Web UI order planner for video/audio/subtitle stream merging and custom output naming.
- **✂️ Video Tools & Pre-Processing:** Trimming, track extraction, stream reordering, encoding, compression, and custom FFmpeg preset filters (`-ht` flag supported).
- **📦 Flexible Range Links:** Seamless sequential downloading and processing for multi-item Telegram range links (20+ files/videos).
- **☁️ Multi-Cloud Destination:** Upload to Telegram, Google Drive, Rclone Remotes, Mega, GoFile, BuzzHeavier, PixelDrain, and more.
- **💎 Premium Telegram UI:** Styled buttons with automatic success/danger indicators, rich emojis, and clean English interface.

---

## 🛠️ Quick Deployment

### VPS One-Command Deployment

```bash
git clone https://github.com/SilentDemonSD/WZML-X.git htr_bot
cd htr_bot
chmod +x deploy.vps
./deploy.vps
```

### Docker & Docker Compose

```bash
git clone https://github.com/SilentDemonSD/WZML-X.git htr_bot
cd htr_bot
cp config_sample.py config.py
docker buildx compose up -d
```

---

## ⚙️ Configuration Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | Yes | Telegram Bot Token from `@BotFather` |
| `TELEGRAM_API` | Yes | Telegram API ID |
| `TELEGRAM_HASH` | Yes | Telegram API Hash |
| `OWNER_ID` | Yes | Bot Owner's Telegram User ID |
| `DATABASE_URL` | Yes | MongoDB Connection String |
| `BASE_URL` | Optional | Public HTTPS URL for Web App features |

---

## 🤝 Community & Support

- **Updates Channel:** [HTR Updates](https://t.me/WZMLX_Updates)
- **Support Group:** [HTR Support Group](https://t.me/WZMLX_Support)

---

## 📜 License

Distributed under the terms of the project license. See `LICENSE` for details.
