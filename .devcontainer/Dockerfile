FROM ros:humble

SHELL ["/bin/bash", "-c"]

# ---------------------------------------------------------------------------
# Non-root user (matches your host UID/GID so files created in the container
# aren't owned by root on disk). 1000 is the default first-user UID on
# Linux/macOS; override at build time with --build-arg USER_UID=<your uid>
# if it differs.
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
# ROS 2 desktop tools (RViz2, etc.), TurtleBot3
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    ros-humble-desktop \
    ros-humble-turtlebot3 \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Installing Gazebo Harmonic 
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y curl lsb-release gnupg \
    && curl -fsSL https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null \
    && apt-get update \
    && apt-get install -y gz-harmonic \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# OpenGL: software rendering via llvmpipe (Mesa). Makes Gazebo/RViz2 work
# on any machine, including ones with no GPU (Mac, CI runners). Slower than
# hardware acceleration, but always works. GPU acceleration is opted into
# at *runtime* via docker-compose.override.yml (see setup.sh) — nothing
# here needs to change for that.
# ---------------------------------------------------------------------------
RUN apt-get update && apt-get install -y \
    mesa-utils \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libegl1 \
    x11-apps \
    && rm -rf /var/lib/apt/lists/*

# Source ROS for every shell. Deliberately NOT exporting DISPLAY or
# LIBGL_ALWAYS_SOFTWARE here — those are runtime-overridable via ENV below
# instead. A value exported from .bashrc would re-clobber whatever
# docker-compose's `environment:` block sets, since .bashrc runs *after*
# a process already has its correct environment.
RUN echo "source /opt/ros/humble/setup.bash" >> /home/$USERNAME/.bashrc \
    && chown $USER_UID:$USER_GID /home/$USERNAME/.bashrc

# Software-rendering defaults. docker-compose.override.yml (written by
# setup.sh) supplies the host display socket and repeats these settings at
# container-creation time.
ENV TURTLEBOT3_MODEL=burger
ENV DISPLAY=:1
ENV LIBGL_ALWAYS_SOFTWARE=1
# Entrypoint must be copied and made executable while still root — once
# USER switches to a non-root account, this user has no write access to
# /usr/local/bin, so this block must come BEFORE the USER instruction.
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

WORKDIR /ros2_ws/src/Warrior1_2027

# Everything after this line, and every container started from this
# image, runs as $USERNAME — keep USER as the last filesystem-affecting
# instruction in the file.
USER $USERNAME

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]


##Things to add
#sudo apt update && sudo apt install nano
#