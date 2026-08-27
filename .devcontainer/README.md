# ROS 2 Humble Devcontainer — Quickstart

Works the same way on Linux, Windows, and macOS. No X server, XQuartz,
VcXsrv, or GPU setup required to get started.

## 1. Prerequisites (all platforms)
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) (Windows/macOS) or Docker Engine (Linux)
- [VS Code](https://code.visualstudio.com/) + the "Dev Containers" extension

## 2. Open the project
1. Put `.devcontainer/Dockerfile`, `.devcontainer/devcontainer.json`, and
   `.devcontainer/supervisord.conf` in a `.devcontainer/` folder at the
   root of your workspace.
2. Open the folder in VS Code.
3. Command Palette → **Dev Containers: Reopen in Container**.
4. Wait for the image to build (first time only — a few minutes).

## 3. View the GUI (Gazebo, RViz2, etc.)
Once the container is running, open a browser tab to:

```
http://localhost:6080/vnc.html
```

Click **Connect**. You now have a virtual desktop running inside the
container — this is where Gazebo and RViz2 windows will appear when you
launch them from the VS Code integrated terminal, e.g.:

```bash
ros2 launch turtlebot3_gazebo empty_world.launch.py
```

or

```bash
rviz2
```

## Why this works everywhere
GUI apps render into a virtual display (`Xvfb`) inside the container using
software OpenGL, get shared over VNC, and are bridged to a plain web page
(noVNC) on port 6080. Nothing depends on the host having a GPU, an X
server, or any OS-specific display protocol — a browser is the only
requirement.

This does mean rendering isn't hardware-accelerated by default, so complex
Gazebo worlds may feel a bit sluggish. That's the trade-off for "it just
works on everyone's laptop." If you're on native Linux with a supported
GPU and want to opt into hardware acceleration on your own machine, see
the commented-out block at the bottom of `devcontainer.json`.

## Notes
- The forwarded port (6080) is per-user/per-container, so this doesn't
  expose anything to your network — VS Code only makes it reachable from
  `localhost`.
- If `postStartCommand` ever fails to bring the GUI stack up (e.g. after a
  container rebuild), run manually inside the container:
  ```bash
  sudo supervisorctl -c /etc/supervisor/supervisord.conf restart all
  ```
