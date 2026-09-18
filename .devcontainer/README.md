


This Docker setup provides ROS 2 Humble, Gazebo, and RViz2 for development. GUI applications use the host X11/WSLg display directly while Mesa is forced to software rendering (llvmpipe) inside the container. There is no virtual display, VNC server, browser relay, or forwarded GUI port.

For execution, enter the following commands:

From the repository root:

On native Linux, allow local Docker clients to connect to the X server:

xhost +local:docker

docker compose build --no-cache # Builds the docker image from the Dockerfile, and docker-compose.yml

docker compose up -d --force-recreate # Runs the container in the background (-d) so the terminal can be used for other things

The setup script runs automatically before a devcontainer rebuild. It detects native Linux X11 or WSLg and configures the corresponding display mounts. Software rendering is the default. To enable supported GPU passthrough, run `.devcontainer/setup.sh --accel=hardware` before rebuilding; this adds `/dev/dri` on native Linux or `/dev/dxg` on WSL2 and removes the llvmpipe override. To force CPU rendering again, run `.devcontainer/setup.sh --accel=software`.

For a headless session, run `.devcontainer/setup.sh --gui=false` before rebuilding. macOS Docker Desktop requires a separately configured XQuartz display socket; without one, the container remains headless because this setup intentionally has no noVNC fallback.

