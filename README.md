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

## Real-Robot Setup

<p align="center">
  <img src="assets/xarm7_handwash_setup.jpg" width="700">
</p>

## Demo

<p align="center">
  <img src="assets/handwash_pick_demo.gif" width="700">
</p>

**Task:** “Pick up the handwash bottle.”
