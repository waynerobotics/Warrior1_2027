import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch_ros.actions import Node
from launch.substitutions import Command


def generate_launch_description():

    description_pkg = get_package_share_directory('warrior1_description')

    xacro_file = os.path.join(
        description_pkg,
        'urdf',
        'warrior.urdf'
    )

    rviz2_config = os.path.join(
        description_pkg,
        'rviz2',
        'warrior_display.rviz'
    )

    robot_description = Command([
        'xacro ',
        xacro_file
    ])

    robot_state_publisher = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[
            {
                'robot_description': robot_description
            }
        ],
        output='screen'
    )

    rviz = Node(
        package='rviz2',
        executable='rviz2',
        output='screen',
        arguments=[
            '-d',
            rviz2_config,
        ]
    )

    return LaunchDescription([
        robot_state_publisher,
        rviz
    ])