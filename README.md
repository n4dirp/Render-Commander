# Render Commander – Background Rendering for Blender

> **Take full control of background rendering without leaving Blender.**

Render Commander is a powerful Blender add-on that lets you run **stills, animations, or custom frame lists** in the background while you continue working. Designed specifically for **artists and studios using multi-GPU systems**, it unlocks parallel rendering capabilities and seamless workflow integration.

Optimized for **Cycles**, it maximizes your hardware by distributing render jobs across multiple GPUs—without affecting your active Blender session.

---

## 🚀 Features

### ⚡ Quick Adjustments

- **Render Presets & Overrides**: Tweak resolution, samples, output paths, and more—without altering your original scene. Save and reuse presets for different project stages (draft, final, client review, etc.).

### 🖥️ Faster Renders on Multi-GPU Systems

- **Device-Parallel Rendering**: Launch multiple background render processes, each assigned to a specific GPU. Cut animation render times dramatically by leveraging all available devices simultaneously.

### 📁 External Scene Support

- Render scenes stored in **external `.blend` files** without opening them in Blender.
- Preview scene settings, apply overrides, and start renders directly from the add-on panel.

### 🔔 System Integration

- **Prevents system sleep** during renders.
- **Desktop notifications** alert you when a render job finishes.

### 🛠️ Advanced Customization

- Use **custom Blender executable paths** (e.g., different Blender versions or builds).
- **Append your own Python scripts** to render jobs for custom logging, post-processing, or pipeline integration.

---

## 📦 Installation

1. Download the latest release from the [Releases](https://github.com/your-username/render-commander/releases) page.
2. In Blender, go to **Edit > Preferences > Get Extensions.
3. Click **Install from Disk…** and select the downloaded `.zip` file.
4. Enable the add-on by checking the box next to **Render Commander**.

---

## ▶️ Usage

1. Open the **Render Commander** panel in the **Viewport Sidebar** panel.
2. Choose a render mode: **Image**, **Animation**, or **Frame List**.
3. **Cycles Render**: On the addon preferences sub-panel select the render devices.
4. Optionally apply a preset or override specific settings.
5. Click **Render** — your job starts immediately, and you can keep working!

---

## 💡 Requirements

- **Blender 4.2 or newer**
- Windows, Linux

---

## 📄 License

Render Commander is licensed under the **GNU General Public License v3.0 (GPL-3.0)** — compatible with Blender’s license.  
See [LICENSE](LICENSE) for details.

---

## 🙌 Feedback & Contributions

Found a bug? Have a feature idea?  
👉 Open an [Issue](https://github.com/your-username/render-commander/issues) or submit a [Pull Request](https://github.com/your-username/render-commander/pulls)!


