"""
Check that a running Warrior simulation works, whichever simulator it is.

Start a sim first (any of `pixi run sim-headless`, `pixi run sim-isaac`,
`pixi run sim-mock`), then in another terminal:

    pixi run sim-check

It waits for the topics every simulator must provide, measures their rates,
then drives the robot forward and checks that /odom follows. Prints a
PASS/FAIL table and exits non-zero on failure, so it can be scripted.
"""

import argparse
import math
import sys
import time

from geometry_msgs.msg import TwistStamped
from nav_msgs.msg import Odometry
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.utilities import remove_ros_args
from rosgraph_msgs.msg import Clock
from sensor_msgs.msg import Imu, JointState, LaserScan

# topic -> (type, minimum Hz, needed in mock mode)
TOPICS = {
    '/clock': (Clock, 20.0, False),
    '/joint_states': (JointState, 20.0, True),
    '/odom': (Odometry, 20.0, True),
    '/scan': (LaserScan, 5.0, False),
    '/imu': (Imu, 50.0, False),
}
ISAAC_TOPIC = '/isaac_joint_states'


class SimCheck(Node):

    def __init__(self, topics):
        super().__init__('warrior_sim_check')
        self.stamps = {t: [] for t in topics}
        self.odom = None
        for topic, msg_type in topics.items():
            self.create_subscription(
                msg_type, topic, self._recorder(topic), qos_profile_sensor_data)
        self.cmd_pub = self.create_publisher(TwistStamped, '/cmd_vel', 10)

    def _recorder(self, topic):
        def callback(msg):
            self.stamps[topic].append(time.monotonic())
            if topic == '/odom':
                self.odom = msg
        return callback

    def spin_for(self, seconds, every=None):
        end = time.monotonic() + seconds
        while time.monotonic() < end:
            rclpy.spin_once(self, timeout_sec=0.02)
            if every:
                every()

    def rate(self, topic, since):
        n = len([s for s in self.stamps[topic] if s >= since])
        return n / (time.monotonic() - since)

    def drive(self, speed):
        msg = TwistStamped()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = 'base_link'
        msg.twist.linear.x = speed
        self.cmd_pub.publish(msg)


def odom_pose(node):
    """Return (x, y, yaw) from the latest /odom message."""
    p = node.odom.pose.pose.position
    q = node.odom.pose.pose.orientation
    yaw = math.atan2(2 * (q.w * q.z + q.x * q.y), 1 - 2 * (q.y * q.y + q.z * q.z))
    return p.x, p.y, yaw


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument('--timeout', type=float, default=120.0,
                        help='seconds to wait for the sim to come up (Isaac is slow)')
    parser.add_argument('--speed', type=float, default=0.3, help='m/s for the drive test')
    parser.add_argument('--drive-time', type=float, default=5.0, help='seconds to drive')
    args = parser.parse_args(remove_ros_args(argv or sys.argv)[1:])

    rclpy.init(args=argv)
    node = SimCheck({t: spec[0] for t, spec in TOPICS.items()} | {ISAAC_TOPIC: JointState})
    results = []

    def check(name, ok, detail):
        results.append((name, ok, detail))
        print(f"  {'PASS' if ok else 'FAIL'}  {name:<28} {detail}", flush=True)

    try:
        print(f'Waiting up to {args.timeout:.0f} s for /odom ...', flush=True)
        deadline = time.monotonic() + args.timeout
        while node.odom is None and time.monotonic() < deadline:
            node.spin_for(0.5)
        if node.odom is None:
            check('/odom received', False,
                  'nothing in time: are the controllers active? '
                  '(ros2 control list_controllers)')
            return 1

        start = time.monotonic()
        node.spin_for(3.0)
        mock = not node.stamps['/clock']
        isaac = bool(node.stamps[ISAAC_TOPIC])
        mode = 'mock' if mock else ('isaac' if isaac else 'gazebo')
        print(f'Simulator looks like: {mode}', flush=True)

        for topic, (_, min_hz, in_mock) in TOPICS.items():
            if mock and not in_mock:
                continue
            hz = node.rate(topic, start)
            check(f'{topic} rate', hz >= min_hz, f'{hz:6.1f} Hz (want >= {min_hz:g})')
        if isaac:
            hz = node.rate(ISAAC_TOPIC, start)
            check(f'{ISAAC_TOPIC} rate', hz >= 20.0, f'{hz:6.1f} Hz (want >= 20)')

        x0, y0, yaw0 = odom_pose(node)
        print(f'Driving forward at {args.speed} m/s for {args.drive_time:g} s ...', flush=True)
        node.spin_for(args.drive_time, every=lambda: node.drive(args.speed))
        node.drive(0.0)
        node.spin_for(1.0, every=lambda: node.drive(0.0))
        x1, y1, _ = odom_pose(node)
        # Split the motion into along / across the robot's starting heading.
        forward = (x1 - x0) * math.cos(yaw0) + (y1 - y0) * math.sin(yaw0)
        sideways = -(x1 - x0) * math.sin(yaw0) + (y1 - y0) * math.cos(yaw0)
        # Sims can run below real time, so only require a third of the ideal distance.
        want = args.speed * args.drive_time / 3
        check('odom moved forward', forward >= want,
              f'{forward:+.2f} m (want >= {want:.2f})')
        check('drove straight', abs(sideways) < 0.25 * max(abs(forward), 0.01),
              f'sideways drift {sideways:+.2f} m')
    finally:
        node.destroy_node()
        rclpy.try_shutdown()

    failed = [name for name, ok, _ in results if not ok]
    print('\nRESULT:', 'PASS' if not failed else f"FAIL ({', '.join(failed)})", flush=True)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
