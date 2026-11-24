# Simulation guide

How the Warrior is simulated, what each piece does, and what to edit when you
want to change something. No prior Gazebo or Isaac Sim experience assumed.

* [The one-paragraph version](#the-one-paragraph-version)
* [Concepts you need](#concepts-you-need)
* [Where everything lives](#where-everything-lives)
* [What happens when you run a sim](#what-happens-when-you-run-a-sim)
* [Gazebo, step by step](#gazebo-step-by-step)
* [Isaac Sim, step by step](#isaac-sim-step-by-step)
* [Mock mode](#mock-mode)
* [The ROS interface every simulator provides](#the-ros-interface-every-simulator-provides)
* [Common changes: what to edit](#common-changes-what-to-edit)
* [Checking that a sim is healthy](#checking-that-a-sim-is-healthy)
* [Running a sim on a remote machine](#running-a-sim-on-a-remote-machine)
* [Known limitations](#known-limitations)

## The one-paragraph version

The robot is described **once**, in `warrior1_description` (a URDF written in
xacro). One launch file, `sim.launch.py`, turns that description into a URDF
and hands it to whichever simulator you pick: Gazebo, Isaac Sim, or "mock" (no
physics). The wheels are driven by **ros2_control** with **one** controller
config, `controllers.yaml`; only a small "hardware plugin" underneath changes
per simulator. Whatever simulator runs, the rest of the code sees the same ROS
topics (`/cmd_vel`, `/odom`, `/scan`, `/imu`, `/tf`, ...), so navigation and
localization code never needs to know which simulator, or the real robot, is
underneath.

```
                    warrior1_description (xacro)  ← the only robot definition
                                 │ xacro
                                 ▼
                               URDF ──────────────┬──────────────────┐
                                 │                │                  │
                  robot_state_publisher      Gazebo spawns it    Isaac imports it
                  (/robot_description, /tf)       │                  │
                                                  ▼                  ▼
  controllers.yaml ──► ros2_control ◄──── GazeboSimSystem    TopicBasedSystem ◄─► Isaac
                       diff_drive_controller                  (over ROS topics)
                       joint_state_broadcaster
                                 │
                                 ▼
          /odom  /tf  /joint_states  /scan  /imu  /clock   ← same in every simulator
```

## Concepts you need

**URDF / xacro.** A URDF is an XML file listing the robot's *links* (rigid
parts, with shape, mass and inertia) and *joints* (how links connect: `fixed`,
or `continuous` for a wheel that spins forever). Xacro is URDF plus macros and
variables, so you can write `diff_wheel` once and use it for both wheels.
Running `xacro` produces a plain URDF. Simulator-specific extras live in
`<gazebo reference="link">` blocks inside the URDF: friction and sensors.

**TF.** The tree of coordinate frames (`odom → base_link → chassis →
laser_frame`, ...). `robot_state_publisher` reads the URDF plus
`/joint_states` and publishes the robot-internal part. The
`diff_drive_controller` publishes `odom → base_link`.

**ros2_control.** The standard ROS layer between controllers and hardware. It
has three parts:

* the **controller manager**, which loads and runs controllers in a fixed-rate loop (50 Hz here);
* **controllers**: `diff_drive_controller` turns `/cmd_vel` into left/right
  wheel speeds and turns measured wheel motion into `/odom`;
  `joint_state_broadcaster` publishes `/joint_states`;
* a **hardware interface** (plugin) that actually moves the wheels. In Gazebo
  that's Gazebo's physics, in Isaac it's a pair of ROS topics to Isaac, in mock
  mode it's a fake that echoes commands back, and on the real robot it will be
  the motor driver.

The `<ros2_control>` block in the URDF says which joints exist, what can be
commanded (wheel *velocity*), what can be read (*position*, *velocity*) and
which hardware plugin to use. Controllers only ever talk to that interface,
which is why they don't care what is underneath.

**Simulated time.** Simulators publish `/clock`, and every node runs with
`use_sim_time: true`, so timestamps follow the simulation even if it runs
slower or faster than real time.

**Bridges.** Gazebo has its own message system (gz-transport), separate from
ROS. `ros_gz_bridge` copies messages between the two. Isaac publishes ROS
messages directly through its built-in ROS 2 bridge, so it needs no extra
bridge process.

## Where everything lives

| What | File | Used by |
| --- | --- | --- |
| Dimensions, masses, motor limits | `warrior1_description/urdf/warrior.urdf` (properties at the top) | everything |
| Wheel, caster, lidar, IMU | `warrior1_description/xacro/*.xacro` | everything |
| ros2_control joints + hardware plugin per simulator | `warrior1_description/xacro/ros2_control.xacro` | everything |
| Controller settings (speed limits, frames, timeout) | `warrior1_bringup/config/controllers.yaml` | ros2_control in every mode |
| Launch logic | `warrior1_bringup/launch/sim.launch.py` | all modes |
| Foxglove bridge settings (remote viewing) | `warrior1_bringup/launch/foxglove.launch.py` | `sim-remote`, `pixi run foxglove` |
| URDF reader (wheel geometry, sensors, friction) | `warrior1_simulation/warrior1_simulation/robot_model.py` | `sim.launch.py` and `run_isaac.py` |
| Gazebo world | `warrior1_simulation/worlds/empty.sdf` | Gazebo |
| Isaac launcher | `warrior1_simulation/isaac/run_isaac.sh` → `run_isaac.py` | Isaac |
| Isaac install (pinned version) | `[feature.isaac]` in `pixi.toml` | `pixi install -e isaac` |
| Sim health check | `warrior1_simulation/warrior1_simulation/sim_check.py` | `pixi run sim-check` |
| Tests that keep all of this consistent | `warrior1_simulation/test/test_robot_model.py` | `pixi run test` |

`robot_model.py` deserves a note. Both the launch file and Isaac need facts
*derived* from the URDF: wheel separation and radius, which sensors exist,
friction per link. Rather than computing those in two places (and letting them
drift apart), they both call this one small file. It uses only the Python
standard library, so it runs in pixi's Python and in Isaac's Python alike.

## What happens when you run a sim

`pixi run sim`, `sim-isaac` and `sim-mock` all run the same launch file with a
different `simulator:=` argument. `sim.launch.py` does this:

1. **Generate the URDF.** Runs xacro on `warrior.urdf` with
   `sim_mode:=<simulator>`. That argument only changes which hardware plugin
   ends up in the `<ros2_control>` block. Links, joints and sensors are
   identical in every mode.
2. **Derive the wheel geometry.** `RobotModel` measures the distance between
   the two wheel joints and the wheel collision radius, and writes them to a
   small `diff_drive_kinematics.yaml` in a temp directory (path printed at
   startup as `generated files in /tmp/warrior_sim_...`). That's why
   `controllers.yaml` has no wheel sizes in it.
3. **Start the common nodes:**
   * `robot_state_publisher`: publishes the URDF on `/robot_description` and the robot's TF;
   * two **spawners**, which wait for the controller manager, then load
     `joint_state_broadcaster` and `diff_drive_controller` (with
     `controllers.yaml` + the generated kinematics file) and activate them.
     They remap the controller's topics to plain `/cmd_vel` and `/odom`.
4. **Start the simulator-specific part** (below).
5. Optionally start `foxglove_bridge` (`foxglove:=true`) for remote viewing.

Launch arguments: `simulator` (gazebo|isaac|mock), `headless`, `foxglove`,
`world` (Gazebo .sdf), `isaac_world` (Isaac .usd), `launch_isaac`.

## Gazebo, step by step

`pixi run sim` (or `sim-headless`, `sim-remote`)

1. **Gazebo starts** with `worlds/empty.sdf`. With `headless:=true` only the
   physics/rendering server runs, with no window.
2. **The robot is spawned.** `ros_gz_sim create` reads `/robot_description`
   and inserts the robot 6 cm above the ground. Gazebo converts the URDF to
   its own format (SDF) on the fly, and the `<gazebo>` blocks are applied:
   * `mu1`/`mu2` friction on the wheels (grippy) and caster (slippery);
   * the `gpu_lidar` and `imu` sensors, publishing on Gazebo topics `scan` and `imu`;
   * the **gz_ros2_control plugin** (only added when `sim_mode:=gazebo`).
3. **ros2_control runs inside Gazebo.** The plugin starts a controller manager
   inside the Gazebo process, using `GazeboSimSystem` as hardware: wheel
   velocity commands become joint velocity targets in Gazebo's physics, and the
   joint position/velocity come straight back from physics.
4. **The spawners connect** to that controller manager and activate the two
   controllers. Now `/cmd_vel` drives the wheels and `/odom` reports motion.
5. **The bridge** (`ros_gz_bridge parameter_bridge`) copies `/clock`, `/scan`
   and `/imu` from Gazebo to ROS. The list of topics is generated from the
   sensors in the URDF by `gz_bridge_arguments()`, so a new sensor in xacro is
   bridged automatically.

## Isaac Sim, step by step

`pixi run sim-isaac` or `sim-isaac-headless` (after `pixi install -e isaac`; see
[the Isaac README](../warrior1_simulation/isaac/README.md))

Isaac Sim is a separate program with its own Python 3.12 and its own copy of
the ROS 2 libraries. It's installed into its **own pixi environment**
(`pixi install -e isaac`), separate from the ROS environment, because loading
Isaac's ROS libraries and pixi's in the same process crashes. The two sides
only talk over ROS topics, so they can even run on different machines.

**ROS side (pixi):**

1. Same URDF, but with `sim_mode:=isaac`, which selects the
   `TopicBasedSystem` hardware plugin.
2. Unlike Gazebo, Isaac doesn't host the controller manager, so
   `ros2_control_node` runs as a normal ROS node with the same
   `controllers.yaml`.
3. `TopicBasedSystem` is the hardware plugin. Every control cycle it publishes
   the wheel velocity commands on `/isaac_joint_commands` and reads wheel
   positions/velocities from `/isaac_joint_states`.
4. If the pixi `isaac` environment is installed (or `ISAAC_PYTHON` /
   `ISAAC_SIM_PATH` point at another install), the launch file also starts
   Isaac via `run_isaac.sh`. With `launch_isaac:=false` it only starts the ROS
   side and you start Isaac yourself, possibly on another machine.

**Isaac side (`run_isaac.py`, running in Isaac's Python):**

1. `run_isaac.sh` finds Isaac's Python (normally `.pixi/envs/isaac`), clears
   the environment (so the ROS environment's libraries don't leak in), sets up
   Isaac's bundled ROS 2 Jazzy libraries, and runs `run_isaac.py`.
2. **Get the URDF**, from the file the launch file wrote, or by subscribing to
   `/robot_description` when Isaac runs on another machine.
3. **Import it.** Isaac's URDF importer converts it to USD (Isaac's scene
   format). Links, joints, meshes, mass and inertia come across directly.
4. **Apply what the importer doesn't handle, read from the same URDF via `RobotModel`:**
   * every joint with a `velocity` command interface in `<ros2_control>` gets a
     velocity drive, with max force from `<limit effort>`;
   * every `<gazebo reference><mu1>/<mu2>` becomes a PhysX friction material
     (with the same "take the lower of the two surfaces" rule Gazebo uses);
   * every `<sensor type="imu">` becomes an Isaac IMU, and every
     `<sensor type="gpu_lidar">` an RTX lidar, publishing on the same topic
     and frame as in Gazebo.
5. **Build the ROS graph** (OmniGraph, Isaac's node-based scripting) that runs
   every physics step: publish `/clock`; publish wheel states on
   `/isaac_joint_states`; subscribe to `/isaac_joint_commands` and feed them to
   the wheel drives; publish `/imu` and `/scan`.
6. **Run** physics at 100 Hz (`--physics-hz`), paced to real time so teleop
   feels the same as on the robot.

The result: `diff_drive_controller` does the same maths as in Gazebo, it just
gets its wheel feedback over a topic instead of from inside the simulator.

## Mock mode

`pixi run sim-mock`: no simulator and no physics. `mock_components/GenericSystem`
pretends to be the hardware and reports back exactly the wheel velocity it was
commanded. `/odom` and `/tf` behave as if the robot drove perfectly, but there
are no sensors (`/scan`, `/imu`) and no collisions. Use it to test controller
settings, teleop, or anything that only needs odometry, on any laptop.

## The ROS interface every simulator provides

| Topic | Type | Published by |
| --- | --- | --- |
| `/cmd_vel` | `geometry_msgs/TwistStamped` | **you** (teleop, Nav2, ...) → robot |
| `/odom`, `/tf` (`odom → base_link`) | `nav_msgs/Odometry`, TF | `diff_drive_controller` |
| `/joint_states`, `/tf` (robot links) | `sensor_msgs/JointState`, TF | `joint_state_broadcaster` + `robot_state_publisher` |
| `/robot_description` | `std_msgs/String` | `robot_state_publisher` |
| `/scan` | `sensor_msgs/LaserScan` | lidar (not in mock) |
| `/imu` | `sensor_msgs/Imu` | IMU (not in mock) |
| `/clock` | `rosgraph_msgs/Clock` | simulator (not in mock) |

`/cmd_vel` is **stamped** (`TwistStamped`, a twist plus a header with a
timestamp) because that's the only type the Jazzy `diff_drive_controller`
accepts. A plain `Twist` on `/cmd_vel` is silently ignored. `pixi run teleop`
already sends the stamped version; set Nav2's `enable_stamped_cmd_vel: true`
when we get there.

## Common changes: what to edit

| I want to... | Edit | Notes |
| --- | --- | --- |
| Change wheel size or track width | `diff_wheel_radius` / `diff_wheel_y` in `warrior.urdf` | The controller picks it up automatically. Keep the caster radius matching so all wheels touch the ground |
| Change a mass | the mass properties at the top of `warrior.urdf` | Keep the chassis the heaviest part, otherwise physics gets unstable |
| Change motor strength / top wheel speed | `diff_wheel_max_effort` / `diff_wheel_max_velocity` in `warrior.urdf` | Used by ros2_control limits and by both simulators' joint drives |
| Change max robot speed / acceleration | `linear.x.*` / `angular.z.*` in `controllers.yaml` | |
| Change how long the robot keeps moving after the last `/cmd_vel` | `cmd_vel_timeout` in `controllers.yaml` | |
| Change wheel or caster grip | `<mu1>`/`<mu2>` in `diff_wheel.xacro` / `caster_wheel.xacro` | Applied in Gazebo and Isaac |
| Move a sensor | IMU: the `x y z` passed to its macro in `warrior.urdf`. Lidar: the `laser_joint` origin in `lidar.xacro` | |
| Change lidar range/rate/samples | `lidar.xacro` | Isaac uses range and rate; see [Known limitations](#known-limitations) |
| Add a sensor | a `<gazebo reference="link"><sensor ...>` block in a xacro | Gazebo bridging is automatic. Isaac supports IMU and lidar today; other types are skipped with a warning until a branch is added in `create_sensors()` in `run_isaac.py` |
| Add a joint you want to control | the joint in xacro + an entry in `ros2_control.xacro` + a controller in `controllers.yaml` | Isaac drives any joint with a velocity command interface automatically |
| Use a different Gazebo world | `world:=/path/to/world.sdf` | |

After any change, `pixi run test` checks that the URDF still builds in every
mode and that the wheels, sensors and masses are still consistent.

To see the URDF a simulator actually receives:

```bash
pixi run bash -c 'source install/setup.bash && xacro warrior1_description/urdf/warrior.urdf sim_mode:=gazebo'
```

## Checking that a sim is healthy

With any sim running (Gazebo, Isaac or mock, headless or not), in a second terminal:

```bash
pixi run sim-check
```

It works out which simulator is running, checks that `/clock`, `/joint_states`,
`/odom`, `/scan` and `/imu` arrive at sensible rates (only the ones that
simulator provides), drives forward for 5 s, and checks `/odom` moved forward
and straight. It prints PASS/FAIL per check and exits non-zero on failure.
Options: `--timeout` (wait for a slow sim to start, default 120 s), `--speed`,
`--drive-time`; pass them with
`pixi run bash -c 'source install/setup.bash && ros2 run warrior1_simulation sim_check --timeout 300'`.

To look around by hand (`pixi shell`, then `source install/setup.bash`):

```bash
ros2 control list_controllers        # both controllers should be "active"
ros2 control list_hardware_interfaces
ros2 topic hz /scan                  # ~10 Hz
ros2 topic hz /imu                   # ~100 Hz
ros2 topic echo /odom --once
```

Drive forward without teleop:

```bash
ros2 topic pub -r 10 /cmd_vel geometry_msgs/msg/TwistStamped \
  "{header: {frame_id: base_link}, twist: {linear: {x: 0.3}}}"
```

Common problems:

* **Controllers never become active:** the controller manager isn't up. In
  Gazebo, check the robot actually spawned. In Isaac, check `/isaac_joint_states`
  is being published (`ros2 topic hz /isaac_joint_states`).
* **Robot doesn't move:** check you're publishing `TwistStamped`, not `Twist`
  (`ros2 topic info /cmd_vel -v`).
* **Nothing arrives from another machine:** see
  [Running a sim on a remote machine](#running-a-sim-on-a-remote-machine).

## Running a sim on a remote machine

Simulators need a GPU; your laptop may not have one. There are three ways to
use a sim running on another machine (a lab desktop, a GPU server), from most
to least common. In all of them the sim machine has its own checkout of this
repo with `pixi install` (and `pixi install -e isaac` for Isaac) done.

**1. View the sim from your laptop (Foxglove).** Run the sim headless on the
GPU machine and look at it through one websocket:

```bash
# on the sim machine (e.g. over SSH)
pixi run sim-remote                     # Gazebo, headless, + Foxglove bridge
pixi run sim-isaac-headless             # or Isaac, then in a second shell:
pixi run foxglove
# on your laptop
ssh -L 8765:localhost:8765 <user>@<sim-machine>
```

Open [Foxglove](https://app.foxglove.dev) → *Open connection* →
`ws://localhost:8765`. You can view `/scan`, TF, the robot model and plots.
In the 3D panel's settings: under *Topics* turn on `/robot_description` (the
robot model; without it you only see frame axes) and `/scan`, and set
*Frame → Display frame* to `odom` so the robot moves through a fixed world
(with `base_link` the view rides along and only `odom` appears to move).
Your laptop needs nothing installed besides SSH and a browser. Run
`pixi run sim-check` on the sim machine to confirm the sim itself is healthy.

To drive, run keyboard teleop on the sim machine through its own SSH session
(`-t` gives it the terminal it needs to read keys), with the same
`ROS_DOMAIN_ID` as the sim if you set one:

```bash
ssh -t <user>@<sim-machine> 'cd <path-to>/Warrior1_2027 && pixi run teleop'
```

Driving from Foxglove itself also works, but it must publish
`geometry_msgs/msg/TwistStamped` on `/cmd_vel`; a plain `Twist` is ignored
(see [the ROS interface](#the-ros-interface-every-simulator-provides)).

If it feels slow (delayed view, sluggish SSH terminal), the link is
saturated. The bridge (`warrior1_bringup/launch/foxglove.launch.py`) already
hides the high-rate internal topics (`/controller_manager/*` at ~1000 msg/s,
`/clock`) and drops old messages instead of queueing them, so what's left is
about 1 Mbit/s. Beyond that: open only the panels you need (each subscribed
topic costs bandwidth), and if you use Tailscale check that `tailscale status`
shows the sim machine as `direct`, not `relay`.

The bridge has no authentication and anyone connected to it can drive the
robot, so it only listens on localhost on the sim machine: the SSH tunnel
above is how you reach it. To serve it on another interface on purpose (e.g.
a VPN address), start it with
`ros2 launch warrior1_bringup foxglove.launch.py address:=<ip>` instead.

**2. See the simulator's own GUI.** For Isaac, run
`warrior1_simulation/isaac/run_isaac.sh --headless --livestream` and connect
with the Isaac Sim WebRTC Streaming Client (ports and firewall in
[the Isaac README](../warrior1_simulation/isaac/README.md#run)). For Gazebo,
use a remote desktop (NoMachine, Sunshine/Moonlight); `ssh -X` is too slow for
Gazebo's 3D view.

**3. Run ROS on one machine and Isaac on another.** Useful when your own
machine runs the ROS side (your nodes, RViz, Nav2) and only Isaac needs the
GPU. The two sides talk over ROS 2 (DDS) directly, so:

* both machines must use the same `ROS_DOMAIN_ID`;
* DDS uses UDP ports 7400 and up (7400 + 250 × domain id onwards); the sim
  machine's firewall must allow them from the other machine;
* DDS finds other machines by multicast, which works on a normal LAN but **not**
  over most VPNs (Tailscale, WireGuard) or across subnets. There, list the
  other machine explicitly on both sides:
  `export ROS_STATIC_PEERS=<other machine's IP>`.

Commands for this setup are in
[the Isaac README](../warrior1_simulation/isaac/README.md#run). Option 1 is
simpler whenever it's enough, because only one TCP port crosses the network.

## Known limitations

* Isaac's IMU doesn't apply the Gaussian noise defined in the URDF.
* Isaac's 2D lidar uses the built-in `Example_Rotary_2D` scan pattern, so its
  angular resolution won't exactly match the URDF's 360 samples.
* Masses and dimensions are placeholders until the real robot is measured.
* The camera dimensions are defined in `warrior.urdf` but no camera is mounted yet.
