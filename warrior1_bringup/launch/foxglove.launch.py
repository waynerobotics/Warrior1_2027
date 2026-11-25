"""
Foxglove bridge for viewing a sim (or the robot) from another machine.

    ros2 launch warrior1_bringup foxglove.launch.py              (pixi run foxglove)
    ros2 launch warrior1_bringup sim.launch.py foxglove:=true    (pixi run sim-remote)

Then connect Foxglove to ws://localhost:8765 through an SSH tunnel
(ssh -L 8765:localhost:8765 <user>@<host>).

The bridge has no authentication and lets clients publish (e.g. drive the
robot), so it only listens on localhost: only people who can SSH into the
machine can reach it. To listen on another interface on purpose, e.g. a VPN
address: ros2 launch warrior1_bringup foxglove.launch.py address:=<ip>

Tuned for slow or remote links:

* Topics that only matter on the sim machine are not offered. ros2_control
  publishes /controller_manager/statistics/* on every simulator step (about
  1000 msg/s, over 2 MB/s in Gazebo) and /clock runs at the physics rate;
  either one saturates an SSH tunnel and makes everything lag. Every other
  topic, including new sensors, is offered as usual.
* send_buffer_limit is lowered from the default 10 MB so that, on a link that
  can't keep up, the bridge drops old messages instead of queueing seconds of
  them (which shows up as large delays in Foxglove).
"""

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node

# Regex (ECMAScript): everything except these topics.
TOPIC_WHITELIST = r'^(?!/controller_manager/|/clock$|/dynamic_joint_states$).*'
# Bytes queued per client before messages are dropped. Must hold the largest
# single message (URDF, scan); keep it small so latency stays low.
SEND_BUFFER_LIMIT = 1_000_000


def foxglove_bridge_node(use_sim_time, port=8765, address='127.0.0.1'):
    """Return the foxglove_bridge node with this repo's settings."""
    return Node(
        package='foxglove_bridge',
        executable='foxglove_bridge',
        parameters=[{
            'port': port,
            'address': address,
            'use_sim_time': use_sim_time,
            'topic_whitelist': [TOPIC_WHITELIST],
            'send_buffer_limit': SEND_BUFFER_LIMIT,
        }],
        output='screen',
    )


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'use_sim_time', default_value='true',
            description='false when viewing the real robot or sim-mock'),
        DeclareLaunchArgument('port', default_value='8765'),
        DeclareLaunchArgument(
            'address', default_value='127.0.0.1',
            description='Interface to listen on (default: localhost only)'),
        foxglove_bridge_node(LaunchConfiguration('use_sim_time'),
                             LaunchConfiguration('port'),
                             LaunchConfiguration('address')),
    ])
