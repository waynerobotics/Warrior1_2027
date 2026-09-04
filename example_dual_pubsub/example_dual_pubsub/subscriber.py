"""Subscribe to messages on the chatter topic."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MinimalSubscriber(Node):
    """Log messages received from the chatter topic."""

    def __init__(self):
        """Initialize the subscriber node."""
        super().__init__('minimal_subscriber')
        self.subscription = self.create_subscription(
            String,
            'chatter',
            self.listener_callback,
            10)
        self.subscription

    def listener_callback(self, message):
        """Log a received message."""
        self.get_logger().info('I heard: "%s"' % message.data)


def main(args=None):
    """Run the subscriber node."""
    rclpy.init(args=args)
    node = MinimalSubscriber()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
