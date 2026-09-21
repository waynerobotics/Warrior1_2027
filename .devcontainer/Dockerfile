FROM ros:humble

SHELL ["/bin/bash", "-c"]

ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID

# ---------------------------------------------------------------------------
# Consolidated Setup & Installations
# 1. Sets up the non-root user
# 2. Installs prerequisites for the Gazebo repository
# 3. Adds the Gazebo repository
# 4. Installs all dev tools, ROS desktop, Gazebo, and OpenGL in one step
# ---------------------------------------------------------------------------
RUN groupadd --gid $USER_GID $USERNAME \
    && useradd -s /bin/bash --uid $USER_UID --gid $USER_GID -m $USERNAME \
    && apt-get update \
    && apt-get install -y sudo curl lsb-release gnupg \
    && echo "$USERNAME ALL=(root) NOPASSWD:ALL" > /etc/sudoers.d/$USERNAME \
    && chmod 0440 /etc/sudoers.d/$USERNAME \
    && curl -fsSL https://packages.osrfoundation.org/gazebo.gpg --output /usr/share/keyrings/pkgs-osrf-archive-keyring.gpg \
    && echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/pkgs-osrf-archive-keyring.gpg] https://packages.osrfoundation.org/gazebo/ubuntu-stable $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/gazebo-stable.list > /dev/null \
    && apt-get update \
    && apt-get install -y \
        build-essential \
        cmake \
        git \
        openssh-client \
        nano \
        # vim \
        # htop \
        # tree \
        # wget \
        python3-pip \
        python3-colcon-common-extensions \
        python3-rosdep \
        ros-humble-desktop \
        ros-humble-turtlebot3 \
        gz-harmonic \
        mesa-utils \
        libgl1-mesa-dri \
        libglx-mesa0 \
        libegl1 \
        x11-apps \
    && rm -rf /var/lib/apt/lists/*

# ---------------------------------------------------------------------------
# Shell configuration and Environment Variables
# ---------------------------------------------------------------------------
RUN echo "source /opt/ros/humble/setup.bash" >> /etc/bash.bashrc \
    && echo "source /opt/ros/humble/setup.bash" >> /root/.bashrc

ENV TURTLEBOT3_MODEL=burger
ENV DISPLAY=:1
ENV LIBGL_ALWAYS_SOFTWARE=1

# ---------------------------------------------------------------------------
# Entrypoint and Workspace Setup
# ---------------------------------------------------------------------------
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod 755 /usr/local/bin/entrypoint.sh

WORKDIR /ros2_ws
RUN mkdir -p /ros2_ws/src/Warrior1_2027 \
    && chown -R $USER_UID:$USER_GID /ros2_ws
WORKDIR /ros2_ws/src/Warrior1_2027

USER $USERNAME

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["/bin/bash"]