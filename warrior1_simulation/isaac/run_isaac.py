"""
Run the Warrior in NVIDIA Isaac Sim (written against the 6.2 API).

This script is executed by Isaac Sim's own Python interpreter (``python.sh``
from an Isaac Sim install, or the Python of a ``pip install isaacsim``),
NOT by the pixi ROS 2 environment. Start it through ``run_isaac.sh``, which
sets up a clean environment, or through
``ros2 launch warrior1_bringup sim.launch.py simulator:=isaac``.

Nothing about the robot is hard-coded here. Everything is derived from the
URDF that ``warrior1_description`` generates, the same URDF Gazebo uses:

* links, joints, masses, inertias, geometry   -> Isaac's URDF importer
* ``<ros2_control>`` velocity joints          -> wheel velocity drives, driven over
  ``/isaac_joint_commands`` by ros2_control's TopicBasedSystem
* ``<gazebo reference=..><sensor>`` blocks     -> equivalent Isaac sensors that
  publish on the same ROS topics and frame ids
* ``<gazebo reference=..><mu1>`` friction      -> PhysX physics materials

The URDF is read from ``--urdf FILE`` or, if not given, from the
``/robot_description`` topic published by robot_state_publisher (this lets
Isaac run on a different machine from the rest of the ROS stack).
"""

import argparse
import math
import os
from pathlib import Path
import signal
import sys
import tempfile
import time

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]
# robot_model.py is plain Python (stdlib only) shared with the ROS launch files.
sys.path.insert(0, str(HERE.parent))
from warrior1_simulation.robot_model import RobotModel  # noqa: E402, I100

GRAPH_PATH = '/World/WarriorROS2Graph'
ROBOT_PATH = '/World/warrior'
JOINT_STATES_TOPIC = 'isaac_joint_states'
JOINT_COMMANDS_TOPIC = 'isaac_joint_commands'
# Angular velocity drive gain. Isaac drives are in degrees, so this is
# N*m per (deg/s); high enough that the wheel tracks the commanded velocity
# until it hits the effort limit from the URDF.
WHEEL_DRIVE_DAMPING = 1.0e3


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__.strip().split('\n')[0])
    parser.add_argument('--urdf', help='URDF file. Default: read /robot_description')
    parser.add_argument('--world', default='',
                        help='USD environment to load. Default: ground plane + walls')
    parser.add_argument('--arena-size', type=float, default=10.0,
                        help='Side length (m) of the walls around the default world; 0 = none. '
                             'Keep it inside the lidar range or /scan is not published.')
    parser.add_argument('--headless', action='store_true', help='No GUI window')
    parser.add_argument('--livestream', action='store_true',
                        help='Stream the GUI over WebRTC (use with --headless); connect with '
                             'the Isaac Sim WebRTC Streaming Client')
    parser.add_argument('--physics-hz', type=float, default=100.0,
                        help='Physics rate. Should be >= the fastest sensor rate (IMU).')
    parser.add_argument('--spawn', type=float, nargs=3, default=(0.0, 0.0, 0.0),
                        metavar=('X', 'Y', 'Z'),
                        help='Spawn position of base_link. Z is added to the wheel radius.')
    parser.add_argument('--no-realtime', action='store_true',
                        help='Run as fast as possible instead of pacing to wall-clock time')
    parser.add_argument('--description-timeout', type=float, default=60.0,
                        help='Seconds to wait for /robot_description when --urdf is not given')
    args, _unknown = parser.parse_known_args()
    return args


args = parse_args()

from isaacsim import SimulationApp  # noqa: E402, I100

simulation_app = SimulationApp({
    'headless': args.headless,
    'hide_ui': False,
    'width': 1280,
    'height': 720,
})

# Isaac modules can only be imported once SimulationApp exists.
import isaacsim.core.experimental.utils.app as app_utils  # noqa: E402, I100
import isaacsim.core.experimental.utils.stage as stage_utils  # noqa: E402, I100

app_utils.enable_extension('isaacsim.ros2.bridge')
app_utils.enable_extension('isaacsim.asset.importer.urdf')
if args.livestream:
    simulation_app.set_setting('/app/window/drawMouse', True)
    app_utils.enable_extension('omni.kit.livestream.app')
simulation_app.update()

import carb  # noqa: E402, I100
from isaacsim.asset.importer.urdf import URDFImporter, URDFImporterConfig  # noqa: E402, I100
from isaacsim.core.experimental.objects import Cube, GroundPlane  # noqa: E402, I100
from isaacsim.core.simulation_manager import SimulationManager  # noqa: E402, I100
from isaacsim.sensors.experimental.physics import IMU  # noqa: E402, I100
from isaacsim.sensors.experimental.rtx import Lidar, LidarSensor  # noqa: E402, I100
import omni.graph.core as og  # noqa: E402, I100
from pxr import (  # noqa: E402, I100
    Gf, PhysxSchema, Sdf, Usd, UsdGeom, UsdLux, UsdPhysics, UsdShade)
import usdrt.Sdf  # noqa: E402, I100


def log(msg):
    print(f'[warrior_isaac] {msg}', flush=True)
    carb.log_info(msg)


# --------------------------------------------------------------------------
# Robot description
# --------------------------------------------------------------------------
def fetch_robot_description(timeout):
    """Read the URDF from the latched /robot_description topic."""
    import rclpy
    from rclpy.qos import DurabilityPolicy, QoSProfile, ReliabilityPolicy
    from std_msgs.msg import String

    rclpy.init()
    node = rclpy.create_node('warrior_isaac_description_reader')
    qos = QoSProfile(depth=1, durability=DurabilityPolicy.TRANSIENT_LOCAL,
                     reliability=ReliabilityPolicy.RELIABLE)
    received = {}
    node.create_subscription(String, '/robot_description',
                             lambda msg: received.setdefault('urdf', msg.data), qos)
    log(f'waiting up to {timeout:.0f}s for /robot_description '
        f'(ROS_DOMAIN_ID={os.environ.get("ROS_DOMAIN_ID", "0")}) ...')
    deadline = time.monotonic() + timeout
    while 'urdf' not in received and time.monotonic() < deadline:
        rclpy.spin_once(node, timeout_sec=0.2)
        simulation_app.update()
    node.destroy_node()
    rclpy.shutdown()
    if 'urdf' not in received:
        raise RuntimeError('no /robot_description received. Is '
                           '"ros2 launch warrior1_bringup sim.launch.py simulator:=isaac" '
                           'running on the same ROS_DOMAIN_ID?')
    return received['urdf']


def repo_package_paths():
    """Map ROS package names in this repo to their source dirs (for package:// URIs)."""
    import xml.etree.ElementTree as ET

    packages = []
    for package_xml in REPO_ROOT.glob('*/package.xml'):
        name = ET.parse(package_xml).getroot().findtext('name')
        if name:
            packages.append({'name': name.strip(), 'path': str(package_xml.parent)})
    return packages


def import_robot(urdf_xml, model, work_dir):
    """Convert the URDF to USD with Isaac's importer and return the USD file."""
    # Fixed name: the URDF may come from the network (/robot_description), so
    # never build a path from its contents.
    urdf_file = os.path.join(work_dir, 'robot.urdf')
    massless = model.massless_links()
    if massless:
        # Without this the importer makes massless links (base_link) plain
        # Xforms and the wheels end up jointed to the world.
        log(f'adding negligible inertia to massless links for import: {massless}')
        urdf_xml = model.urdf_with_inertials()
    with open(urdf_file, 'w', encoding='utf-8') as f:
        f.write(urdf_xml)
    config = URDFImporterConfig()
    config.urdf_path = urdf_file
    config.usd_path = os.path.join(work_dir, 'usd')
    # Keep sensor/caster links as separate bodies so sensors can attach to them.
    config.merge_fixed_joints = False
    config.fix_base = False
    config.collision_from_visuals = False
    config.allow_self_collision = False
    config.ros_package_paths = repo_package_paths()
    usd_file = URDFImporter(config).import_urdf()
    log(f'imported {urdf_file} -> {usd_file}')
    return usd_file


# --------------------------------------------------------------------------
# Stage helpers
# --------------------------------------------------------------------------
def iter_prims(root):
    return iter(Usd.PrimRange(root))


def find_link_prim(root, link_name):
    """Find the rigid body prim the importer created for a URDF link."""
    fallback = None
    for prim in iter_prims(root):
        if prim.GetName() != link_name:
            continue
        if prim.HasAPI(UsdPhysics.RigidBodyAPI):
            return prim
        fallback = fallback or prim
    if fallback is None:
        raise RuntimeError(f'link {link_name!r} not found under {root.GetPath()}')
    return fallback


def find_joint_prim(root, joint_name):
    for prim in iter_prims(root):
        if prim.GetName() == joint_name and prim.IsA(UsdPhysics.Joint):
            return prim
    raise RuntimeError(f'joint {joint_name!r} not found under {root.GetPath()}')


def find_articulation_root(root):
    for prim in iter_prims(root):
        if prim.HasAPI(UsdPhysics.ArticulationRootAPI):
            return prim
    return root


def add_arena_walls(size, height=0.5, thickness=0.1):
    """
    Square of walls around the origin for the default world.

    Isaac's RTX LaserScan publisher sends nothing for a scan with zero
    returns, so on a bare ground plane a 2D lidar never publishes /scan
    (Gazebo would publish all-inf ranges). Walls inside the lidar's range
    keep /scan flowing and give Nav2/SLAM something to see.
    """
    if size <= 0:
        return
    half = size / 2.0
    z = height / 2.0
    paths = [f'/World/Arena/wall_{side}' for side in ('north', 'south', 'east', 'west')]
    Cube(
        paths,
        sizes=1.0,
        positions=[[half, 0.0, z], [-half, 0.0, z], [0.0, half, z], [0.0, -half, z]],
        scales=[[thickness, size, height], [thickness, size, height],
                [size, thickness, height], [size, thickness, height]],
    )
    stage = stage_utils.get_current_stage()
    for path in paths:  # static colliders: the robot can bump into them
        UsdPhysics.CollisionAPI.Apply(stage.GetPrimAtPath(path))
    log(f'default world: ground plane + {size:g} m square of walls '
        '(--arena-size 0 to disable)')


def build_world(stage):
    stage_utils.set_stage_units(meters_per_unit=1.0)
    UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.z)
    if not any(p.IsA(UsdPhysics.Scene) for p in stage.Traverse()):
        scene = UsdPhysics.Scene.Define(stage, Sdf.Path('/World/PhysicsScene'))
        scene.CreateGravityDirectionAttr().Set(Gf.Vec3f(0.0, 0.0, -1.0))
        scene.CreateGravityMagnitudeAttr().Set(9.81)
    if args.world:
        stage_utils.add_reference_to_stage(args.world, '/World/Environment')
        log(f'loaded environment {args.world}')
    else:
        GroundPlane('/World/GroundPlane', positions=[0.0, 0.0, 0.0])
        add_arena_walls(args.arena_size)
    light = UsdLux.DistantLight.Define(stage, Sdf.Path('/World/Sun'))
    light.CreateIntensityAttr(2500.0)
    UsdGeom.Xformable(light.GetPrim()).AddRotateXYZOp().Set(Gf.Vec3f(-30.0, 20.0, 0.0))


def add_robot(stage, usd_file, model):
    prim = stage_utils.add_reference_to_stage(usd_file, ROBOT_PATH)
    variant_sets = prim.GetVariantSets()
    if variant_sets.HasVariantSet('Physics'):
        variant_sets.GetVariantSet('Physics').SetVariantSelection('physx')
    # base_link sits on the wheel axle, so lift it by the wheel radius.
    _, wheel_radius = model.wheel_kinematics('left_wheel_joint', 'right_wheel_joint')
    x, y, z = args.spawn
    xform = UsdGeom.XformCommonAPI(prim)
    xform.SetTranslate(Gf.Vec3d(x, y, z + wheel_radius + 0.005))
    return prim


def configure_wheel_drives(robot_prim, model):
    """Velocity-drive every joint that ros2_control commands by velocity."""
    for joint_name, interfaces in model.ros2_control_joints().items():
        if 'velocity' not in interfaces:
            log(f'joint {joint_name}: interfaces {interfaces} not supported yet, skipped')
            continue
        joint = model.joints[joint_name]
        prim = find_joint_prim(robot_prim, joint_name)
        drive = UsdPhysics.DriveAPI.Apply(prim, 'angular')
        drive.CreateTypeAttr().Set('force')
        drive.CreateStiffnessAttr().Set(0.0)
        drive.CreateDampingAttr().Set(WHEEL_DRIVE_DAMPING)
        drive.CreateTargetVelocityAttr().Set(0.0)
        if joint.effort:
            drive.CreateMaxForceAttr().Set(joint.effort)
        if joint.velocity:
            PhysxSchema.PhysxJointAPI.Apply(prim).CreateMaxJointVelocityAttr().Set(
                math.degrees(joint.velocity))
        log(f'joint {joint_name}: velocity drive, max effort {joint.effort} N*m')


def apply_friction(stage, robot_prim, model):
    """Turn the URDF's <gazebo><mu1/mu2> values into PhysX materials."""
    for link, (mu1, mu2) in model.link_friction().items():
        material_path = Sdf.Path(f'/World/PhysicsMaterials/{link}')
        material = UsdShade.Material.Define(stage, material_path)
        physics = UsdPhysics.MaterialAPI.Apply(material.GetPrim())
        physics.CreateStaticFrictionAttr().Set(max(mu1, mu2))
        physics.CreateDynamicFrictionAttr().Set(min(mu1, mu2))
        physics.CreateRestitutionAttr().Set(0.0)
        # Gazebo combines friction with min(); do the same so a near-zero
        # caster really slides on any floor.
        physx = PhysxSchema.PhysxMaterialAPI.Apply(material.GetPrim())
        physx.CreateFrictionCombineModeAttr().Set('min')
        link_prim = find_link_prim(robot_prim, link)
        UsdShade.MaterialBindingAPI.Apply(link_prim).Bind(
            material, UsdShade.Tokens.weakerThanDescendants, 'physics')
        log(f'link {link}: friction mu1={mu1} mu2={mu2}')


# --------------------------------------------------------------------------
# Sensors + ROS 2 graph
# --------------------------------------------------------------------------
def create_sensors(robot_prim, model, physics_hz):
    """
    Create Isaac sensors matching the URDF's Gazebo sensors.

    Returns (imus, lidars): lists of (Sensor, prim path) / (Sensor, Lidar).
    """
    imus, lidars = [], []
    for sensor in model.sensors():
        link_path = find_link_prim(robot_prim, sensor.link).GetPath().pathString
        path = f'{link_path}/{sensor.name}'
        xyz = list(sensor.params.get('pose', (0.0,) * 6)[:3])
        if sensor.kind == 'imu':
            IMU.create(path, translations=[xyz])
            if sensor.update_rate and sensor.update_rate > physics_hz:
                log(f'IMU {sensor.name}: {sensor.update_rate} Hz requested but physics runs at '
                    f'{physics_hz} Hz; raise --physics-hz')
            imus.append((sensor, path))
        elif sensor.kind == 'lidar':
            if sensor.params.get('vertical_samples', 1) > 1:
                config = 'Example_Rotary'
            else:
                config = 'Example_Rotary_2D'
            lidar = Lidar.create(
                path=path,
                config=config,
                tick_rate=sensor.update_rate or 10.0,
                translations=[xyz],
                attributes={
                    'omni:sensor:Core:nearRangeM': float(sensor.params['range_min']),
                    'omni:sensor:Core:farRangeM': float(sensor.params['range_max']),
                },
            )
            lidars.append((sensor, lidar))
        else:
            log(f'sensor {sensor.name}: type {sensor.gz_type!r} has no Isaac mapping yet, '
                'skipped (add one in create_sensors)')
        log(f'sensor {sensor.name} ({sensor.kind}) on {sensor.link} -> {sensor.topic}')
    return imus, lidars


def build_ros_graph(articulation_path, imus):
    """Clock, joint state/command bridge for ros2_control, and IMU publishers."""
    keys = og.Controller.Keys
    nodes = [
        ('OnPlaybackTick', 'omni.graph.action.OnPlaybackTick'),
        ('Context', 'isaacsim.ros2.bridge.ROS2Context'),
        ('ReadSimTime', 'isaacsim.core.nodes.IsaacReadSimulationTime'),
        ('PublishClock', 'isaacsim.ros2.bridge.ROS2PublishClock'),
        ('ReadJointState', 'isaacsim.sensors.physics.IsaacReadJointState'),
        ('PublishJointState', 'isaacsim.ros2.bridge.ROS2PublishJointState'),
        ('SubscribeJointState', 'isaacsim.ros2.bridge.ROS2SubscribeJointState'),
        ('ArticulationController', 'isaacsim.core.nodes.IsaacArticulationController'),
    ]
    connect = [
        ('OnPlaybackTick.outputs:tick', 'PublishClock.inputs:execIn'),
        ('Context.outputs:context', 'PublishClock.inputs:context'),
        ('ReadSimTime.outputs:simulationTime', 'PublishClock.inputs:timeStamp'),
        # Isaac -> ROS: joint states for topic_based_ros2_control
        ('OnPlaybackTick.outputs:tick', 'ReadJointState.inputs:execIn'),
        ('ReadJointState.outputs:execOut', 'PublishJointState.inputs:execIn'),
        ('Context.outputs:context', 'PublishJointState.inputs:context'),
        ('ReadSimTime.outputs:simulationTime', 'PublishJointState.inputs:timeStamp'),
    ]
    for field in ('jointNames', 'jointPositions', 'jointVelocities', 'jointEfforts',
                  'jointDofTypes', 'stageMetersPerUnit', 'sensorTime'):
        connect.append((f'ReadJointState.outputs:{field}', f'PublishJointState.inputs:{field}'))
    connect += [
        # ROS -> Isaac: joint commands from topic_based_ros2_control
        ('OnPlaybackTick.outputs:tick', 'SubscribeJointState.inputs:execIn'),
        ('Context.outputs:context', 'SubscribeJointState.inputs:context'),
        ('OnPlaybackTick.outputs:tick', 'ArticulationController.inputs:execIn'),
    ]
    for field in ('jointNames', 'positionCommand', 'velocityCommand', 'effortCommand'):
        dst = 'jointNames' if field == 'jointNames' else field
        connect.append((f'SubscribeJointState.outputs:{field}',
                        f'ArticulationController.inputs:{dst}'))
    values = [
        ('ReadJointState.inputs:prim', [usdrt.Sdf.Path(articulation_path)]),
        ('PublishJointState.inputs:topicName', JOINT_STATES_TOPIC),
        ('SubscribeJointState.inputs:topicName', JOINT_COMMANDS_TOPIC),
        ('ArticulationController.inputs:robotPath', articulation_path),
        ('PublishClock.inputs:topicName', 'clock'),
    ]
    for i, (sensor, prim_path) in enumerate(imus):
        read, pub = f'ReadIMU{i}', f'PublishImu{i}'
        nodes += [(read, 'isaacsim.sensors.physics.IsaacReadIMU'),
                  (pub, 'isaacsim.ros2.bridge.ROS2PublishImu')]
        connect += [
            ('OnPlaybackTick.outputs:tick', f'{read}.inputs:execIn'),
            (f'{read}.outputs:execOut', f'{pub}.inputs:execIn'),
            ('Context.outputs:context', f'{pub}.inputs:context'),
            ('ReadSimTime.outputs:simulationTime', f'{pub}.inputs:timeStamp'),
            (f'{read}.outputs:linAcc', f'{pub}.inputs:linearAcceleration'),
            (f'{read}.outputs:angVel', f'{pub}.inputs:angularVelocity'),
            (f'{read}.outputs:orientation', f'{pub}.inputs:orientation'),
        ]
        values += [
            (f'{read}.inputs:imuPrim', [usdrt.Sdf.Path(prim_path)]),
            (f'{read}.inputs:readGravity', True),
            (f'{pub}.inputs:topicName', sensor.topic.lstrip('/')),
            (f'{pub}.inputs:frameId', sensor.frame_id),
        ]
    og.Controller.edit(
        {'graph_path': GRAPH_PATH, 'evaluator_name': 'execution'},
        {keys.CREATE_NODES: nodes, keys.CONNECT: connect, keys.SET_VALUES: values},
    )


def attach_lidar_publishers(lidars):
    """
    Publish each RTX lidar with Isaac's ROS2RtxLidarHelper graph node.

    The helper reads the scan geometry from the OmniLidar prim and picks the
    right publishing backend itself. (Attaching the RtxLidarROS2PublishLaserScan
    writer directly to the sensor's render product published nothing in 6.2.)
    """
    keys = og.Controller.Keys
    sensors, nodes, connect, values = [], [], [], []
    for i, (sensor, lidar) in enumerate(lidars):
        rtx = LidarSensor(lidar)
        sensors.append(rtx)  # keep a reference so the render product stays alive
        name = f'PublishLidar{i}'
        kind = 'point_cloud' if sensor.params.get('vertical_samples', 1) > 1 else 'laser_scan'
        nodes.append((name, 'isaacsim.ros2.bridge.ROS2RtxLidarHelper'))
        # Absolute paths: these nodes join the graph built in build_ros_graph().
        connect += [(f'{GRAPH_PATH}/OnPlaybackTick.outputs:tick', f'{name}.inputs:execIn'),
                    (f'{GRAPH_PATH}/Context.outputs:context', f'{name}.inputs:context')]
        values += [(f'{name}.inputs:renderProductPath',
                    rtx.render_product.GetPath().pathString),
                   (f'{name}.inputs:topicName', sensor.topic.lstrip('/')),
                   (f'{name}.inputs:frameId', sensor.frame_id),
                   (f'{name}.inputs:type', kind)]
    if nodes:
        og.Controller.edit(GRAPH_PATH, {keys.CREATE_NODES: nodes, keys.CONNECT: connect,
                                        keys.SET_VALUES: values})
    return sensors


# --------------------------------------------------------------------------
def install_stop_handlers():
    """Make Ctrl+C / SIGTERM stop Isaac (Kit ignores them otherwise)."""
    # The main loop polls state['requested'] once state['running'] is set.
    # Before that (import, scene setup) there is nothing worth shutting down
    # cleanly, so a signal exits at once; so does a second signal, in case
    # Isaac's shutdown hangs.
    state = {'running': False, 'requested': False}

    def handler(signum, _frame):
        if state['requested'] or not state['running']:
            os._exit(128 + signum)
        log(f'{signal.Signals(signum).name} received, shutting down')
        state['requested'] = True

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)
    return state


def main():
    stop = install_stop_handlers()
    work_dir = tempfile.mkdtemp(prefix='warrior_isaac_')
    if args.urdf:
        with open(args.urdf, encoding='utf-8') as f:
            urdf_xml = f.read()
    else:
        urdf_xml = fetch_robot_description(args.description_timeout)
    model = RobotModel(urdf_xml)

    plugin, hw_params = model.ros2_control_hardware()
    if plugin != 'topic_based_ros2_control/TopicBasedSystem':
        log(f'WARNING: URDF ros2_control plugin is {plugin!r}; Isaac expects the URDF '
            'generated with sim_mode:=isaac (TopicBasedSystem)')
    for key, topic in (('joint_states_topic', JOINT_STATES_TOPIC),
                       ('joint_commands_topic', JOINT_COMMANDS_TOPIC)):
        if hw_params.get(key, '/' + topic).lstrip('/') != topic:
            log(f'WARNING: URDF {key}={hw_params[key]} but Isaac uses /{topic}')

    usd_file = import_robot(urdf_xml, model, work_dir)

    stage_utils.create_new_stage()
    stage = stage_utils.get_current_stage()
    build_world(stage)
    robot_prim = add_robot(stage, usd_file, model)
    simulation_app.update()

    configure_wheel_drives(robot_prim, model)
    apply_friction(stage, robot_prim, model)
    imus, lidars = create_sensors(robot_prim, model, args.physics_hz)
    articulation = find_articulation_root(robot_prim).GetPath().pathString
    log(f'articulation root: {articulation}')
    build_ros_graph(articulation, imus)
    simulation_app.update()

    dt = 1.0 / args.physics_hz
    SimulationManager.setup_simulation(dt=dt, device='cpu')
    simulation_app.update()
    lidar_sensors = attach_lidar_publishers(lidars)  # noqa: F841
    simulation_app.update()

    app_utils.play()
    stop['running'] = True
    log('simulation running - ROS topics: /clock /isaac_joint_states /isaac_joint_commands '
        + ' '.join(s.topic for s in model.sensors()))

    start_wall = time.monotonic()
    start_sim = SimulationManager.get_simulation_time()
    while simulation_app.is_running() and not stop['requested']:
        simulation_app.update()
        if not args.no_realtime:
            # Keep simulated time from running ahead of wall-clock time so
            # teleop and timeouts behave like on the real robot.
            sim_elapsed = SimulationManager.get_simulation_time() - start_sim
            ahead = sim_elapsed - (time.monotonic() - start_wall)
            if ahead > 0:
                time.sleep(min(ahead, 0.1))

    app_utils.stop()
    simulation_app.close()


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback

        traceback.print_exc()
        simulation_app.close()
        sys.exit(1)
