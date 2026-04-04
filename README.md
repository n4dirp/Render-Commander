# Render Commander

[![GitHub Release](https://img.shields.io/github/v/release/n4dirp/Render-Commander?style=flat-square)](https://github.com/n4dirp/Render-Commander/releases)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux-lightgrey?style=flat-square)](https://github.com/n4dirp/Render-Commander)
[![Blender Version](https://img.shields.io/badge/Blender-4.2%20--%205.1-orange?style=flat-square&logo=blender)](https://www.blender.org/)

Render Commander is a Blender add-on designed for automated, parallel rendering. It allows you to configure, launch, and export command-line render jobs, manage multi-GPU workloads, and generate standalone scripts. The add-on also supports external .blend files and enables batch execution through presets and customizable overrides.

<img src="images/render_launcher.png" alt="Render-Commander Panel" width="300">

## Features

### Multi-Process and Device-Parallel Rendering

**Cycles**: Automates device configuration and launches separate render instances for each enabled GPU devices. Render Commander support multiple frame-allocation strategies and can render across different backends simultaneously.

**EEVEE**: Improve animation rendering times by running multiple parallel render jobs.


### Render Overrides & Presets

Tweak resolution, samples, output paths, and more without altering your original saved settings. Create, apply and reuse render presets for different project stages (draft, final, etc.).

### External Blend Files

Save system memory by rendering scenes stored in external `.blend` files without opening them in Blender.
Preview they settings, apply overrides, and start custom renders directly from the add-on panel.

### Advanced Options

- **Custom Blender Executables** – Define custom Blender paths to use different versions or builds.

- **Append Python Scripts** – Attach your own Python scripts to render jobs for logging, post-processing, or pipeline integration.

- **Desktop Notifications** – Get notified when a render job finishes.

- **System Power Control** – Automatically put the system to sleep or shut it down once all jobs are complete.

## System Requirements

The add-on is compatible with **Blender 4.2+** and newer versions and creates compatible render scripts for Windows and GNU/Linux systems.

## Installation

1. Download the latest release from the [Releases](https://github.com/n4dirp/render-commander/releases) page.
2. Drag and drop the `.zip` into Blender to install the add-on.

## Location
- The main add-on panel is available in the *Render Commander* tab in the viewport sidebar.
- Additional controls are available in the *Render* menu on the topbar.

## Build from Source

```bash
git clone https://github.com/n4dirp/Render-Commander.git
cd Render-Commander/render_commander
blender --command extension build
```
