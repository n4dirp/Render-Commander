# Changelog

## [1.3.0] - [Unreleased]

### Added
- New **Panel Location** preference to place the addon panels in the **3D Viewport** sidebar, the **Render Properties** tab, or the **Output Properties** tab
- New master **Enable Overrides** toggle to turn all render overrides on or off at once
- New **Render Summary** in the launcher panel showing the current render/export settings and pre-export warnings before exporting scripts

### Changed
- Minimum Blender version bumped to **5.2 LTS**
- Override settings are now shown as individual collapsible boxes inside the **Overrides** panel
- Export options moved to a new **Scripts Output** sub-panel under **Rendder Settings** (the old visibility popup was removed)
- **Visible Panels** toggles moved to the addon preferences
- Removed the **OCIO** custom config env-var option (panel, preferences, presets)

### Fixed
- Prevent exported render scripts from failing on Blender 5.2 when render output is disabled and no active File Output nodes are available

---

## [1.2.6] - 2026-08-01

### Changed
- Removed clipboard access for advanced property overrides
- The **OCIO** panel is now always visible (removed the visibility toggle from preferences)
- Custom variables editor moved from preferences to the **Path Variables** popup

---

## [1.2.5] - 2026-05-05

### Added
- New **FPS Converter** override option

### Changed
- **Manage Cycles Devices** is now optional for parallel rendering
- Export options moved to a popup panel for a cleaner workflow

---

## [1.2.3] - 2026-04-27

### Added
- Added a `Start Delay` setting for parallel renders

### Changed
- Updated UI for improved consistency
- Updated the log format for rendering

### Fixed
- Fixed an issue where removing items not found in export history removed all items
- Fixed an issue where opening a blend file did not check for unsaved changes
- Fixed preset settings in the add-on preferences
- Fixed the modified date in blend info

---

## [1.2.2] - 2026-04-23

### Added
- New options for script file naming

### Fixed
- Improved file path handling overall
- Fixed file paths in render scripts on Unix systems
- Fixed a bug when reading scene information from a .blend file containing multiple cameras
- Added compatibility with Blender 5.0 for the override `Bypass File Outputs`

### Deprecated
- Removed add-on launch options from the top bar

---

## [1.2.1] - 2026-04-21

### Added
- Minor UI and label updates for improved clarity

### Fixed
- Display output paths in **Blend File Details** > **Output Paths**
- Handle `#` characters and correctly in output paths
- Open Script in Text Editor now loads the file into a new Text data-block

### Improved
- Optimized the frame-list script generation for better performance and reliability
