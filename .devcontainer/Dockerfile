FROM ros:humble

SHELL ["/bin/bash", "-c"]


# Add vscode user with same UID and GID as your host system
# (copied from https://code.visualstudio.com/remote/advancedcontainers/add-nonroot-user#_creating-a-nonroot-user)
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo \
    && echo $USERNAME ALL=\(root\) NOPASSWD:ALL > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME


# Basic development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

    # TurtleBot3 packages
RUN apt-get update && apt-get install -y \
    ros-humble-turtlebot3 \
    ros-humble-turtlebot3-simulations \
    && rm -rf /var/lib/apt/lists/*


RUN apt-get update && apt-get install -y \
    x11-apps \
    mesa-utils \
    libgl1-mesa-dri \
    libglx-mesa0 \
    libegl1 \
    && rm -rf /var/lib/apt/lists/*
# ROS 2 desktop packages:
# Includes RViz2 and other desktop tools.
RUN apt-get update && apt-get install -y \
    ros-humble-desktop \
    && rm -rf /var/lib/apt/lists/*

# Source ROS automatically for every bash shell
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

WORKDIR /workspaces/warrior

# Switch from root to user
USER $USERNAME
