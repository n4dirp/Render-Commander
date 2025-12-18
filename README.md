# Render Commander — Blender Add-on

> *Take full control of background rendering without leaving Blender.*

Run **stills**, **animations**, or **frame lists** in the background while you keep working.<br>
Designed for artists and studios working on multi-GPU systems.

![Render-Commander Panel](images/render_launcher.png)

---

## Features

### Faster Renders on Multi-GPU Systems

- **Device-Parallel Rendering**: Launch multiple background render processes, each assigned to a specific GPU. Cut animation render times dramatically by leveraging all available devices simultaneously.
  
  ![Device-Parallel](images/device_parallel.png)

  ![Device-Parallel Benchmark](images/parallel_render_benchmark.jpg)
  
### Quick Adjustments

- **Render Presets & Overrides**: Tweak resolution, samples, output paths, and more—without altering your original scene. Save and reuse presets for different project stages (draft, final, client review, etc.).
  
  ![Render Overrides](images/override_settings.png)
  
  ![Output Path Templates](images/path_templates.png)

### External Scene Support

- Render scenes stored in **external `.blend` files** without opening them in Blender.

- Preview scene settings, apply overrides, and start renders directly from the add-on panel.
  
  ![External Scene](images/external_scene.png)

### System Integration

- **Prevents system sleep** during renders.
- **Desktop notifications** alert you when a render job finishes.

### Advanced Customization

- Use **custom Blender executable paths** (e.g., different Blender versions or builds).
- Append your own Python scripts to render jobs for custom logging, post-processing, or pipeline integration.

  ![Misc](images/misc.png)

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

```
git clone https://github.com/n4dirp/Render-Commander.git
cd Render-Commander/render_commander
blender --command extension build --split-platforms
```

See [build](https://docs.blender.org/manual/en/latest/advanced/command_line/extension_arguments.html#command-line-args-extension-build) docs.