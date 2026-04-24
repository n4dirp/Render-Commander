# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog,
and this project adheres to Semantic Versioning.

## [Unreleased]

### Fixed
- Fixed remove items not found from export history

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
