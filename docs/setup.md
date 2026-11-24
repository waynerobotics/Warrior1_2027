# Setting up your machine

One-time setup for working on Warrior1_2027. When you're done, go back to the
[README](../README.md) for everyday commands.

If you want to experiment with the repository, **fork the repository first** and clone your fork.

## Supported platforms

| Platform | Notes |
| --- | --- |
| Ubuntu 24.04 (or other modern Linux) | Recommended. x86-64 Linux needs glibc 2.35+ (Ubuntu 22.04 or newer, current Arch, Fedora) |
| Windows 11 | Use WSL2 (Ubuntu 24.04), see below |
| Linux ARM64 (e.g. Jetson / Raspberry Pi) | Supported by the lockfile |
| macOS (Apple Silicon) | Supported by the lockfile, less tested |

## Windows 11 users

If you are using Windows 11, work inside **WSL (Windows Subsystem for Linux)**.

If WSL is not already installed, open PowerShell or Windows Terminal and run:

```bash
wsl --install
```

After installation, enter WSL:

```bash
wsl
```

All remaining commands in these docs are run inside WSL. GUI apps (Gazebo, RViz2) display through WSLg automatically.

> **WSL users:** do not clone the repository inside `/mnt/...`. Store the project inside the WSL filesystem (e.g. under `~`) for much better performance.

## Install pixi

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Restart your terminal (or run `source ~/.bashrc`) and verify:

```bash
pixi --version
```

## Graphics drivers (Linux / WSL)

pixi provides everything except the graphics driver, which comes from the host system. A normal Ubuntu desktop already has it. On a minimal install, server, or container, install Mesa:

```bash
sudo apt install libegl-mesa0 libgl1-mesa-dri libglx-mesa0
```

## Clone the repository

Clone the repository using SSH so that you can push changes to your fork. It can live anywhere; a `ros2_ws/src` layout is **not** required.

```bash
cd ~
git clone git@github.com:<your-username>/Warrior1_2027.git
cd Warrior1_2027
```

> Replace the repository URL above with the SSH URL provided by GitHub under **Code → SSH**.

## Install the environment

From the repository root:

```bash
pixi install
```

The first run downloads ROS 2 Jazzy, Gazebo Harmonic, and the build tools (a few GB) into `.pixi/`. Later runs are instant.

Check that everything works:

```bash
pixi run test
```

Run `pixi install` again whenever you pull changes to `pixi.toml` or `pixi.lock`.

## VS Code

Open the repository root in VS Code. `.vscode/settings.json` points the Python and C++ extensions at the pixi environment. Run `pixi install` first so `.pixi/` exists.

## Display and GPU notes

* Gazebo and RViz2 use the host's OpenGL driver (Mesa or NVIDIA).
* If you have no GPU, Mesa's software renderer (llvmpipe) is used automatically. It works but is slow; `pixi run sim-headless` avoids the GUI cost while still producing sensor data.
* If Gazebo crashes with `Unable to load Ogre Plugin ... RenderSystem_GL3Plus`, no OpenGL driver is installed; see [Graphics drivers](#graphics-drivers-linux--wsl).
* Isaac Sim has much bigger requirements (RTX GPU with 16 GB VRAM, 32 GB RAM) and is installed separately; see [the Isaac README](../warrior1_simulation/isaac/README.md).
