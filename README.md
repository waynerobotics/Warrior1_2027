# Warrior1_2027

ROS 2 development environment and software stack for the Wayne State Robotics Warrior platform.

The project targets **ROS 2 Jazzy**, simulated in **Gazebo Harmonic** or **NVIDIA Isaac Sim**. The development environment is managed with [**pixi**](https://pixi.sh), which installs ROS 2, Gazebo, RViz2, and all build tools into a self-contained folder inside the repository (`.pixi/`) using packages from [RoboStack](https://robostack.github.io). No system-wide ROS install, `/opt/ros`, `apt` ROS repositories, or Docker are required, and every developer gets the exact same package versions (pinned in `pixi.lock`).

> **Legacy Docker setup:** The `.devcontainer/` folder contains the old ROS 2 Humble Docker environment. It is kept for reference only and is no longer maintained. Use pixi.

## Documentation

| Doc | Read it when |
| --- | --- |
| [docs/setup.md](docs/setup.md) | Setting up a new machine (WSL, pixi, drivers, VS Code) |
| [docs/simulation.md](docs/simulation.md) | Working with the simulators: how Gazebo/Isaac/mock work with this repo, what to edit for common changes, remote viewing |
| [warrior1_simulation/isaac/README.md](warrior1_simulation/isaac/README.md) | Installing and running Isaac Sim |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Picking up an issue, commit style, branches, pull requests |

## Quick start

```bash
# Windows: run everything inside WSL (see docs/setup.md)
curl -fsSL https://pixi.sh/install.sh | sh        # then restart your terminal
git clone git@github.com:<your-username>/Warrior1_2027.git
cd Warrior1_2027
pixi install                                      # ROS 2 Jazzy + Gazebo into .pixi/
pixi run test                                     # build and run all tests
pixi run sim                                      # Gazebo with the robot
pixi run teleop                                   # drive it (second terminal)
```

After pulling changes to `pixi.toml` / `pixi.lock`, run `pixi install` again.

## Tasks

All commands are run from the repository root. Common workflows are defined as tasks in `pixi.toml`; run `pixi task list` to see them with descriptions.

| Command | What it does |
| --- | --- |
| `pixi run build` | `colcon build --symlink-install` for all packages |
| `pixi run test` | Build, then `colcon test` and print results |
| `pixi run clean` | Delete `build/`, `install/`, `log/` |
| `pixi run display` | Show the robot model in RViz2 with joint sliders |
| `pixi run sim` | Gazebo Harmonic with the robot spawned, controllers running and sensors bridged to ROS |
| `pixi run sim-headless` | Same as `sim`, but Gazebo server only (no GUI window), e.g. over SSH |
| `pixi run sim-remote` | Headless Gazebo + Foxglove bridge on port 8765, to view from another machine |
| `pixi run sim-isaac` | Isaac Sim instead of Gazebo. Needs `pixi install -e isaac` first (see [the Isaac README](warrior1_simulation/isaac/README.md)) |
| `pixi run sim-isaac-headless` | Same, without Isaac's window |
| `pixi run sim-check` | With a sim running: checks topic rates and drives the robot, prints PASS/FAIL |
| `pixi run sim-mock` | No physics at all: controllers run against mock hardware. Works on any laptop |
| `pixi run teleop` | Drive the robot with the keyboard (in a second terminal) |
| `pixi run foxglove` | Start only the Foxglove bridge (port 8765) next to an already-running sim. Remote viewing and driving: [docs/simulation.md](docs/simulation.md#running-a-sim-on-a-remote-machine) |
| `pixi run talker-listener` | Sanity check that ROS 2 communication works |

Isaac Sim lives in a separate, opt-in pixi environment (`isaac`, about 20 GB, x86-64 Linux only), so `pixi install` alone never downloads it. Its own tasks run with `-e isaac`, e.g. `pixi run -e isaac isaac-sim-headless`.

Launch tasks build the workspace first, so you don't need to run `pixi run build` separately. Build output (`build/`, `install/`, `log/`) is git-ignored.

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

Type `exit` to leave the pixi shell. You can also run a single command without entering the shell:

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

## Repository layout

| Package | Contents |
| --- | --- |
| `warrior1_description` | The robot model (URDF/xacro): links, joints, masses, sensors, ros2_control |
| `warrior1_bringup` | Launch files and `config/controllers.yaml` |
| `warrior1_simulation` | Gazebo worlds, the shared URDF reader (`robot_model.py`), the Isaac Sim launcher (`isaac/`) |
| `warrior1_localization` | Localization (empty package, not started yet) |
| `warrior1_navigation` | Navigation (empty package, not started yet) |
