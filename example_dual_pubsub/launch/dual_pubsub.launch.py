"""Launch the example publisher and subscriber nodes."""

from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    """Create a launch description for both example nodes."""


    publisher_node = Node(
        package='example_dual_pubsub',
        executable='publisher',
        name='minimal_publisher',
        output='screen'
    )

    subscriber_node = Node(
        package='example_dual_pubsub',
        executable='subscriber',
        name='minimal_subscriber',
        output='screen'
    )
    return LaunchDescription([
        publisher_node,
        subscriber_node,
    ])
