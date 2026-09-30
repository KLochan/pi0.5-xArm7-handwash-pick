import csv
from pathlib import Path

import numpy as np


DATA_ROOT = Path.home() / "xarm_demos_handwash_fresh_100"

JOINTS = [f"joint{i}" for i in range(1, 8)]


def centered_moving_average(x, window=5):
    """
    Centered moving average equivalent to:
    rolling(window=5, center=True, min_periods=1).mean()
    """
    x = np.asarray(x, dtype=np.float64)

    radius = window // 2
    out = np.empty_like(x)

    for i in range(len(x)):
        start = max(0, i - radius)
        end = min(len(x), i + radius + 1)

        out[i] = np.mean(x[start:end])

    return out


def preprocess_episode(ep):

    episode_dir = DATA_ROOT / f"episode_{ep:04d}"

    raw_path = episode_dir / "robot_data.csv"

    actions_path = (
        episode_dir / "robot_data_with_actions.csv"
    )

    training_path = (
        episode_dir / "robot_data_training.csv"
    )

    print()
    print("=" * 70)
    print(f"Processing episode {ep:04d}")
    print("=" * 70)

    with open(raw_path, newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        raw_fieldnames = reader.fieldnames

    if len(rows) < 2:
        raise RuntimeError(
            f"Episode {ep:04d} has fewer than 2 frames"
        )

    n = len(rows)

    timestamps = np.array(
        [float(r["timestamp"]) for r in rows],
        dtype=np.float64,
    )

    raw_joints = np.zeros(
        (n, 7),
        dtype=np.float64,
    )

    for j in range(7):
        raw_joints[:, j] = [
            float(r[f"joint{j+1}"])
            for r in rows
        ]

    gripper = np.array(
        [
            float(r["gripper_normalized"])
            for r in rows
        ],
        dtype=np.float64,
    )

    # --------------------------------------------------
    # 1. Smoothed joints
    # --------------------------------------------------

    smoothed = np.zeros_like(raw_joints)

    for j in range(7):
        smoothed[:, j] = centered_moving_average(
            raw_joints[:, j],
            window=5,
        )

    # --------------------------------------------------
    # 2. Actions from smoothed trajectory
    # --------------------------------------------------

    actions = np.zeros(
        (n, 7),
        dtype=np.float64,
    )

    for i in range(n - 1):

        dt = timestamps[i + 1] - timestamps[i]

        if dt <= 0:
            raise RuntimeError(
                f"Invalid dt in episode {ep:04d}, "
                f"frame {i}: {dt}"
            )

        actions[i, :] = (
            smoothed[i + 1, :]
            - smoothed[i, :]
        ) / dt

    # Last frame has no next state.
    actions[-1, :] = 0.0

    # --------------------------------------------------
    # 3. robot_data_with_actions.csv
    # --------------------------------------------------

    action_fields = [
        f"action_joint{i}"
        for i in range(1, 8)
    ] + [
        "action_gripper"
    ]

    with open(
        actions_path,
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=raw_fieldnames + action_fields,
        )

        writer.writeheader()

        for i, r in enumerate(rows):

            out = dict(r)

            for j in range(7):
                out[f"action_joint{j+1}"] = (
                    float(actions[i, j])
                )

            out["action_gripper"] = (
                float(gripper[i])
            )

            writer.writerow(out)

    # --------------------------------------------------
    # 4. robot_data_training.csv
    #
    # Exact column ordering of original dataset:
    #
    # raw fields,
    # smoothed_joint1, action_joint1,
    # smoothed_joint2, action_joint2,
    # ...
    # smoothed_joint7, action_joint7,
    # action_gripper
    # --------------------------------------------------

    training_fields = list(raw_fieldnames)

    for j in range(1, 8):
        training_fields.extend(
            [
                f"smoothed_joint{j}",
                f"action_joint{j}",
            ]
        )

    training_fields.append(
        "action_gripper"
    )

    with open(
        training_path,
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=training_fields,
        )

        writer.writeheader()

        for i, r in enumerate(rows):

            out = dict(r)

            for j in range(7):

                out[f"smoothed_joint{j+1}"] = (
                    float(smoothed[i, j])
                )

                out[f"action_joint{j+1}"] = (
                    float(actions[i, j])
                )

            out["action_gripper"] = (
                float(gripper[i])
            )

            writer.writerow(out)

    print(f"Frames: {n}")
    print(f"Created: {actions_path.name}")
    print(f"Created: {training_path.name}")

    print(
        "dt mean:",
        float(np.mean(np.diff(timestamps))),
    )

    print(
        "max |joint action|:",
        float(np.max(np.abs(actions))),
    )

    print(
        "gripper range:",
        float(np.min(gripper)),
        "to",
        float(np.max(gripper)),
    )


def main():

    for ep in range(1, 101):
        preprocess_episode(ep)

    print()
    print("=" * 70)
    print("ALL 100 EPISODES PREPROCESSED")
    print("=" * 70)


if __name__ == "__main__":
    main()
