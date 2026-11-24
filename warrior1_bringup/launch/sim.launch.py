"""
Launch the Warrior in a simulator.

    ros2 launch warrior1_bringup sim.launch.py simulator:=gazebo   (default)
    ros2 launch warrior1_bringup sim.launch.py simulator:=isaac
    ros2 launch warrior1_bringup sim.launch.py simulator:=mock

Whatever the simulator, the rest of the ROS graph sees the same interface:

    /cmd_vel (geometry_msgs/TwistStamped)  ->  diff_drive_controller
    /odom, /tf (odom -> base_link)         <-  diff_drive_controller
    /joint_states, /tf (robot links)       <-  joint_state_broadcaster + robot_state_publisher
    /scan, /imu, ...                       <-  sensors declared in the URDF
    /clock                                 <-  the simulator (not in mock mode)

The robot is defined once in warrior1_description (xacro) and the controllers
once in warrior1_bringup/config/controllers.yaml; only the small
simulator-specific blocks below differ.
"""

import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    LogInfo,
    OpaqueFunction,
)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from warrior1_simulation.robot_model import gz_bridge_arguments, RobotModel
import xacro
import yaml

SIMULATORS = ('gazebo', 'isaac', 'mock')


def _truthy(value):
    return str(value).lower() in ('1', 'true', 'yes', 'on')


def _find_isaac_launcher():
    """Return the command prefix that starts Isaac Sim's Python, or None."""
    simulation_pkg = get_package_share_directory('warrior1_simulation')
    wrapper = os.path.join(simulation_pkg, 'isaac', 'run_isaac.sh')
    if os.environ.get('ISAAC_SIM_PATH') or os.environ.get('ISAAC_PYTHON'):
        return ['bash', wrapper]
    # `pixi install -e isaac` puts Isaac next to the ROS environment.
    pixi_root = os.environ.get('PIXI_PROJECT_ROOT')
    if pixi_root:
        site = os.path.join(pixi_root, '.pixi', 'envs', 'isaac', 'lib', 'python3.12',
                            'site-packages')
        if os.path.isdir(os.path.join(site, 'isaacsim')):
            return ['bash', wrapper]
    return None


def _launch_setup(context):
    simulator = LaunchConfiguration('simulator').perform(context)
    headless = _truthy(LaunchConfiguration('headless').perform(context))
    launch_isaac = _truthy(LaunchConfiguration('launch_isaac').perform(context))
    foxglove = _truthy(LaunchConfiguration('foxglove').perform(context))
    world = LaunchConfiguration('world').perform(context)
    isaac_world = LaunchConfiguration('isaac_world').perform(context)

    if simulator not in SIMULATORS:
        raise RuntimeError(f"simulator:='{simulator}' must be one of {SIMULATORS}")

    description_pkg = get_package_share_directory('warrior1_description')
    bringup_pkg = get_package_share_directory('warrior1_bringup')
    controllers_file = os.path.join(bringup_pkg, 'config', 'controllers.yaml')
    use_sim_time = simulator != 'mock'

    # ---- 1. Robot description: the single source of truth ------------------
    urdf_xml = xacro.process_file(
        os.path.join(description_pkg, 'urdf', 'warrior.urdf'),
        mappings={'sim_mode': simulator, 'controllers_file': controllers_file},
    ).toprettyxml(indent='  ')
    model = RobotModel(urdf_xml)

    # Generated files (URDF for Isaac, kinematics for the diff drive) go to a
    # per-launch temp dir so nothing generated ends up in the source tree.
    gen_dir = tempfile.mkdtemp(prefix='warrior_sim_')
    urdf_path = os.path.join(gen_dir, 'robot.urdf')
    with open(urdf_path, 'w', encoding='utf-8') as f:
        f.write(urdf_xml)

    # Wheel separation / radius come from the URDF, not from controllers.yaml
    kinematics_file = os.path.join(gen_dir, 'diff_drive_kinematics.yaml')
    with open(kinematics_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(
            {'diff_drive_controller': {'ros__parameters': model.diff_drive_parameters()}}, f)

    actions = [LogInfo(msg=f'[warrior] simulator={simulator}, generated files in {gen_dir}')]

    # ---- 2. Common to every simulator --------------------------------------
    actions.append(Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        parameters=[{'robot_description': urdf_xml, 'use_sim_time': use_sim_time}],
        output='screen',
    ))

    # One spawner activates both controllers in a single switch request.
    # (Two spawners serialize on a file lock; while one waits for a slow
    # simulator the other gives up on the lock after ~2 minutes.)
    spawner_args = ['--controller-manager', '/controller_manager',
                    '--controller-manager-timeout', '120',
                    '--activate-as-group']
    if simulator == 'isaac':
        # controller_manager runs on sim time and only cycles once Isaac
        # publishes /clock. Isaac takes from ~10 s (warm) to several minutes
        # (first start, shader cache) to get there, or is started later on
        # another machine. The switch request blocks until then, so both the
        # switch timeout (default 5 s) and the service call timeout (default
        # 10 s; a retry then fails because the controllers are already
        # active) must cover that wait.
        spawner_args += ['--switch-timeout', '900',
                         '--service-call-timeout', '900']
    actions.append(Node(
        package='controller_manager',
        executable='spawner',
        arguments=[
            *spawner_args,
            '--controller', 'joint_state_broadcaster',
            '--controller', 'diff_drive_controller',
            '--param-file', controllers_file,
            '--param-file', kinematics_file,
            '--controller-ros-args',
            '-r ~/cmd_vel:=/cmd_vel -r ~/odom:=/odom',
        ],
        output='screen',
    ))

    # ---- 3. Simulator-specific ---------------------------------------------
    if simulator == 'gazebo':
        actions += _gazebo(model, world, headless)
    else:
        # Isaac and mock: controller_manager runs as a normal ROS node. It reads
        # the URDF from /robot_description and picks the hardware plugin from
        # the <ros2_control> block (TopicBasedSystem or GenericSystem).
        actions.append(Node(
            package='controller_manager',
            executable='ros2_control_node',
            parameters=[controllers_file, {'use_sim_time': use_sim_time}],
            remappings=[('~/robot_description', '/robot_description')],
            output='screen',
        ))
    if simulator == 'isaac':
        actions += _isaac(urdf_path, isaac_world, headless, launch_isaac)

    if foxglove:
        # Same bridge settings as `pixi run foxglove` (tuned for remote links).
        actions.append(IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(bringup_pkg, 'launch', 'foxglove.launch.py')),
            launch_arguments={'use_sim_time': str(use_sim_time).lower()}.items(),
        ))
    return actions


def _gazebo(model, world, headless):
    ros_gz_sim_pkg = get_package_share_directory('ros_gz_sim')
    gz_args = '-r ' + ('-s --headless-rendering ' if headless else '') + world
    return [
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(
                os.path.join(ros_gz_sim_pkg, 'launch', 'gz_sim.launch.py')),
            launch_arguments={'gz_args': gz_args}.items(),
        ),
        Node(
            package='ros_gz_sim',
            executable='create',
            arguments=['-topic', 'robot_description', '-name', model.name, '-z', '0.06'],
            output='screen',
        ),
        # Topics come from the sensors declared in the URDF, so adding a sensor
        # in xacro is enough to get it bridged.
        Node(
            package='ros_gz_bridge',
            executable='parameter_bridge',
            arguments=gz_bridge_arguments(model),
            output='screen',
        ),
    ]


def _isaac(urdf_path, isaac_world, headless, launch_isaac):
    if not launch_isaac:
        return [LogInfo(msg=(
            '[warrior] launch_isaac:=false - start Isaac Sim yourself (on this or another '
            'machine on the same ROS_DOMAIN_ID): warrior1_simulation/isaac/run_isaac.sh'))]
    launcher = _find_isaac_launcher()
    if launcher is None:
        return [LogInfo(msg=(
            '[warrior] Isaac Sim not found: run `pixi install -e isaac`, or set ISAAC_SIM_PATH '
            '(Isaac Sim install dir) or ISAAC_PYTHON (python of a pip install), or run with '
            'launch_isaac:=false and '
            'start Isaac on another machine. ROS side is running and waiting for '
            '/isaac_joint_states.'))]
    cmd = launcher + ['--urdf', urdf_path]
    if headless:
        cmd.append('--headless')
    if isaac_world:
        cmd += ['--world', isaac_world]
    return [ExecuteProcess(cmd=cmd, output='screen', name='isaac_sim')]


def generate_launch_description():
    simulation_pkg = get_package_share_directory('warrior1_simulation')
    return LaunchDescription([
        DeclareLaunchArgument(
            'simulator', default_value='gazebo',
            description='Which simulator to use: gazebo, isaac or mock (no physics)'),
        DeclareLaunchArgument(
            'headless', default_value='false',
            description='Run the simulator without its GUI window (e.g. over SSH)'),
        DeclareLaunchArgument(
            'launch_isaac', default_value='true',
            description='simulator:=isaac only. false = only start the ROS side and let '
                        'Isaac Sim be started separately (e.g. on another machine)'),
        DeclareLaunchArgument(
            'foxglove', default_value='false',
            description='Start foxglove_bridge on port 8765 for remote viewing'),
        DeclareLaunchArgument(
            'world',
            default_value=os.path.join(simulation_pkg, 'worlds', 'empty.sdf'),
            description='Gazebo world (.sdf)'),
        DeclareLaunchArgument(
            'isaac_world', default_value='',
            description='Isaac Sim environment (.usd); empty = flat ground plane'),
        OpaqueFunction(function=_launch_setup),
    ])
