# Handwash Bottle Picking Workflow

The real-robot pipeline is:

```text
100 xArm7 demonstrations
        |
        v
record_xarm_fresh_100.py
        |
        v
trim_xarm_fresh_100.py
        |
        v
preprocess_xarm_fresh_100.py
        |
        v
xarm_to_lerobot_fresh_100.py
        |
        v
LeRobot dataset
        |
        v
π0.5 training / checkpoint
        |
        v
π0.5 inference server
        |
        v
run_handwash_pick.py
        |
        v
xArm7 + UF G2 gripper
```

## Main task

Language instruction:

> Pick up the handwash bottle.

The policy receives visual observations, robot state, and the language instruction and predicts an action chunk for the xArm7.
