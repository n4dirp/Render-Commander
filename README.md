# Render Commander — Blender Add-on

> **Take full control of background rendering without leaving Blender.**

Run **stills, animations, or frame lists** in the background while you keep working.
Designed for artists and studios working on **multi-GPU** systems.

<img title="" src="images/render_launcher.png" alt="Alt text" style="zoom:67%;">

---

## Features

### Quick Adjustments

- **Render Presets & Overrides**: Tweak resolution, samples, output paths, and more—without altering your original scene. Save and reuse presets for different project stages (draft, final, client review, etc.).
  
  <img src="images/override_settings.png" title="" alt="override_settings" style="zoom:50%;">
  
  <img src="images/path_templates.png" title="" alt="path_templates" style="zoom:50%;">

### Faster Renders on Multi-GPU Systems

- **Device-Parallel Rendering**: Launch multiple background render processes, each assigned to a specific GPU. Cut animation render times dramatically by leveraging all available devices simultaneously.
  
  <img src="images/device_parallel.png" title="" alt="device_parallel" style="zoom:50%;">
  
  <img src="images/parallel_render_benchmark.jpg" title="" alt="parallel_render_benchmark" style="zoom:50%;">

### External Scene Support

- Render scenes stored in **external `.blend` files** without opening them in Blender.

- Preview scene settings, apply overrides, and start renders directly from the add-on panel.
  
  <img src="images/external_scene.png" title="" alt="external_scene" style="zoom:50%;">

### System Integration

- **Prevents system sleep** during renders.
- **Desktop notifications** alert you when a render job finishes.

### Advanced Customization

- Use **custom Blender executable paths** (e.g., different Blender versions or builds).
- **Append your own Python scripts** to render jobs for custom logging, post-processing, or pipeline integration.
  
  

<img title="" src="images/misc.png" alt="misc" style="zoom:50%;">

---

## Installation

1. Download the latest release from the [Releases](https://github.com/n4dirp/render-commander/releases) page.
2. In Blender, go to **Edit > Preferences > Get Extensions.
3. Click **Install from Disk…** and select the downloaded `.zip` file.
4. Enable the add-on by checking the box next to **Render Commander**.

---

## Usage

1. Open the **Render Commander** panel in the **Viewport Sidebar** panel.
2. Choose a render mode: **Image**, **Animation**, or **Frame List**.
3. **Cycles Render**: On the addon preferences sub-panel select the render devices.
4. Optionally apply a preset or override specific settings.
5. Click **Render** — your job starts immediately, and you can keep working!

---

## Requirements

- Blender 4.2 or newer
- Windows, Linux
