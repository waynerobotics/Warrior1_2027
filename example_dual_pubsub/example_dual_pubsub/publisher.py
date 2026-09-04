"""Publish messages on the chatter topic."""

import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class MinimalPublisher(Node):
    """Publish an incrementing message at a fixed interval."""

    def __init__(self):
        """Initialize the publisher node."""
        super().__init__('minimal_publisher')
        self.publisher = self.create_publisher(String, 'chatter', 10)
        self.message_count = 0
        self.timer = self.create_timer(0.5, self.publish_message)

    def publish_message(self):
        """Publish the next message and log it."""
        message = String()
        message.data = 'Hello World: %d' % self.message_count
        self.publisher.publish(message)
        self.get_logger().info('Publishing: "%s"' % message.data)
        self.message_count += 1


def main(args=None):
    """Run the publisher node."""
    rclpy.init(args=args)
    node = MinimalPublisher()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
