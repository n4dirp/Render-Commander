# Render Commander — Blender Add-on

> *Take full control of background rendering without leaving Blender.*

Run **stills**, **animations**, or **frame lists** in the background while you keep working.<br>
Designed for artists and studios working on multi-GPU systems.

<img src="images/render_launcher.png" alt="Render-Commander Panel" width="350">

---

## Features

### Faster Renders with Device-Parallel Rendering

Launch multiple background render processes, each assigned to a specific GPU. Cut animation render times dramatically by leveraging all available devices simultaneously.

<img src="images/parallel_render_benchmark.jpg" alt="Device-Parallel Benchmark">
<img src="images/device_parallel.png" alt="Device-Parallel" width="300">

### Render Presets & Overrides

Tweak resolution, samples, output paths, and more—without altering your original scene. Save and reuse presets for different project stages (draft, final, client review, etc.).
  
<img src="images/override_settings.png" alt="Render Overrides" width="300">
<img src="images/path_templates.png" alt="Output Path Templates" width="300">

### External Scene Support

Render scenes stored in external `.blend` files without opening them in Blender.
Preview scene settings, apply overrides, and start renders directly from the add-on panel.
  
<img src="images/external_scene.png" alt="External Scene" width="300">

### Advanced Customization

- Desktop notifications alert you when a render job finishes.
- Prevents system sleep during renders.
- Use custom Blender executable paths (e.g., different Blender versions or builds).
- Append your own Python scripts to render jobs for custom logging, post-processing, or pipeline integration.

<img src="images/misc.png" alt="Misc" width="300">

---

## Requirements

- Blender 4.2 or newer
- Windows, Linux

---

## Installation

1. Download the latest release from the [Releases](https://github.com/n4dirp/render-commander/releases) page.
2. In Blender, go to **Edit > Preferences > Get Extensions.**
3. Click **Install from Disk…** and select the downloaded `.zip` file.
4. Enable the add-on by checking the box next to **Render Commander**.

---

## Usage

1. Open the **Render Commander** panel in the **Viewport Sidebar** panel.
2. Choose a render mode: **Image**, **Animation**, or **Frame List**.
3. In the Add‑on Preferences, select the render devices for *Cycles*.
4. Optionally apply a preset or override specific settings.
5. Click **Render** — your job starts immediately, and you can keep working!

---

## Building from Source

If you want to build the extension yourself, follow these steps:

```bash
git clone https://github.com/n4dirp/Render-Commander.git
cd Render-Commander/render_commander
blender --command extension build --split-platforms
```

See blender extensions [build](https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html#command-line-args-extension-build) docs.