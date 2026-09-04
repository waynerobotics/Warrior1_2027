# example_dual_pubsub

This package contains two small ROS 2 Python nodes that demonstrate a topic
publisher and subscriber working together.

## Nodes and topic

- `publisher` runs the `minimal_publisher` node. Every 0.5 seconds it publishes
  a `std_msgs/msg/String` message on the `chatter` topic.
- `subscriber` runs the `minimal_subscriber` node. It listens to `chatter` and
  logs each received message.

The publisher and subscriber use the same topic name and message type, so ROS 2
can connect them automatically through its built-in graph discovery.

## Build and run

From a sourced ROS 2 workspace (/workspaces directory), build and source the package:

```bash
colcon build --packages-select example_dual_pubsub
source install/setup.bash
```

Run both nodes with the launch file:

```bash
ros2 launch example_dual_pubsub dual_pubsub.launch.py
```

The nodes can also be run separately in two terminals:

```bash
ros2 run example_dual_pubsub publisher
ros2 run example_dual_pubsub subscriber
```