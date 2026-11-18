# Warrior1_2027

ROS 2 development environment and software stack for the Wayne State Robotics Warrior platform.

The project targets **ROS 2 Jazzy** and **Gazebo Harmonic**. The development environment is managed with [**pixi**](https://pixi.sh), which installs ROS 2, Gazebo, RViz2, and all build tools into a self-contained folder inside the repository (`.pixi/`) using packages from [RoboStack](https://robostack.github.io). No system-wide ROS install, `/opt/ros`, `apt` ROS repositories, or Docker are required, and every developer gets the exact same package versions (pinned in `pixi.lock`).

> **Legacy Docker setup:** The `.devcontainer/` folder contains the old ROS 2 Humble Docker environment. It is kept for reference only and is no longer maintained. Use pixi.

## Getting Started

If you want to experiment with the repository, **fork the repository first** and clone your fork.

### Supported platforms

| Platform | Notes |
| --- | --- |
| Ubuntu 24.04 (or other modern Linux) | Recommended |
| Windows 11 | Use WSL2 (Ubuntu 24.04), see below |
| Linux ARM64 (e.g. Jetson / Raspberry Pi) | Supported by the lockfile |
| macOS (Apple Silicon) | Supported by the lockfile, less tested |

### Windows 11 Users

If you are using Windows 11, work inside **WSL (Windows Subsystem for Linux)**.

If WSL is not already installed, open PowerShell or Windows Terminal and run:

```bash
wsl --install
```

After installation, enter WSL:

```bash
wsl
```

All remaining commands in this README are run inside WSL. GUI apps (Gazebo, RViz2) display through WSLg automatically.

> **WSL users:** do not clone the repository inside `/mnt/...`. Store the project inside the WSL filesystem (e.g. under `~`) for much better performance.

### Install pixi

```bash
curl -fsSL https://pixi.sh/install.sh | sh
```

Restart your terminal (or run `source ~/.bashrc`) and verify:

```bash
pixi --version
```

### Graphics drivers (Linux / WSL)

pixi provides everything except the graphics driver, which comes from the host system. A normal Ubuntu desktop already has it. On a minimal install, server, or container, install Mesa:

```bash
sudo apt install libegl-mesa0 libgl1-mesa-dri libglx-mesa0
```

### Clone the Repository

Clone the repository using SSH so that you can push changes to your fork. It can live anywhere; a `ros2_ws/src` layout is **not** required.

```bash
cd ~
git clone git@github.com:<your-username>/Warrior1_2027.git
cd Warrior1_2027
```

> Replace the repository URL above with the SSH URL provided by GitHub under **Code → SSH**.

### Install the environment

From the repository root:

```bash
pixi install
```

The first run downloads ROS 2 Jazzy, Gazebo Harmonic, and the build tools (a few GB) into `.pixi/`. Later runs are instant.

---

# Using the pixi Environment

All commands are run from the repository root. Workspace build output (`build/`, `install/`, `log/`) is created there and is git-ignored.

## Tasks

Common workflows are defined as tasks in `pixi.toml`:

| Command | What it does |
| --- | --- |
| `pixi run build` | `colcon build --symlink-install` for all packages |
| `pixi run test` | Build, then `colcon test` and print results |
| `pixi run clean` | Delete `build/`, `install/`, `log/` |
| `pixi run display` | Show the robot model in RViz2 with joint sliders |
| `pixi run sim` | Launch Gazebo Harmonic with the robot spawned and sensors bridged to ROS |
| `pixi run sim-headless` | Same as `sim`, but Gazebo server only (no GUI window), e.g. over SSH |
| `pixi run talker-listener` | Sanity check that ROS 2 communication works |

Launch tasks build the workspace first, so you don't need to run `pixi run build` separately.

Run `pixi task list` to see all tasks.

## Interactive shell

To get a terminal with ROS 2 available (the equivalent of `source /opt/ros/jazzy/setup.bash`):

```bash
pixi shell
source install/setup.bash   # after building, to use this workspace's packages
```

Then use `ros2`, `colcon`, `gz`, `rviz2`, etc. as normal:

```bash
ros2 launch warrior1_bringup sim.launch.py
ros2 topic list
```

Type `exit` to leave the pixi shell.

You can also run a single command without entering the shell:

```bash
pixi run ros2 topic list
```

## Adding dependencies

ROS packages are installed through pixi, not `apt`/`rosdep`. Package names follow the pattern `ros-jazzy-<package-name>` (underscores become dashes):

```bash
pixi add ros-jazzy-nav2-bringup
pixi add ros-jazzy-robot-localization
```

This updates `pixi.toml` and `pixi.lock`; **commit both files**. Also list the dependency in the package's `package.xml` as usual.

Browse available ROS packages at <https://prefix.dev/channels/robostack-jazzy>.

## Display and GPU notes

* Gazebo and RViz2 use the host's OpenGL driver (Mesa or NVIDIA).
* If you have no GPU, Mesa's software renderer (llvmpipe) is used automatically. It works but is slow; `pixi run sim-headless` avoids the GUI cost while still producing sensor data.
* If Gazebo crashes with `Unable to load Ogre Plugin ... RenderSystem_GL3Plus`, no OpenGL driver is installed; see [Graphics drivers](#graphics-drivers-linux--wsl).

## VS Code

Open the repository root in VS Code. `.vscode/settings.json` points the Python and C++ extensions at the pixi environment. Run `pixi install` first so `.pixi/` exists.

---

# Development Workflow

Before starting work, check the repository's **GitHub Issues** tab.

Issues are labeled by:

* Difficulty
* Type
* Other relevant project information

Choose an issue that you want to work on.

---

# Working on an Issue

## 1. Select an Issue

Read the issue description carefully.

Once you have selected an issue, assign it to yourself.

Under **Development**, select **Create branch**.

> **Branches must be created from `dev`, not `main`.**

Before creating new work, make sure your local `dev` branch is up to date:

```bash
git fetch origin
git checkout dev
git pull origin dev
```

Then create the issue-specific branch from `dev`.

GitHub can also provide the commands for creating and checking out the branch under the issue's **Development** section. Use those commands if provided.

They will generally look similar to:

```bash
git fetch
git checkout <branch-name>
```

## 2. Make Your Changes

Work on the issue in your branch.

Commit frequently rather than accumulating a large number of unrelated changes.

Before committing:

```bash
git status
```

Stage the changes you want included:

```bash
git add .
```

Commit them:

```bash
git commit -m "type-description #issue-number"
```

For example:

```bash
git commit -m "fix-correct wheel joint origin #10"
```

### Commit Types

Use a short type to describe the general nature of the change:

| Type       | Purpose                                               |
| ---------- | ----------------------------------------------------- |
| `fix`      | Bug fix                                               |
| `feat`     | New functionality                                     |
| `clean`    | Cleanup                                               |
| `refactor` | Code restructuring without changing intended behavior |
| `doc`      | Documentation changes                                 |

The remainder of the commit message should briefly describe what changed.

For additional guidance on commit message conventions, see:

[Git commit message guidelines](https://gist.github.com/qoomon/5dfcdf8eec66a051ecd85625518cfd13?utm_source=chatgpt.com)

## 3. Push Your Branch

Once your changes are committed:

```bash
git push
```

This pushes your commits to the remote repository so they are available to the team.

## 4. Open a Pull Request

Go to the GitHub repository and open a **Pull Request**.

The pull request should describe the broad changes made by the branch.

Individual commits should already communicate the detailed changes, so the pull request description should focus on:

* What was changed
* Why it was changed
* Any relevant implementation details
* Testing performed
* Any known limitations

The pull request should target:

```text
dev
```

not `main`.

## 5. Review

The pull request will be reviewed by another team member.

If changes are requested, address the review comments in your existing branch and push the additional commits:

```bash
git add .
git commit -m "fix-address-review-comments #10"
git push
```

The pull request will update automatically.

Once the changes have been reviewed and approved, the issue can be closed and the branch can be deleted.

---

# Branch Structure

The general development flow is:

```text
main
  ↑
  │ approved pull request
  │
dev
  ↑
  │ pull request
  │
issue-specific branch
  │
  └── your local changes
```

**Do not develop directly on `main`&#x20;**

Before creating a new branch, update your local `dev`:

```bash
git fetch origin
git checkout dev
git pull origin dev
```

---

# Quick Reference

### First-time setup

```bash
# Windows only: install WSL if needed, then enter it
wsl --install
wsl

# Install pixi (then restart your terminal)
curl -fsSL https://pixi.sh/install.sh | sh

# Clone your fork
cd ~
git clone git@github.com:<your-username>/Warrior1_2027.git
cd Warrior1_2027

# Install ROS 2 Jazzy + Gazebo Harmonic into .pixi/
pixi install

# Build and test
pixi run test
```

### Everyday use

```bash
cd ~/Warrior1_2027
pixi run build          # build the workspace
pixi run sim            # Gazebo simulation
pixi run display        # RViz2 robot model
pixi shell              # interactive ROS 2 terminal (then: source install/setup.bash)
```

### After pulling changes to pixi.toml / pixi.lock

```bash
pixi install
```
