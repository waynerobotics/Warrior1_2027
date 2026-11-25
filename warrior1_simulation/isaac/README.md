# Isaac Sim integration

Runs the Warrior in NVIDIA Isaac Sim with the **same robot description, the
same controllers and the same ROS topics** as Gazebo. Nothing about the robot
is defined here: `run_isaac.py` reads the URDF generated from
`warrior1_description` and builds the Isaac scene from it.

Written against **Isaac Sim 6.2** (Python 3.12, bundled ROS 2 Jazzy libraries).
For how this fits with Gazebo and the rest of the repo, read
[docs/simulation.md](../../docs/simulation.md) first.

## How it fits together

```
 pixi environment (ROS 2 Jazzy)                     Isaac Sim (its own Python)
 ───────────────────────────────                    ──────────────────────────
 robot_state_publisher ── /robot_description ─────▶ URDF importer → USD robot
 ros2_control_node                                   wheel velocity drives
   TopicBasedSystem ──── /isaac_joint_commands ────▶ articulation controller
                    ◀─── /isaac_joint_states ─────── joint state reader
   diff_drive_controller ◀── /cmd_vel
                         ──▶ /odom, /tf
 your nodes, RViz, Nav2 ◀── /scan, /imu, /clock ──── RTX lidar, IMU, sim clock
```

The two sides only talk over ROS 2 topics (DDS), so Isaac can run on the same
machine or on a different one (e.g. a desktop with a big GPU) on the same
network and `ROS_DOMAIN_ID`.

Isaac Sim gets its **own pixi environment** (`isaac`), separate from the ROS
one: it bundles its own Python and its own ROS 2 libraries, and loading those
next to the pixi ROS libraries in one process crashes. The `isaac` environment
contains only Python 3.12 and the `isaacsim` wheels, pinned in `pixi.lock` like
everything else. `run_isaac.sh` starts Isaac with a clean environment.

## Requirements

NVIDIA RTX GPU (NVIDIA lists RTX 4080 / 16 GB VRAM as the minimum tier), 32 GB+
RAM, ~50 GB free disk, NVIDIA driver 595+, x86-64 Linux with glibc 2.35+
(Ubuntu 22.04+, current Arch). The driver comes from the host; pixi
installs everything else.

## Install Isaac Sim

**pixi (recommended):**

```bash
pixi install -e isaac      # once, ~20+ GB; same Isaac version on every machine
```

On first start Isaac asks you to accept the NVIDIA Omniverse EULA in the
terminal. When it is started by `ros2 launch` there is no terminal to answer
in, so start it once by hand (`pixi run -e isaac isaac-sim-headless`), or
export `OMNI_KIT_ACCEPT_EULA=YES` once you have read and accepted the EULA.

You can also bring your own install instead; `run_isaac.sh` prefers these over
the pixi environment when set:

* **Workstation zip:** unzip `isaac-sim-standalone-6.2.0-linux-x86_64.zip` to
  `~/isaacsim`, run `./post_install.sh`, then `export ISAAC_SIM_PATH=~/isaacsim`.
* **Your own venv:** `pip install "isaacsim[all,extscache]==6.2.0.0" --extra-index-url https://pypi.nvidia.com`
  in a Python 3.12 venv, then `export ISAAC_PYTHON=/path/to/venv/bin/python`.
* **Container:** needs the NVIDIA Container Toolkit.

  ```bash
  docker run --rm -it --gpus all --network=host -e ACCEPT_EULA=Y \
    -v ~/Warrior1_2027:/warrior nvcr.io/nvidia/isaac-sim:6.2.0 bash
  # inside the container:
  ISAAC_SIM_PATH=/isaac-sim /warrior/warrior1_simulation/isaac/run_isaac.sh --headless --livestream
  ```

## Run

**Everything on one machine:**

```bash
pixi run sim-isaac             # ROS side + Isaac with its window
pixi run sim-isaac-headless    # ROS side + Isaac without a window (e.g. over SSH)
pixi run teleop                # drive it (another terminal)
pixi run sim-check             # automated check: topic rates + drive test (another terminal)
```

**Isaac on the GPU desktop, ROS on another machine:**

```bash
# ROS machine:
export ROS_DOMAIN_ID=12
pixi run bash -c 'source install/setup.bash && ros2 launch warrior1_bringup sim.launch.py simulator:=isaac launch_isaac:=false'

# GPU machine (a checkout of this repo with `pixi install -e isaac` done):
export ROS_DOMAIN_ID=12
pixi run -e isaac isaac-sim-headless     # reads /robot_description over the network
```

Start the two sides in either order; the controllers activate once Isaac is
publishing. If the machines are on different subnets or connected through a
VPN such as Tailscale (no multicast), also `export ROS_STATIC_PEERS=<the other
machine's IP>` on each side before starting, and make sure the firewalls allow
DDS (UDP 7400 and up); see
[docs/simulation.md](../../docs/simulation.md#running-a-sim-on-a-remote-machine).

`run_isaac.sh` options (pass them after the script, e.g.
`warrior1_simulation/isaac/run_isaac.sh --headless --livestream`): `--headless`, `--livestream` (WebRTC; connect
with the *Isaac Sim WebRTC Streaming Client*), `--world scene.usd`,
`--physics-hz 200`, `--spawn X Y Z`, `--urdf file.urdf`, `--arena-size 10`
(walls around the default world, `0` = none).

**Viewing the Isaac GUI from a laptop (`--livestream`):** the WebRTC stream
needs TCP 49100 (signaling) and UDP 47998 (video) to reach the sim machine,
so it cannot go through a plain `ssh -L` tunnel. Open those ports on the sim
machine's firewall for your laptop (for ufw: `sudo ufw allow from <laptop-ip>
to any port 49100 proto tcp` and the same for `47998 proto udp`), or connect
over a VPN such as Tailscale/WireGuard whose interface the firewall trusts.
Foxglove (`pixi run foxglove`, port 8765) does work over `ssh -L`.

## What gets translated from the URDF

| URDF | Isaac |
| --- | --- |
| links, joints, inertia, collision/visual geometry | URDF importer |
| `<ros2_control>` joints with a `velocity` command interface | angular velocity drive, max force from `<limit effort>` |
| `<gazebo reference="link"><mu1>/<mu2>` | PhysX material, `min` friction combine (same rule as Gazebo) |
| `<sensor type="imu">` | Isaac IMU → `sensor_msgs/Imu` on the same topic/frame |
| `<sensor type="gpu_lidar">` (1 vertical sample) | RTX 2D lidar → `sensor_msgs/LaserScan`, near/far range from the URDF |
| `<sensor type="gpu_lidar">` (>1 vertical sample) | RTX 3D lidar → `PointCloud2` |
| other sensor types (camera, ...) | not yet: logged and skipped. Add a branch in `create_sensors()` |

Known differences from Gazebo:

* Isaac's RTX LaserScan publisher sends **nothing** for a scan with no
  returns (Gazebo sends all-`inf` ranges). On an empty ground plane `/scan`
  would never appear, which is why the default world has walls
  (`--arena-size`). Any `--world` you load needs something within lidar range.
* Isaac's IMU does not apply the URDF's Gaussian
  noise, and the RTX 2D lidar uses the `Example_Rotary_2D` scan pattern, so the
  angular resolution is the pattern's (0.1°, 3600 rays), not the URDF's `<samples>`.
* Links without `<inertial>` (`base_link`) get a negligible mass in the copy
  of the URDF handed to Isaac's importer; otherwise Isaac 6.2 turns them into
  plain transforms and the wheels end up jointed to the world.

## Troubleshooting

| Symptom | Cause / fix |
| --- | --- |
| `libxml2.so.2: cannot open shared object file` (asset_converter) | Host has libxml2 ≥ 2.14 (Arch, Fedora 42+). The `isaac` env ships 2.13 and `run_isaac.sh` exposes it; re-run `pixi install -e isaac`. |
| `Switch controller timed out` / no `/odom` | controller_manager only ticks once Isaac publishes `/clock`. The spawners wait up to 15 min in Isaac mode; check Isaac actually reached `simulation running`. |
| `JointStateSensor: no DOFs found under articulation root` | The robot was imported as several articulations; see the `<inertial>` note above. |
| `/scan` missing | Nothing within lidar range; see above. |
| Crash a few seconds in with `Out of GPU memory` / `ERROR_OUT_OF_DEVICE_MEMORY` | Another program holds most of the VRAM (`run_isaac.sh` warns below 8 GB free). Check `nvidia-smi` and close it. |
| GUI start hangs after `Attaching default app window` | Isaac waits for its window to become visible, which never happens while the desktop is locked or the display is off. Unlock it, or use `--headless` (optionally with `--livestream`). |
| `waiting ... for /robot_description` never finishes (Isaac on another machine) | DDS can't reach the ROS machine: check `ROS_DOMAIN_ID`, firewalls, and `ROS_STATIC_PEERS` (see above). |

