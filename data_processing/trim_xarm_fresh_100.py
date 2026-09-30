import csv
import shutil
from pathlib import Path

import numpy as np


SRC_ROOT = Path.home() / "xarm_demos_handwash_fresh_100"
DST_ROOT = Path.home() / "xarm_demos_handwash_fresh_100_trimmed"

MOTION_THRESHOLD = 0.005
PAD_FRAMES = 6


def load_rows(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def trim_episode(ep):
    src_ep = SRC_ROOT / f"episode_{ep:04d}"
    dst_ep = DST_ROOT / f"episode_{ep:04d}"

    training_path = src_ep / "robot_data_training.csv"
    raw_path = src_ep / "robot_data.csv"

    training_rows = load_rows(training_path)
    raw_rows = load_rows(raw_path)

    actions = np.array([
        [
            float(r[f"action_joint{i}"])
            for i in range(1, 8)
        ]
        for r in training_rows
    ])

    mag = np.max(np.abs(actions), axis=1)

    moving = np.where(
        mag > MOTION_THRESHOLD
    )[0]

    if len(moving) == 0:
        raise RuntimeError(
            f"Episode {ep:04d}: no motion found"
        )

    first_motion = int(moving[0])
    last_motion = int(moving[-1])

    start = max(
        0,
        first_motion - PAD_FRAMES,
    )

    end = min(
        len(raw_rows) - 1,
        last_motion + PAD_FRAMES,
    )

    print()
    print("=" * 60)
    print(f"Episode {ep:04d}")
    print("=" * 60)

    print("Original frames:", len(raw_rows))
    print("First motion:", first_motion)
    print("Last motion:", last_motion)
    print("Keeping:", start, "to", end)

    selected_rows = training_rows[
        start:end + 1
    ]

    if dst_ep.exists():
        shutil.rmtree(dst_ep)

    external_dst = (
        dst_ep / "external"
    )

    wrist_dst = (
        dst_ep / "wrist"
    )

    external_dst.mkdir(
        parents=True,
        exist_ok=True,
    )

    wrist_dst.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_csv = (
        dst_ep / "robot_data.csv"
    )

    fieldnames = list(
        selected_rows[0].keys()
    )

    t0 = float(
        selected_rows[0]["timestamp"]
    )

    with open(
        output_csv,
        "w",
        newline="",
    ) as f:

        writer = csv.DictWriter(
            f,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        for new_idx, row in enumerate(
            selected_rows
        ):
            old_idx = int(
                row["frame"]
            )

            new_row = dict(row)

            new_row["frame"] = new_idx

            old_time = float(
                row["timestamp"]
            )

            new_row["timestamp"] = (
                t0
                + (
                    old_time
                    - t0
                )
            )

            writer.writerow(
                new_row
            )

            src_ext = (
                src_ep
                / "external"
                / f"{old_idx:06d}.jpg"
            )

            src_wrist = (
                src_ep
                / "wrist"
                / f"{old_idx:06d}.jpg"
            )

            dst_ext = (
                external_dst
                / f"{new_idx:06d}.jpg"
            )

            dst_wrist = (
                wrist_dst
                / f"{new_idx:06d}.jpg"
            )

            shutil.copy2(
                src_ext,
                dst_ext,
            )

            shutil.copy2(
                src_wrist,
                dst_wrist,
            )

    print(
        "Trimmed frames:",
        len(selected_rows),
    )


def main():
    DST_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    for ep in range(1, 101):
        trim_episode(ep)

    print()
    print("=" * 60)
    print(
        "ALL 100 EPISODES TRIMMED"
    )
    print("=" * 60)

    print(
        "Saved to:",
        DST_ROOT,
    )


if __name__ == "__main__":
    main()
