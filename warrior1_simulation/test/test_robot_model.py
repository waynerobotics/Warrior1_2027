"""Checks on the generated Warrior URDF that every simulator relies on."""

import os

from ament_index_python.packages import get_package_share_directory
import pytest
from warrior1_simulation.robot_model import gz_bridge_arguments, RobotModel
import xacro

SIM_MODES = ('gazebo', 'isaac', 'mock')
HW_PLUGINS = {
    'gazebo': 'gz_ros2_control/GazeboSimSystem',
    'isaac': 'topic_based_ros2_control/TopicBasedSystem',
    'mock': 'mock_components/GenericSystem',
}


def load(sim_mode):
    path = os.path.join(get_package_share_directory('warrior1_description'),
                        'urdf', 'warrior.urdf')
    xml = xacro.process_file(
        path, mappings={'sim_mode': sim_mode, 'controllers_file': '/tmp/controllers.yaml'}
    ).toxml()
    return RobotModel(xml)


@pytest.fixture(scope='module', params=SIM_MODES)
def model(request):
    return request.param, load(request.param)


def test_hardware_plugin_matches_sim_mode(model):
    mode, m = model
    plugin, _ = m.ros2_control_hardware()
    assert plugin == HW_PLUGINS[mode]


def test_same_joints_and_sensors_in_every_mode():
    models = [load(mode) for mode in SIM_MODES]
    joints = {tuple(sorted(m.joints)) for m in models}
    sensors = {tuple(sorted(s.name for s in m.sensors())) for m in models}
    controls = {tuple(sorted((j, tuple(i)) for j, i in m.ros2_control_joints().items()))
                for m in models}
    assert len(joints) == 1
    assert len(sensors) == 1
    assert len(controls) == 1


def test_two_velocity_controlled_wheels():
    m = load('mock')
    assert m.ros2_control_joints() == {
        'left_wheel_joint': ['velocity'],
        'right_wheel_joint': ['velocity'],
    }
    for name in ('left_wheel_joint', 'right_wheel_joint'):
        assert m.joints[name].joint_type == 'continuous'
        assert m.joints[name].effort and m.joints[name].velocity


def test_wheels_spin_about_robot_y_axis():
    """Positive wheel velocity must roll the robot forward (+x)."""
    m = load('mock')
    for name in ('left_wheel_joint', 'right_wheel_joint'):
        joint = m.joints[name]
        _, rot = m.link_pose_in_root(joint.child)
        axis = [sum(rot[i][k] * joint.axis[k] for k in range(3)) for i in range(3)]
        assert axis == pytest.approx([0.0, 1.0, 0.0], abs=1e-9)


def test_wheels_are_symmetric_and_kinematics_derived():
    m = load('mock')
    left, _ = m.link_pose_in_root('left_wheel')
    right, _ = m.link_pose_in_root('right_wheel')
    assert left[1] == pytest.approx(-right[1])
    assert left[1] > 0
    params = m.diff_drive_parameters()
    assert params['wheel_separation'] == pytest.approx(left[1] - right[1])
    assert params['wheel_radius'] == pytest.approx(m.collision_radius('left_wheel'))


def test_wheels_and_caster_touch_the_same_ground_plane():
    m = load('mock')
    bottoms = []
    for link in ('left_wheel', 'right_wheel', 'caster_wheel'):
        pos, _ = m.link_pose_in_root(link)
        bottoms.append(pos[2] - m.collision_radius(link))
    assert max(bottoms) - min(bottoms) == pytest.approx(0.0, abs=1e-6)


def test_physics_import_copy_has_no_massless_links():
    # Isaac's URDF importer drops massless links from the articulation.
    m = load('isaac')
    assert m.massless_links() == ['base_link']
    fixed = RobotModel(m.urdf_with_inertials())
    assert fixed.massless_links() == []
    assert set(fixed.joints) == set(m.joints)
    assert fixed.root_link == m.root_link
    # The original model is left alone.
    assert m.massless_links() == ['base_link']


def test_masses_are_physically_sane():
    m = load('mock')
    masses = {}
    for name, link in m.links.items():
        mass = link.find('inertial/mass')
        if mass is not None:
            masses[name] = float(mass.get('value'))
    assert max(masses, key=masses.get) == 'chassis'
    assert masses['caster_wheel'] < masses['chassis']


def test_caster_slides_and_wheels_grip():
    friction = load('mock').link_friction()
    assert friction['caster_wheel'][0] < 0.01
    assert friction['left_wheel'][0] >= 0.5
    assert friction['right_wheel'][0] >= 0.5


def test_sensors_and_gazebo_bridge():
    m = load('gazebo')
    sensors = {s.name: s for s in m.sensors()}
    assert sensors['lidar'].kind == 'lidar'
    assert sensors['lidar'].topic == '/scan'
    assert sensors['lidar'].frame_id == 'laser_frame'
    assert sensors['main_imu'].kind == 'imu'
    assert sensors['main_imu'].topic == '/imu'
    args = gz_bridge_arguments(m)
    assert '/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock' in args
    assert '/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan' in args
    assert '/imu@sensor_msgs/msg/Imu[gz.msgs.IMU' in args


def test_gazebo_mode_loads_ros2_control_plugin():
    m = load('gazebo')
    plugins = [p.get('filename') for p in m.root.findall('gazebo/plugin')]
    assert 'gz_ros2_control-system' in plugins
    assert not load('isaac').root.findall('gazebo/plugin')
