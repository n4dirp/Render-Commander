# Render Commander

Render Commander exports standalone render scripts with fully embedded settings. It enables parallel rendering across multiple devices and supports advanced configuration for Cycles and EEVEE.

---

## Features

### Launch Modes
- Still images
- Frame sequences
- Custom frame lists (e.g., 1, 5–10, 25)

### External File Rendering
- Inspect scene data from external `.blend` files
- No need to open them in Blender

### Overrides & Presets
- Non-destructive overrides per job
- Includes:
  - Samples
  - Resolution
  - Output settings
- Advanced:
  - Overscan
  - Custom output variables
  - Compositor toggles
  - Override specific data paths
- Save setups as reusable presets

### Parallel Rendering
- **Device Parallel**: One process per GPU
- **Multi-Process**: Multiple Blender instances

### Customization
- Command-line arguments
- Custom Python scripts
- Render time tracking (progress + ETA)

---

## Workflow

### 1. Setup & Generate
Configure frames, overrides, and parallel settings.  
Click **Generate Scripts** and choose an export directory.

### 2. Output Files
Each render job generates:

- **Launch Scripts (`.bat` / `.sh`)**
  - Start Blender in background mode  
  - Example: `scene_render_worker0.bat`

- **Python Scripts (`.py`)**
  - Contain all render settings and frame assignments  
  - Example: `scene_script_worker0.py`

---

## Build from Source

```bash
git clone https://github.com/n4dirp/Render-Commander.git
cd Render-Commander/render_commander
blender --command extension build
```

## Installation

1. Open Blender and go to **Edit → Preferences → Extensions**.
2. Search for **Render Commander**.
3. Click **Install** and enable the add-on.
4. Alternatively, you can install it manually from the [Blender Extensions page](https://extensions.blender.org/add-ons/render-commander/).

