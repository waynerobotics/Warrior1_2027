#!/bin/bash
set -e

source /opt/ros/humble/setup.bash

if [ -f "/home/vscode/ros2_ws/install/setup.bash" ]; then
  source "/home/vscode/ros2_ws/install/setup.bash"
fi

exec "$@"
