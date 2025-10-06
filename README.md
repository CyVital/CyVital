---

# CyVitals

![License](https://img.shields.io/badge/License-GPL%20v3.0-blue.svg)
![Version](https://img.shields.io/badge/Version-1.0-brightgreen.svg)
![Status](https://img.shields.io/badge/Status-Active-success.svg)

## Project Overview

**CyVitals** is dedicated to providing modular hardware in the form of sensors and its corresponding software counterpart to read, analyze and display data seen within physiological sensors.

## Features
- **IN-PROGRESS**: N/A

## Lead Developers
- Ty Beresford
- Sajan Patel
- Daniel Karpov
- Jay Patel

## External Libraries
- imgui-bundle: [GitHub](https://github.com/pthom/imgui_bundle/)

## License
CyVitals is licensed under the **GNU General Public License v3.0 (GPL-3.0)**. See the [LICENSE](LICENSE) file for more details or visit [GNU GPL v3.0](https://www.gnu.org/licenses/gpl-3.0.en.html).

# INSTALL MACOS
- 1. /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
- 2. brew install cmake pkg-config freetype (OPTIONAL M1: export ARCHFLAGS="-arch arm64" or "echo 'export ARCHFLAGS="-arch arm64"' >> ~/.zshrc")
- 3. python -m pip install --upgrade pip setuptools wheel
- 4. python -m pip install --force-reinstall --no-cache-dir --config-settings=cmake.define.HELLOIMGUI_USE_SDL_OPENGL3=ON imgui-bundle