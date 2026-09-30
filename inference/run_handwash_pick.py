import cv2
import time
import numpy as np

import rclpy
from rclpy.node import Node

from sensor_msgs.msg import JointState
from sensor_msgs.msg import Image
from cv_bridge import CvBridge

from xarm_msgs.srv import GetFloat32, MoveVelocity, GripperMove, SetInt16

from openpi_client import websocket_client_policy

PROMPT = input(
    'Enter task: '
).strip()

MAX_VEL = 0.03          # rad/s
COMMAND_TIME = 0.5            # seconds
NUM_CYCLES = 5          # very small first closed-loop test
# π0.5 broad-approach handoff region.
# Once the marker is sufficiently low in the wrist image,
# stop joint-velocity control and switch once to Cartesian Mode 5.
MARKER_SWITCH_X_MIN = 600
MARKER_SWITCH_X_MAX = 680

MARKER_SWITCH_Y_MIN = 550
MARKER_SWITCH_Y_MAX = 680

# Final Cartesian +X alignment target.
FINAL_X_MIN = 720
FINAL_X_MAX = 740

# Conservative Cartesian alignment pulse.
FINAL_X_SPEED = 5.0
FINAL_X_PULSE_TIME = 0.30
FINAL_X_MAX_PULSES = 18
class XArmPi05ClosedLoop(Node):

    def __init__(self):
        super().__init__("xarm_pi05_closed_loop")

        self.bridge = CvBridge()

        self.joint_position = None
        self.external_image = None
        self.wrist_image = None

        self.marker_x = None
        self.marker_y = None
        self.marker_area = 0.0
        self.marker_visible = False
        self.marker_x = None
        self.marker_y = None
        self.marker_area = 0.0
        self.create_subscription(
            JointState,
            "/xarm/joint_states",
            self.joint_callback,
            10,
        )

        self.create_subscription(
            Image,
            "/external/external/color/image_raw",
            self.external_callback,
            10,
        )

        self.create_subscription(
            Image,
            "/wrist/wrist/color/image_raw",
            self.wrist_callback,
            10,
        )

        self.gripper_client = self.create_client(
            GetFloat32,
            "/xarm/get_gripper_position",
        )

        self.velocity_client = self.create_client(
            MoveVelocity,
            "/xarm/vc_set_joint_velocity",
        )
        self.cartesian_velocity_client = self.create_client(
            MoveVelocity,
            "/xarm/vc_set_cartesian_velocity",
        )
        self.mode_client = self.create_client(
            SetInt16,
            "/xarm/set_mode",
        )

        self.state_client = self.create_client(
            SetInt16,
            "/xarm/set_state",
        )
        self.gripper_move_client = self.create_client(
            GripperMove,
            "/xarm/set_gripper_position",
        )

        self.gripper_enable_client = self.create_client(
            SetInt16,
            "/xarm/set_gripper_enable",
        )

        self.gripper_mode_client = self.create_client(
            SetInt16,
            "/xarm/set_gripper_mode",
        )
    def joint_callback(self, msg):
        joint_dict = dict(zip(msg.name, msg.position))

        try:
            self.joint_position = np.array(
                [
                    joint_dict["joint1"],
                    joint_dict["joint2"],
                    joint_dict["joint3"],
                    joint_dict["joint4"],
                    joint_dict["joint5"],
                    joint_dict["joint6"],
                    joint_dict["joint7"],
                ],
                dtype=np.float32,
            )
        except KeyError:
            pass

    def external_callback(self, msg):
        self.external_image = np.asarray(
            self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding="rgb8",
            ),
            dtype=np.uint8,
        )

    def wrist_callback(self, msg):

        self.wrist_image = np.asarray(
            self.bridge.imgmsg_to_cv2(
                msg,
                desired_encoding="rgb8",
            ),
            dtype=np.uint8,
        )

        # --------------------------------------------------
        # RED MARKER DETECTION
        # --------------------------------------------------

        bgr = cv2.cvtColor(
            self.wrist_image,
            cv2.COLOR_RGB2BGR,
        )

        hsv = cv2.cvtColor(
            bgr,
            cv2.COLOR_BGR2HSV,
        )

        lower1 = np.array(
            [0, 100, 80],
            dtype=np.uint8,
        )

        upper1 = np.array(
            [10, 255, 255],
            dtype=np.uint8,
        )

        lower2 = np.array(
            [170, 100, 80],
            dtype=np.uint8,
        )

        upper2 = np.array(
            [180, 255, 255],
            dtype=np.uint8,
        )

        mask1 = cv2.inRange(
            hsv,
            lower1,
            upper1,
        )

        mask2 = cv2.inRange(
            hsv,
            lower2,
            upper2,
        )

        mask = mask1 | mask2

        h, w = mask.shape

        roi = np.zeros_like(mask)

        roi[
            int(0.45 * h):h,
            int(0.25 * w):int(0.90 * w),
        ] = mask[
            int(0.45 * h):h,
            int(0.25 * w):int(0.90 * w),
        ]

        kernel = np.ones(
            (3, 3),
            np.uint8,
        )

        roi = cv2.morphologyEx(
            roi,
            cv2.MORPH_OPEN,
            kernel,
        )

        contours, _ = cv2.findContours(
            roi,
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE,
        )

        self.marker_visible = False

        if contours:

            contour = max(
                contours,
                key=cv2.contourArea,
            )

            area = cv2.contourArea(
                contour
            )

            if area >= 5.0:

                x, y, bw, bh = (
                    cv2.boundingRect(
                        contour
                    )
                )

                self.marker_x = (
                    x + bw // 2
                )

                self.marker_y = (
                    y + bh // 2
                )

                self.marker_area = float(
                    area
                )

                self.marker_visible = True
               
    def get_gripper(self):
        while not self.gripper_client.wait_for_service(
            timeout_sec=1.0
        ):
            print("Waiting for gripper service...")

        future = self.gripper_client.call_async(
            GetFloat32.Request()
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        response = future.result()

        if response is None:
            raise RuntimeError(
                "Could not read gripper."
            )

        raw = float(response.data)

        raw_clipped = np.clip(
            raw,
            340.0,
            850.0,
        )

        normalized = (
            1.0
            - raw_clipped / 850.0
        )

        return raw, normalized

    def refresh_inputs(self):

        old_joint = None

        if self.joint_position is not None:
            old_joint = self.joint_position.copy()

        # Spin briefly so we receive fresh images/state
        start = time.time()

        while time.time() - start < 0.5:
            rclpy.spin_once(
                self,
                timeout_sec=0.05,
            )

        return old_joint
    def prepare_gripper(self):

        while not self.gripper_enable_client.wait_for_service(
            timeout_sec=1.0
        ):
            print("Waiting for gripper enable service...")

        enable_req = SetInt16.Request()
        enable_req.data = 1

        future = self.gripper_enable_client.call_async(
            enable_req
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        print(
            "Gripper enable response:",
            future.result().ret,
            future.result().message,
        )

        while not self.gripper_mode_client.wait_for_service(
            timeout_sec=1.0
        ):
            print("Waiting for gripper mode service...")

        mode_req = SetInt16.Request()
        mode_req.data = 0

        future = self.gripper_mode_client.call_async(
            mode_req
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        print(
            "Gripper mode response:",
            future.result().ret,
            future.result().message,
        )

    def move_gripper(self, target):

        while not self.gripper_move_client.wait_for_service(
            timeout_sec=1.0
        ):
            print("Waiting for gripper move service...")

        request = GripperMove.Request()

        request.pos = float(target)
        request.wait = False
        request.timeout = 5.0

        future = self.gripper_move_client.call_async(
            request
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        return future.result()
    
    def send_velocity(
        self,
        velocities,
        duration,
    ):

        while not self.velocity_client.wait_for_service(
            timeout_sec=1.0
        ):
            print(
                "Waiting for velocity service..."
            )

        request = MoveVelocity.Request()

        request.speeds = [
            float(v)
            for v in velocities
        ]

        request.is_sync = True
        request.duration = float(duration)

        future = self.velocity_client.call_async(
            request
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        response = future.result()

        if response is None:
            raise RuntimeError(
                "Velocity service call failed."
            )

        return response
    def send_cartesian_velocity(
        self,
        velocities,
        duration,
    ):

        while not self.cartesian_velocity_client.wait_for_service(
            timeout_sec=1.0
        ):
            print("Waiting for Cartesian velocity service...")

        request = MoveVelocity.Request()

        request.speeds = [
            float(v)
            for v in velocities
        ]

        request.is_sync = False
        request.is_tool_coord = False
        request.duration = float(duration)

        future = self.cartesian_velocity_client.call_async(
            request
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        response = future.result()

        if response is None:
            raise RuntimeError(
                "Cartesian velocity service call failed."
            )

        return response
    def set_robot_mode(self, mode):

        while not self.mode_client.wait_for_service(
            timeout_sec=1.0
        ):
            print("Waiting for /xarm/set_mode...")

        request = SetInt16.Request()
        request.data = int(mode)

        future = self.mode_client.call_async(request)

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        return future.result()


    def set_robot_state(self, state):

        while not self.state_client.wait_for_service(
            timeout_sec=1.0
        ):
            print("Waiting for /xarm/set_state...")

        request = SetInt16.Request()
        request.data = int(state)

        future = self.state_client.call_async(request)

        rclpy.spin_until_future_complete(
            self,
            future,
        )

        return future.result()
    def stop_robot(self):

        stop_request = MoveVelocity.Request()

        stop_request.speeds = [0.0] * 7
        stop_request.is_sync = True
        stop_request.duration = 0.1

        future = self.velocity_client.call_async(
            stop_request
        )

        rclpy.spin_until_future_complete(
            self,
            future,
        )


def main():

    rclpy.init()

    node = XArmPi05ClosedLoop()

    node.prepare_gripper()
    print("Gripper enabled and ready.")
    print(
        "Waiting for robot and both cameras..."
    )

    while rclpy.ok():

        rclpy.spin_once(
            node,
            timeout_sec=0.1,
        )

        if (
            node.joint_position is not None
            and node.external_image is not None
            and node.wrist_image is not None
        ):
            break

    print(
        "All live inputs received."
    )

    policy = (
        websocket_client_policy
        .WebsocketClientPolicy(
            host="0.0.0.0",
            port=8000,
        )
    )

    print(
        "Connected to π0.5 server."
    )

    print(
        "\n===================================="
    )
    print(
        "CLOSED-LOOP TEST SETTINGS"
    )
    print(
        "===================================="
    )

    print(
        "Cycles:",
        NUM_CYCLES,
    )

    print(
        "Max velocity:",
        MAX_VEL,
        "rad/s",
    )

    print(
        "Command time:",
        COMMAND_TIME,
        "seconds",
    )

    print(
        "Gripper motion: ENABLED"
    )

    answer = input(
        "\nType START to begin the end-to-end VLA test: "
    )

    if answer != "START":

        print(
            "Cancelled. No motion sent."
        )

        node.destroy_node()
        rclpy.shutdown()
        return

    try:

        for cycle in range(
            NUM_CYCLES
        ):

            print(
                "\n===================================="
            )

            print(
                f"CYCLE {cycle + 1}/{NUM_CYCLES}"
            )

            print(
                "===================================="
            )

            node.refresh_inputs()

            raw_gripper, normalized_gripper = (
                node.get_gripper()
            )

            state = np.concatenate(
                [
                    node.joint_position,
                    np.array(
                        [normalized_gripper],
                        dtype=np.float32,
                    ),
                ]
            ).astype(np.float32)

            observation = {
                "observation/state":
                    state,

                "observation/image":
                    node.external_image,

                "observation/wrist_image":
                    node.wrist_image,

                "prompt":
                    PROMPT,
            }
            print(
                "Current joints:"
            )
            print(
                node.joint_position
            )

            print(
                "Raw gripper:",
                raw_gripper,
            )

            print(
                "Running 5 π0.5 candidate inferences..."
            )

            NUM_SAMPLES = 1
            EXECUTE_STEPS = 1

            candidates = []
            sample_times = []

            # IMPORTANT:
            # All 5 candidates use this exact same frozen observation.
            for sample_index in range(NUM_SAMPLES):

                start = time.time()

                result = policy.infer(
                    observation
                )

                elapsed = (
                    time.time() - start
                )

                sample_times.append(
                    elapsed
                )

                actions = np.asarray(
                    result["actions"],
                    dtype=np.float32,
                )

                physical = (
                    actions[:, :8]
                )

                first3_joints = (
                    physical[
                        :EXECUTE_STEPS,
                        :7,
                    ]
                )

                candidates.append(
                    {
                        "physical": physical,
                        "first3": first3_joints,
                    }
                )

                print(
                    f"Candidate {sample_index + 1}/{NUM_SAMPLES} "
                    f"inference time: {elapsed:.4f} s"
                )

            # Shape:
            # [5 candidates, 3 actions, 7 joints]
            candidate_stack = np.stack(
                [
                    candidate["first3"]
                    for candidate in candidates
                ],
                axis=0,
            )

            # Element-wise median trajectory.
            median_trajectory = np.median(
                candidate_stack,
                axis=0,
            )

            MIN_MOTION_NORM = 0.02

            active_indices = []

            print()
            print("Candidate selection:")

            for sample_index, candidate in enumerate(
                candidates
            ):

                # Check the COMPLETE 15-step predicted joint trajectory.
                # The first few post-grasp actions may intentionally be near zero,
                # while meaningful lift motion appears later in the chunk.
                full_joint_chunk = candidate["physical"][:, :7]

                motion_norm = float(
                    np.linalg.norm(
                        full_joint_chunk
                    )
                )

                max_abs_velocity = float(
                    np.max(
                        np.abs(
                            full_joint_chunk
                        )
                    )
                )

                if motion_norm >= MIN_MOTION_NORM:
                    status = "ACTIVE"
                    active_indices.append(
                        sample_index
                    )
                else:
                    status = "REJECT NEAR-ZERO"

                print(
                    f"  Candidate {sample_index + 1}: "
                    f"motion_norm={motion_norm:.6f}, "
                    f"max_abs_vel={max_abs_velocity:.6f}, "
                    f"{status}"
                )

            if len(active_indices) == 0:
                raise RuntimeError(
                    "No meaningful-motion candidate found. "
                    "Robot will not move."
                )

            active_stack = np.stack(
                [
                    candidates[i]["first3"]
                    for i in active_indices
                ],
                axis=0,
            )

            active_median = np.median(
                active_stack,
                axis=0,
            )

            active_distances = []

            for i in active_indices:

                distance = float(
                    np.linalg.norm(
                        candidates[i]["first3"]
                        - active_median
                    )
                )

                active_distances.append(
                    distance
                )

                print(
                    f"    Active candidate {i + 1}: "
                    f"distance_to_active_median="
                    f"{distance:.6f}"
                )

            best_active_position = int(
                np.argmin(
                    active_distances
                )
            )

            selected_index = (
                active_indices[
                    best_active_position
                ]
            )

            physical_actions = (
                candidates[
                    selected_index
                ]["physical"]
            )

            print()
            print(
                "Selected representative candidate:",
                selected_index + 1,
            )

            print(
                "Total 5-sample inference time:",
                sum(sample_times),
                "s",
            )

            print(
                "Selected physical action(s):"
            )

            print(
                physical_actions[
                    :EXECUTE_STEPS,
                    :8,
                ]
            )

            print(
                "Gripper predictions across 15-step chunk:"
            )

            print(
                physical_actions[:, 7]
            )

            print(
                "Maximum gripper prediction in chunk:",
                float(
                    np.max(
                        physical_actions[:, 7]
                    )
                ),
            )


            # -------------------------------------------------
            # END-TO-END VLA EXECUTION
            #
            # Always execute the earliest action from the newly
            # inferred chunk, then re-observe and infer again.
            # -------------------------------------------------
            for action_index in range(EXECUTE_STEPS):

                chunk_index = action_index

                current_action = physical_actions[
                    chunk_index
                ]

                # ---------------------------------------------
                # Learned arm action: joint velocity [rad/s]
                # ---------------------------------------------
                predicted_joint_vel = (
                    current_action[:7]
                )

                # Match the displacement of one 6 Hz training step
                # while keeping the longer command duration required
                # for reliable xArm motion.
                TRAINING_DT = 1.0 / 6.0
                time_scale = TRAINING_DT / COMMAND_TIME

                timing_scaled_joint_vel = (
                    predicted_joint_vel * time_scale
                )

                max_abs = np.max(
                    np.abs(timing_scaled_joint_vel)
                )

                # Safety clipping only.
                # This is NOT task-specific hand coding.
                if max_abs > MAX_VEL:
                    clip_scale = MAX_VEL / max_abs
                    safe_joint_vel = (
                        timing_scaled_joint_vel * clip_scale
                    )
                else:
                    safe_joint_vel = (
                        timing_scaled_joint_vel.copy()
                    )

                # ---------------------------------------------
                # Learned gripper action
                #
                # Training space:
                #   0.0 ~= fully open
                #   0.6 ~= closed
                #
                # xArm raw space:
                #   850 ~= fully open
                #   340 ~= closed
                # ---------------------------------------------
                gripper_action = float(
                    current_action[7]
                )

                gripper_normalized = float(
                    np.clip(
                        gripper_action,
                        0.0,
                        0.6,
                    )
                )

                gripper_raw_target = float(
                    np.clip(
                        850.0
                        * (
                            1.0
                            - gripper_normalized
                        ),
                        340.0,
                        850.0,
                    )
                )

                print()
                print(
                    f"Executing VLA action "
                    f"{chunk_index + 1}/15"
                )

                print(
                    "Predicted joint velocity:"
                )
                print(
                    predicted_joint_vel
                )

                print(
                    "Executed joint velocity:"
                )
                print(
                    safe_joint_vel
                )

                print(
                    "Predicted gripper action:",
                    gripper_action,
                )

                print(
                    "Policy gripper normalized:",
                    gripper_normalized,
                )

                print(
                    "Policy gripper raw target:",
                    gripper_raw_target,
                )

                # π0.5 directly controls the gripper.
                gripper_response = node.move_gripper(
                    gripper_raw_target
                )

                print(
                    "Gripper response:",
                    gripper_response.ret,
                )

                # π0.5 directly controls the arm.
                response = node.send_velocity(
                    safe_joint_vel,
                    COMMAND_TIME,
                )

                print(
                    "Velocity response:",
                    response.ret,
                    response.message,
                )

                # Let this velocity command actually run.
                time.sleep(
                    COMMAND_TIME
                )

            # Explicit stop after the 3-action chunk.
            node.stop_robot()

            print(
                "Zero velocity sent after VLA action."
            )            

            # Receive updated robot/camera state
            node.refresh_inputs()

            print(
                "Updated joints:"
            )

            print(
                node.joint_position
            )

        print(
            "\n===================================="
        )

        print(
            "END-TO-END VLA TEST COMPLETE"
        )

        print(
            "===================================="
        )

    except KeyboardInterrupt:

        print(
            "\nKeyboard interrupt."
        )

    finally:

        # Always attempt a stop before exiting.
        try:
            node.stop_robot()

            print(
                "Final zero velocity sent."
            )

        except Exception as error:

            print(
                "Final stop error:",
                error,
            )

        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()
