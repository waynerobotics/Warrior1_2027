FROM ros:humble

SHELL ["/bin/bash", "-c"]

# ---------------------------------------------------------------------------
# Non-root user (matches your host UID/GID so files created in the container
# aren't owned by root on disk). 1000 is the default first-user UID on
# Linux/macOS; if a teammate's host UID differs they can override it at
# build time with --build-arg USER_UID=<their uid>, or devcontainer.json's
# updateRemoteUserUID feature can do it automatically.
# ---------------------------------------------------------------------------
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Basic dev tools
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# ROS 2 desktop tools (RViz2, etc.), TurtleBot3, and modern Gazebo (ros-gz)
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    ros-humble-desktop \
    ros-humble-turtlebot3 \
    ros-humble-ros-gz \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# OpenGL: software rendering via llvmpipe (Mesa). This is the piece that
# makes Gazebo/RViz2 work identically on every machine, including ones with
# no GPU at all (e.g. a Mac under Docker Desktop, or a CI runner). It's
# slower than hardware acceleration, but it *always works*. Members who want
# GPU acceleration can opt in later (see devcontainer.json comments).
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    mesa-utils \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libegl1 \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Virtual display + browser-based VNC (noVNC). This is what lets every
# platform (Linux/Windows/macOS) see GUI apps the same way: open
# http://localhost:6080 in a browser. No host X server, no XQuartz, no
# VcXsrv, no DISPLAY env-var juggling required.
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    xvfb \
    x11vnc \
    fluxbox \
    novnc \
    websockify \
    supervisor \
    && rm -rf /var/lib/apt/lists/*

COPY .devcontainer/supervisord.conf /etc/supervisor/conf.d/gui.conf
RUN mkdir -p /var/log/supervisor

# Auto-source ROS + sane defaults for every shell (works for both the login
# shell and the ones VS Code spawns for its integrated terminal)
RUN echo "source /opt/ros/humble/setup.bash" >> /home/$USERNAME/.bashrc \
    && echo "export TURTLEBOT3_MODEL=burger" >> /home/$USERNAME/.bashrc \
    && echo "export LIBGL_ALWAYS_SOFTWARE=1" >> /home/$USERNAME/.bashrc \
    && echo "export DISPLAY=:1" >> /home/$USERNAME/.bashrc \
    && chown $USER_UID:$USER_GID /home/$USERNAME/.bashrc

WORKDIR /workspaces/warrior

USER $USERNAME
