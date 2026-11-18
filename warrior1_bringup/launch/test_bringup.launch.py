from launch import LaunchDescription
from launch_ros.actions import Node


# Sanity check that the ROS 2 environment works (talker/listener demo).
def generate_launch_description():
    return LaunchDescription([
        Node(
            package='demo_nodes_cpp',
            executable='talker',
            name='talker',
            output='screen',
        ),
        Node(
            package='demo_nodes_cpp',
            executable='listener',
            name='listener',
            output='screen',
        ),
    ])
