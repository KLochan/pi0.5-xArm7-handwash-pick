from pathlib import Path
import shutil

import numpy as np
import pandas as pd
from PIL import Image

from lerobot.common.datasets.lerobot_dataset import (
    HF_LEROBOT_HOME,
    LeRobotDataset,
)


# ---------------------------------------------------------
# SETTINGS
# ---------------------------------------------------------

RAW_DATA_DIR = Path.home() / "xarm_demos_handwash_fresh_100_trimmed"

# Local LeRobot dataset name.
# We are NOT uploading it yet.
REPO_NAME = "lochan/xarm_handwash_fresh_100"

FPS = 6

TASK = "pick up the handwash bottle"


# ---------------------------------------------------------
# CREATE DATASET
# ---------------------------------------------------------

def main():

    output_path = HF_LEROBOT_HOME / REPO_NAME

    print("Raw dataset:")
    print(RAW_DATA_DIR)

    print()
    print("LeRobot output:")
    print(output_path)

    # Remove an earlier test conversion, if one exists
    if output_path.exists():
        print()
        print("Removing previous converted dataset...")
        shutil.rmtree(output_path)

    dataset = LeRobotDataset.create(
        repo_id=REPO_NAME,
        robot_type="xarm7",
        fps=FPS,
        features={

            # External RealSense RGB image
            "external_image": {
                "dtype": "image",
                "shape": (720, 1280, 3),
                "names": [
                    "height",
                    "width",
                    "channel",
                ],
            },

            # Wrist RealSense RGB image
            "wrist_image": {
                "dtype": "image",
                "shape": (720, 1280, 3),
                "names": [
                    "height",
                    "width",
                    "channel",
                ],
            },

            # 7 arm joint positions
            "joint_position": {
                "dtype": "float32",
                "shape": (7,),
                "names": [
                    "joint_position",
                ],
            },

            # Normalized gripper state
            "gripper_position": {
                "dtype": "float32",
                "shape": (1,),
                "names": [
                    "gripper_position",
                ],
            },

            # 7 derived joint velocities
            # + normalized gripper action
            "actions": {
                "dtype": "float32",
                "shape": (8,),
                "names": [
                    "actions",
                ],
            },
        },
        image_writer_threads=4,
        image_writer_processes=0,
    )

    episode_dirs = sorted(
        RAW_DATA_DIR.glob("episode_*")
    )

    print()
    print(
        f"Found {len(episode_dirs)} episodes."
    )

    if len(episode_dirs) == 0:
        raise RuntimeError(
            "No episode folders found."
        )

    # -----------------------------------------------------
    # PROCESS EPISODES
    # -----------------------------------------------------

    for episode_index, episode_dir in enumerate(
        episode_dirs
    ):

        print()
        print(
            f"[{episode_index + 1}/{len(episode_dirs)}] "
            f"{episode_dir.name}"
        )

        csv_path = (
            episode_dir /
            "robot_data.csv"
        )

        external_dir = (
            episode_dir /
            "external"
        )

        wrist_dir = (
            episode_dir /
            "wrist"
        )

        if not csv_path.exists():
            raise FileNotFoundError(
                f"Missing: {csv_path}"
            )

        df = pd.read_csv(csv_path)

        for row_index, row in df.iterrows():

            frame_id = int(row["frame"])

            external_path = (
                external_dir /
                f"{frame_id:06d}.jpg"
            )

            wrist_path = (
                wrist_dir /
                f"{frame_id:06d}.jpg"
            )

            if not external_path.exists():
                raise FileNotFoundError(
                    f"Missing external image: "
                    f"{external_path}"
                )

            if not wrist_path.exists():
                raise FileNotFoundError(
                    f"Missing wrist image: "
                    f"{wrist_path}"
                )

            # PIL -> RGB numpy array
            external_image = np.asarray(
                Image.open(
                    external_path
                ).convert("RGB")
            )

            wrist_image = np.asarray(
                Image.open(
                    wrist_path
                ).convert("RGB")
            )

            # ---------------------------------------------
            # STATE
            # ---------------------------------------------

            joint_position = np.asarray(
                [
                    row["joint1"],
                    row["joint2"],
                    row["joint3"],
                    row["joint4"],
                    row["joint5"],
                    row["joint6"],
                    row["joint7"],
                ],
                dtype=np.float32,
            )

            gripper_position = np.asarray(
                [
                    row[
                        "gripper_normalized"
                    ]
                ],
                dtype=np.float32,
            )

            # ---------------------------------------------
            # ACTION
            # ---------------------------------------------

            actions = np.asarray(
                [
                    row["action_joint1"],
                    row["action_joint2"],
                    row["action_joint3"],
                    row["action_joint4"],
                    row["action_joint5"],
                    row["action_joint6"],
                    row["action_joint7"],
                    row["action_gripper"],
                ],
                dtype=np.float32,
            )

            # ---------------------------------------------
            # ADD FRAME
            # ---------------------------------------------

            dataset.add_frame(
                {
                    "external_image":
                        external_image,

                    "wrist_image":
                        wrist_image,

                    "joint_position":
                        joint_position,

                    "gripper_position":
                        gripper_position,

                    "actions":
                        actions,

                    "task":
                        TASK,
                }
            )

        # Save this episode
        dataset.save_episode()

        print(
            f"Saved {len(df)} frames."
        )

    # -----------------------------------------------------
    # FINALIZE DATASET
    # -----------------------------------------------------

    print()
    print("Finalizing LeRobot dataset...")

    # Required by current LeRobot v3 writer
    if hasattr(dataset, "finalize"):
        dataset.finalize()

    print()
    print("========================================")
    print("xArm → LeRobot conversion complete")
    print("========================================")
    print(f"Episodes: {len(episode_dirs)}")
    print(f"FPS:      {FPS}")
    print(f"Task:     {TASK}")
    print()
    print("Dataset saved at:")
    print(output_path)
    print("========================================")


if __name__ == "__main__":
    main()
