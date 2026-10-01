# π0.5 xArm7 Handwash Bottle Picking

Vision-Language-Action implementation using π0.5 on a UFactory xArm7 robot for real-world handwash bottle picking.

## Overview

This project integrates:

- π0.5 Vision-Language-Action model
- UFactory xArm7 robot
- UF G2 gripper
- Dual Intel RealSense D435i cameras
- LeRobot-format demonstrations
- Real-robot inference and action execution

## Task

The robot is instructed to:

> Pick up the handwash bottle.

The system receives:

- External RGB camera image
- Wrist RGB camera image
- xArm7 joint state
- Natural-language instruction

and uses π0.5 to generate robot actions.

## Hardware

- UFactory xArm7
- UF G2 gripper
- 2 × Intel RealSense D435i
- NVIDIA GPU workstation

## Dataset

Approximately 100 real-robot demonstrations were collected for the handwash-bottle picking task.

The dataset was converted into LeRobot format for π0.5 training and inference.

## System Pipeline

```text
External Camera
      +
Wrist Camera
      +
Robot Joint State
      +
Language Instruction
      ↓
     π0.5
      ↓
Predicted Action Chunk
      ↓
xArm7 + UF G2 Gripper
```

## Real-Robot Setup

<p align="center">
  <img src="assets/xarm7_handwash_setup.jpg" width="700">
</p>

## Demo

<p align="center">
  <img src="assets/handwash_pick_demo.gif" width="700">
</p>

**Task:** “Pick up the handwash bottle.”

## How to Run

This repository assumes that ROS 2 Jazzy, the UFactory xArm ROS 2 packages, the RealSense camera stack, and the OpenPI / π0.5 environment are already installed.

1. Clone this repository and enter the project folder.

```bash
git clone https://github.com/KLochan/pi0.5-xArm7-handwash-pick.git
cd pi0.5-xArm7-handwash-pick
```

2. Install the general Python dependencies.

```bash
pip install -r requirements.txt
```

3. Source ROS 2 and the xArm workspace.

```bash
source /opt/ros/jazzy/setup.bash
source ~/xarm_ws/install/setup.bash
```

4. Start the required robot and camera interfaces for your local setup.

5. Start the π0.5 / OpenPI inference server from the OpenPI environment.

6. Run the real-robot handwash picking client.

```bash
python3 inference/run_handwash_pick.py
```

For an inference-only check, use:

```bash
python3 inference/xarm_pi05_live_inference_only.py
```

For a dry run before commanding the robot, use:

```bash
python3 tests/xarm_pi05_true_dryrun.py
```

> **Safety:** Verify the robot workspace, emergency-stop access, joint limits, gripper state, camera streams, and predicted actions before enabling real-robot motion.

More setup details are available in [docs/setup.md](docs/setup.md), and the data-to-deployment pipeline is summarized in [docs/workflow.md](docs/workflow.md).

## Repository Scope

This repository contains the xArm7 integration, data-collection, preprocessing, LeRobot conversion, and real-robot inference code developed for the handwash-bottle picking experiment.

Large datasets, trained checkpoints, recorded ROS bags, Hugging Face caches, and upstream third-party repositories are intentionally excluded.

## Acknowledgements

This project builds on several external software and hardware ecosystems:

- **π0.5 / OpenPI** for the Vision-Language-Action policy and inference infrastructure.
- **LeRobot** for robot-learning dataset tooling and dataset representation.
- **ROS 2** for robot communication and middleware.
- **UFactory xArm7 and xArm ROS 2 packages** for robot control.
- **Intel RealSense** cameras for visual observations.

The third-party frameworks and drivers above remain subject to their respective licenses and terms. This repository focuses on the integration and experimental pipeline for deploying π0.5 on the xArm7 handwash-bottle task.

## Citation

If you use this repository in academic work, please cite the relevant upstream π0.5 / OpenPI and LeRobot publications or repositories in addition to referencing this implementation.

A project-specific BibTeX entry can be added here if this work is released with an associated paper.

