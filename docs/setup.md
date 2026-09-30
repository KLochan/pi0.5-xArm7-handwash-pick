# Setup

## Platform

- Ubuntu 24.04
- ROS 2 Jazzy
- UFactory xArm7
- UF G2 gripper
- 2 × Intel RealSense D435i cameras
- NVIDIA GPU
- π0.5 / OpenPI

## Python dependencies

Install the general Python dependencies with:

```bash
pip install -r requirements.txt
```

## ROS 2 dependencies

This project also requires:
- rclpy
- sensor_msgs
- cv_bridge
- xarm_msgs

The UFactory xArm ROS 2 packages should be built and sourced separately.

Example:

```bash
source /opt/ros/jazzy/setup.bash
source ~/xarm_ws/install/setup.bash
```

## π0.5 / OpenPI

The π0.5 model and openpi_client are provided through the OpenPI environment and are not included directly in this repository.

Model checkpoints and training datasets are intentionally excluded from Git.
