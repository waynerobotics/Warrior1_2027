#!/bin/bash
set -e

source /opt/ros/humble/setup.bash
if [ -f "/home/vscode/ros2_ws/install/setup.bash" ]; then
  source "/home/vscode/ros2_ws/install/setup.bash"
fi

if [ -d "/ros2_ws/src" ]; then
    echo "Updating rosdep and installing workspace dependencies..."
    sudo apt update
    rosdep update
    rosdep install --from-paths /ros2_ws/src --ignore-src -r -y
fi
exec "$@"
