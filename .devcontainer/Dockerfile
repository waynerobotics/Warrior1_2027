FROM ros:humble

SHELL ["/bin/bash", "-c"]

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# ---------------------------------------------------------------------------
# System setup
# ---------------------------------------------------------------------------

RUN groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y \
        sudo \
        curl \
        lsb-release \
        gnupg \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    \
    # Gazebo package repository
    && curl -fsSL https://packages.osrfoundation.org/gazebo.gpg \
        --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" \
        | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null \
    \
    && apt-get update \
    && apt-get install -y \
        build-essential \
        cmake \
        git \
        openssh-client \
        nano \
        python3-pip \
        python3-colcon-common-extensions \
        python3-rosdep \
        ros-humble-desktop \
        gz-harmonic \
        mesa-utils \
        libgl1-mesa-dri \
        libglx-mesa0 \
        libegl1 \
        x11-apps \
    \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# ROS environment
# ---------------------------------------------------------------------------

RUN echo "source /opt/ros/humble/setup.bash" >> /etc/bash.bashrc \
    && echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

ENV TURTLEBOT3_MODEL=burger
ENV DISPLAY=:1
ENV LIBGL_ALWAYS_SOFTWARE=1

# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------

COPY entrypoint.sh /usr/local/bin/entrypoint.sh

RUN chmod 755 /usr/local/bin/entrypoint.sh

# ---------------------------------------------------------------------------
# Workspace
# ---------------------------------------------------------------------------

WORKDIR /ros2_ws

RUN mkdir -p /ros2_ws/src/Warrior1_2027 \
    && chown -R $USER_UID:$USER_GID /ros2_ws

# Copy the repository into the image.
#
# This assumes your Docker build context contains:
#
#   Warrior1_2027/
#       src/
#           warrior_description/
#           warrior_bringup/
#           ...
#
COPY --chown=$USERNAME:$USERNAME . /ros2_ws/src/Warrior1_2027/

WORKDIR /ros2_ws

# ---------------------------------------------------------------------------
# rosdep
# ---------------------------------------------------------------------------
#
# Update the rosdep database, then inspect all package.xml files in src/
# and install their declared dependencies.
#
# --from-paths src
#     Search all packages under src/
#
# --ignore-src
#     Do not try to install packages that are themselves present in src/
#
# -r
#     Continue resolving dependencies even if one dependency cannot be found
#
# -y
#     Automatically answer yes to apt installation prompts
#
RUN source /opt/ros/humble/setup.bash \
    && rosdep init 2>/dev/null || true \
    && rosdep update \
    && rosdep install \
        --from-paths src \
        --ignore-src \
        -r \
        -y

# ---------------------------------------------------------------------------
# Build workspace
# ---------------------------------------------------------------------------

RUN source /opt/ros/humble/setup.bash \
    && colcon build

# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------

USER $USERNAME

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

CMD ["/bin/bash"]