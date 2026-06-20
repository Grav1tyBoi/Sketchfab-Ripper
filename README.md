<div align="center">
    
# Sketchfab Asset Downloader

**A sleek desktop tool to download 3D models, textures, and animations from Sketchfab — with full material reconstruction.**

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.6%2B-green?logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078D6?logo=windows&logoColor=white)](https://microsoft.com/windows)
[![License](https://img.shields.io/badge/License-Private-red)]()

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🎯 Smart Download
- Paste any public model URL and go
- Fetches thumbnails instantly as you type
- Handles both **new (binz)** and **legacy (osgjs.gz)** formats
- Downloads are decrypted and converted automatically

</td>
<td width="50%">

### 🎨 Full Material Pipeline
- Extracts all texture channels (PBR-ready)
- Generates a **.blend** file with reconstructed shading
- Exports clean **.gltf** and optional **.fbx**
- Preserves normal maps, roughness, metallic & more

</td>
</tr>
<tr>
<td width="50%">

### 📋 Queue System
- Add multiple downloads to a visual queue
- Live progress bars and status pills
- Cancel individual items or the whole batch
- Load from **.json** or **.txt** link files

</td>
<td width="50%">

### 👤 User List Scraper
- Enter any Sketchfab profile URL
- Fetches **all public models** across pages
- Saves as a reusable list for batch downloading
- Shows model count per saved list

</td>
</tr>
</table>

---
<br>
<div align="center">
<img src="https://i.imgur.com/Bmygwga.png">
</div>

---

## 📁 Project Structure

```
sketchfab-downloader/
├── SF_Ripper.py                  # Entry point & full GUI application
├── blender_shading.py       # Blender script for material reconstruction
├── config.ini               # Persistent user settings
├── tools/
│   ├── binz/
│   │   ├── binzDecrypt.exe  # Decrypts new-format .binz files
│   │   └── binzOsg.exe      # Converts binz → osgjs
│   ├── OsgConv/
│   │   └── osgconv.exe      # osgjs → glTF / FBX conversion
│   └── TexDe/
│       └── texde.py         # Texture extraction engine
├── downloads/               # Default output directory
│   └── <model-name>/
│       ├── <model>.gltf
│       ├── <model>.fbx
│       ├── <model>.blend
│       ├── textures/
│       ├── animations/
│       └── thumbnail.jpg
└── links/                   # Saved user model lists
    └── <username>.json
```

---

## 🚀 Getting Started

### Prerequisites

| Dependency | Purpose | Install |
|---|---|---|
| **Python 3.10+** | Runtime | [python.org](https://python.org) |
| **Blender** *(optional)* | .blend export & shading | [blender.org](https://blender.org) |
| **pip packages** | GUI & utilities | See below |

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Configure

1. **Run the app once** — it generates `config.ini` automatically
2. Go to **Settings** → set your **Blender folder** path (e.g. `C:\Program Files\Blender Foundation\Blender 4.0`)
3. Optionally set a custom download folder

### Run

```bash
py SF_Ripper.py
```
---

## 📖 Usage

### Single Model

1. Go to **Download**
2. Paste a Sketchfab URL like `https://sketchfab.com/3d-models/some-model-abcdef123`
3. Thumbnail previews automatically
4. Click **Add to Queue**

### Batch from File

1. Set the source dropdown to **Links File (.json / .txt)**
2. Pick a file containing one URL per line (`.txt`) or a JSON array (`.json`)
3. Click **Add to Queue**

### Batch from User Profile

1. Go to **User Lists**
2. Paste `https://sketchfab.com/<username>`
3. Click **Create List** — all their public models are saved
4. Back on **Download**, switch source to **User List** and select it

### Queue Management

| Status | Meaning |
|---|---|
| <span style="background:#e5e5e7;color:#6e6e73;padding:2px 10px;border-radius:9px;font-size:12px;font-weight:500;">Queued</span> | Waiting to start |
| <span style="background:#cfe5ff;color:#0066d6;padding:2px 10px;border-radius:9px;font-size:12px;font-weight:500;">Running</span> | Currently downloading |
| <span style="background:#d4f3dd;color:#1d8338;padding:2px 10px;border-radius:9px;font-size:12px;font-weight:500;">Done</span> | Completed successfully |
| <span style="background:#ffe1de;color:#c8281f;padding:2px 10px;border-radius:9px;font-size:12px;font-weight:500;">Failed</span> | Errored — check `error.log` |

---

## ⚙️ Settings Reference

| Setting | Default | Description |
|---|---|---|
| **Blender folder** | *empty* | Path to your Blender installation (enables `.blend` output) |
| **Download folder** | `./downloads` | Custom output root. Leave empty for default |
| **FBX Export** | ✅ On | Also export `.fbx` alongside `.gltf` |
| **Thumbnail Download** | ✅ On | Save `thumbnail.jpg` with each model |
| **Quads Recreation** | ❌ Off | Recreate quads in Blender if model is >75% quads |

Settings are persisted in `config.ini` and survive restarts.

---

## ⚠️ Important Notes

- Sketchfab's API may change; texture extraction logic may need updates
- Some models use complex shader setups that can't be perfectly replicated
- Check `error.log` in the app directory if a download fails

---

<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=80&section=header" width="100%"/>

</div>
