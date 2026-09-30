import csv
import time
import threading
from pathlib import Path

import cv2
import numpy as np
import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image, JointState

from xarm_msgs.srv import GetFloat32


DATA_ROOT = Path.home() / "xarm_demos_handwash_fresh_100"

EXTERNAL_TOPIC = "/external/external/color/image_raw"
WRIST_TOPIC = "/wrist/wrist/color/image_raw"
JOINT_TOPIC = "/xarm/joint_states"

FPS = 6.0
DT = 1.0 / FPS

TASK = "pick up the handwash bottle"


class DemoRecorder(Node):

    def __init__(self):

        super().__init__("xarm_demo_recorder")

        self.bridge = CvBridge()

        self.external_image = None
        self.wrist_image = None
        self.joints = None

        self.create_subscription(
            Image,
            EXTERNAL_TOPIC,
            self.external_callback,
            10,
        )

        self.create_subscription(
            Image,
            WRIST_TOPIC,
            self.wrist_callback,
            10,
        )

        self.create_subscription(
            JointState,
            JOINT_TOPIC,
            self.joint_callback,
            10,
        )

        self.gripper_client = self.create_client(
            GetFloat32,
            "/xarm/get_gripper_position",
        )

    def external_callback(self, msg):

        self.external_image = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="bgr8",
        )

    def wrist_callback(self, msg):

        self.wrist_image = self.bridge.imgmsg_to_cv2(
            msg,
            desired_encoding="bgr8",
        )

    def joint_callback(self, msg):

        if len(msg.position) >= 7:
            self.joints = np.asarray(
                msg.position[:7],
                dtype=np.float32,
            )

    def get_gripper(self):

        if not self.gripper_client.wait_for_service(
            timeout_sec=1.0
        ):
            return None

        request = GetFloat32.Request()

        future = self.gripper_client.call_async(
            request
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        result = future.result()

        if result is None:
            return None

        return float(result.data)


def wait_for_inputs(node):

    print("Waiting for robot and both cameras...")

    while rclpy.ok():

        rclpy.spin_once(
            node,
            timeout_sec=0.1,
        )

        if (
            node.external_image is not None
            and node.wrist_image is not None
            and node.joints is not None
        ):
            print("All inputs received.")
            return


def record_episode(node, episode_index):

    episode_dir = (
        DATA_ROOT
        / f"episode_{episode_index:04d}"
    )

    external_dir = (
        episode_dir / "external"
    )

    wrist_dir = (
        episode_dir / "wrist"
    )

    external_dir.mkdir(
        parents=True,
        exist_ok=False,
    )

    wrist_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    csv_path = (
        episode_dir / "robot_data.csv"
    )

    fieldnames = [
        "frame",
        "timestamp",
        "joint1",
        "joint2",
        "joint3",
        "joint4",
        "joint5",
        "joint6",
        "joint7",
        "gripper_command_raw",
        "gripper_normalized",
        "task",
    ]

    stop_event = threading.Event()

    def wait_for_stop():

        input(
            "\nPress ENTER when this demonstration is finished...\n"
        )

        stop_event.set()

    stop_thread = threading.Thread(
        target=wait_for_stop,
        daemon=True,
    )

    with open(
        csv_path,
        "w",
        newline="",
    ) as csv_file:

        writer = csv.DictWriter(
            csv_file,
            fieldnames=fieldnames,
        )

        writer.writeheader()

        print()
        print(
            f"Recording episode "
            f"{episode_index:04d}"
        )

        print(
            "Perform the demonstration now."
        )

        print(
            "DO NOT press Ctrl+C."
        )

        print(
            "Press ENTER when finished."
        )

        stop_thread.start()

        frame = 0
        next_time = time.monotonic()

        while (
            rclpy.ok()
            and not stop_event.is_set()
        ):

            now = time.monotonic()

            if now < next_time:

                rclpy.spin_once(
                    node,
                    timeout_sec=min(
                        0.01,
                        next_time - now,
                    ),
                )

                continue

            next_time += DT

            rclpy.spin_once(
                node,
                timeout_sec=0.001,
            )

            if (
                node.external_image is None
                or node.wrist_image is None
                or node.joints is None
            ):
                continue

            raw_gripper = (
                node.get_gripper()
            )

            if raw_gripper is None:
                print(
                    "\nWARNING: "
                    "gripper read failed"
                )
                continue

            raw_gripper = np.clip(
                raw_gripper,
                340.0,
                850.0,
            )

            gripper_normalized = (
                1.0
                - raw_gripper / 850.0
            )

            timestamp = time.time()

            external_image = (
                node.external_image.copy()
            )

            wrist_image = (
                node.wrist_image.copy()
            )

            joints = (
                node.joints.copy()
            )

            cv2.imwrite(
                str(
                    external_dir
                    / f"{frame:06d}.jpg"
                ),
                external_image,
            )

            cv2.imwrite(
                str(
                    wrist_dir
                    / f"{frame:06d}.jpg"
                ),
                wrist_image,
            )

            row = {
                "frame":
                    frame,

                "timestamp":
                    timestamp,

                "joint1":
                    float(joints[0]),

                "joint2":
                    float(joints[1]),

                "joint3":
                    float(joints[2]),

                "joint4":
                    float(joints[3]),

                "joint5":
                    float(joints[4]),

                "joint6":
                    float(joints[5]),

                "joint7":
                    float(joints[6]),

                "gripper_command_raw":
                    float(raw_gripper),

                "gripper_normalized":
                    float(
                        gripper_normalized
                    ),

                "task":
                    TASK,
            }

            writer.writerow(row)

            csv_file.flush()

            print(
                f"\rframe {frame}",
                end="",
                flush=True,
            )

            frame += 1

    print()
    print(
        f"Episode {episode_index:04d} "
        f"saved with {frame} frames."
    )


def main():

    rclpy.init()

    node = DemoRecorder()

    DATA_ROOT.mkdir(
        parents=True,
        exist_ok=True,
    )

    try:

        wait_for_inputs(node)

        for episode_index in range(
            1,
            101,
        ):

            print()
            print("=" * 60)

            print(
                f"READY FOR DEMONSTRATION "
                f"{episode_index}/100"
            )

            print("=" * 60)

            input(
                "Reset robot and bottle, "
                "then press ENTER to START..."
            )

            record_episode(
                node,
                episode_index,
            )

            if episode_index < 100:

                print()
                print(
                    "Reset robot and bottle "
                    "for the next demonstration."
                )

        print()
        print("=" * 60)
        print(
            "ALL 100 DEMONSTRATIONS COMPLETE"
        )
        print("=" * 60)

    except KeyboardInterrupt:

        print()
        print(
            "Recording session aborted."
        )

    finally:

        if rclpy.ok():
            node.destroy_node()
            rclpy.shutdown()


if __name__ == "__main__":
    main()
