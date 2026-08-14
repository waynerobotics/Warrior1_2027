FROM ros:humble

SHELL ["/bin/bash", "-c"]

# Basic development tools
RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    git \
    python3-pip \
    python3-colcon-common-extensions \
    python3-rosdep \
    && rm -rf /var/lib/apt/lists/*

# ROS 2 desktop packages:
# Includes RViz2 and other desktop tools.
RUN apt-get update && apt-get install -y \
    ros-humble-desktop \
    && rm -rf /var/lib/apt/lists/*

# Source ROS automatically for every bash shell
RUN echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

WORKDIR /workspaces/warrior