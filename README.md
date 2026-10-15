# Warrior1_2027

ROS 2 development environment and software stack for the Wayne State Robotics Warrior platform.

The repository includes a Docker-based development environment providing **ROS 2 Humble, Gazebo, and RViz2**. The environment is designed to provide a consistent setup across development machines while allowing GUI applications to run directly through the host display.

## Getting Started

If you want to experiment with the repository or Docker environment, **fork the repository first** and clone your fork.

### Windows 11 Users

If you are using Windows 11, the project uses **WSL (Windows Subsystem for Linux)** rather than running Docker directly through Windows.

If WSL is not already installed, open PowerShell or Windows Terminal and run:

```bash
wsl --install
```

After installation, enter WSL:

```bash
wsl
```

### Install Docker in WSL

This project uses **Docker Engine installed directly inside WSL**. **Docker Desktop is not required and should not be used for this setup.**

The exact Docker installation procedure depends on your WSL Linux distribution. For Ubuntu, follow Docker's installation instructions for Ubuntu.

A guide for installing Docker directly in WSL without Docker Desktop is available here:

[Install Docker directly in WSL without Docker Desktop](https://daniel.es/blog/how-to-install-docker-in-wsl-without-docker-desktop/?utm_source=chatgpt.com)

After installing Docker, verify that it is working:

```bash
docker run hello-world
```

Make sure Docker Compose is also available:

```bash
docker compose version
```

> **WSL users:** Docker should be installed and running inside the WSL environment itself. Do not install Docker Desktop as part of this setup.

### Clone the Repository

Choose a location for your project files and navigate there using `cd` and `ls`.

If you are using WSL, **do not clone the repository inside `/mnt/...`**. Store the project inside the WSL filesystem for better performance.

Create the workspace structure:

```bash
cd ~
mkdir -p ros2_ws/src
cd ros2_ws/src
```

Clone the repository using SSH so that you can push changes to your fork:

```bash
git clone git@github.com:<your-username>/Warrior1_2027.git
```

Your final directory structure should look like:

```text
~/ros2_ws/
└── src/
    └── Warrior1_2027/
        ├── .devcontainer/
        ├── ...
        └── ...
```

> Replace the repository URL above with the SSH URL provided by GitHub under **Code → SSH**.

---

# Docker Development Environment

The Docker environment provides:

* ROS 2 Humble
* Gazebo
* RViz2
* Required development dependencies
* A consistent Ubuntu/ROS environment for the project

GUI applications use the host **X11/WSLg display directly**. Mesa is configured for **software rendering (llvmpipe)** by default.

## Initial Setup

From the repository root:

```bash
cd ~/ros2_ws/src/Warrior1_2027
```

### Native Linux

On native Linux, allow local Docker clients to connect to the X server:

```bash
xhost +local:docker
```

This is only required for native Linux X11. WSLg uses its own display integration.

### Run the Setup Script

Navigate into `.devcontainer`:

```bash
cd .devcontainer
```

Run:

```bash
./setup.sh
```

The setup script detects the host environment and configures the corresponding display mounts.

It supports:

* Native Linux X11
* Windows WSL2/WSLg
* Software rendering
* Optional hardware acceleration
* Headless operation

Run the setup script again whenever you change the GUI or acceleration configuration.

### Build the Docker Image

For the initial setup:

```bash
docker compose build
```

Run this again when the `Dockerfile` or other Docker build dependencies change.

Normally, the cached build is sufficient. If you need to force a completely fresh build:

```bash
docker compose build --no-cache
```

### Start the Container

For normal startup:

```bash
docker compose up -d
```

This starts the container in the background.

If the Compose configuration has changed and the container needs to be recreated:

```bash
docker compose up -d --force-recreate
```

### Open a Docker Terminal

```bash
docker compose exec ros2 bash
```

You can now work inside the ROS 2 development environment.

---

# Display and GPU Configuration

Software rendering is the default configuration. This uses Mesa's **llvmpipe** renderer inside the container and provides a consistent fallback across supported hosts.

The setup script can be used to change the rendering mode.

## Software Rendering

To explicitly configure software rendering:

```bash
./setup.sh --accel=software
```

After changing the acceleration setting, recreate the container:

```bash
docker compose up -d --force-recreate
```

## Hardware Acceleration

If your system supports GPU passthrough, hardware acceleration can be enabled with:

```bash
./setup.sh --accel=hardware
```

This configures the appropriate device for the host:

| Host         | GPU device |
| ------------ | ---------- |
| Native Linux | `/dev/dri` |
| WSL2         | `/dev/dxg` |

The llvmpipe override is removed when hardware acceleration is enabled.

After changing the rendering configuration, recreate the container:

```bash
docker compose up -d --force-recreate
** This might not work, so if so, make an issue with the details about your environment an graphics capability and it (might) be fixed**
```

## Headless Mode

If GUI applications are not required:

```bash
./setup.sh --gui=false
```

Then recreate the container:

```bash
docker compose up -d --force-recreate
```

This configures the environment without host GUI display integration.

---

# Development Workflow

Once the Docker container is running, open a terminal inside it:

```bash
docker compose exec ros2 bash
```

From there, work normally within the ROS 2 workspace.

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

### First-time setup — Windows 11 / WSL

```bash
# Only if WSL is not already installed
wsl --install

# Enter WSL
wsl

# Create the ROS workspace
cd ~
mkdir -p ros2_ws/src
cd ros2_ws/src

# Clone your fork
git clone git@github.com:<your-username>/Warrior1_2027.git
cd Warrior1_2027/.devcontainer

# Configure the environment
./setup.sh

# Build the image
docker compose build

# Start the container
docker compose up -d

# Enter the container
docker compose exec ros2 bash
```

### Normal startup

```bash
cd ~/ros2_ws/src/Warrior1_2027/.devcontainer
docker compose up -d
docker compose exec ros2 bash
```

### After changing the Dockerfile

```bash
docker compose build
docker compose up -d --force-recreate
```

If a completely fresh build is required:

```bash
docker compose build --no-cache
docker compose up -d --force-recreate
```

### Change rendering mode

```bash
# Software rendering
./setup.sh --accel=software

# Hardware acceleration
./setup.sh --accel=hardware

# Headless
./setup.sh --gui=false
```

After changing the rendering mode:

```bash
docker compose up -d --force-recreate
```

### Update `dev` before creating a branch

```bash
git fetch origin
git checkout dev
git pull origin dev
```

### Git workflow

```bash
# Create/switch to your issue branch
git checkout <branch-name>

# Make changes...

# Check changes
git status

# Commit
git add .
git commit -m "type-description #issue-number"

# Push
git push
```

Then open a pull request targeting **`dev`**.
