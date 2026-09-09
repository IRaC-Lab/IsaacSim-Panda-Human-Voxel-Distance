"""Isaac Sim 4.2 behavior script for a smooth Franka Panda pick/place motion.

Attach this file to the ``/Panda`` prim with Add > Python Scripting.
Disable the existing Pick-and-Place Action Graph before using this script so
that two controllers do not command the same articulation simultaneously.
"""

import numpy as np

from omni.isaac.franka.controllers.pick_place_controller import PickPlaceController
from omni.isaac.franka.franka import Franka
from omni.kit.scripting import BehaviorScript


class PandaPickPlaceBehavior(BehaviorScript):
    """Run a pick/place-like motion automatically while the timeline plays."""

    # World-frame targets. The Panda base is at approximately Z=0.80196 m.
    # Keep X/Z fixed and sweep clearly across the robot's left/right (+/-Y).
    PICK_POSITION = np.array([0.45, 0.30, 0.95])
    PLACE_POSITION = np.array([0.45, -0.30, 0.95])
    APPROACH_HEIGHT = 1.10

    # Clamp each arm joint command to prevent a large jump on the first tick.
    MAX_JOINT_SPEED = 1.0  # rad/s

    def on_init(self):
        self._initialized = False
        self._robot = None
        self._controller = None

    def on_play(self):
        # Recreate the handles after Stop/Play because physics handles change.
        self._initialized = False

    def _initialize(self):
        self._robot = Franka(prim_path=str(self.prim_path))
        self._robot.initialize()

        self._controller = PickPlaceController(
            name="panda_pick_place_behavior_controller",
            robot_articulation=self._robot,
            gripper=self._robot.gripper,
            end_effector_initial_height=self.APPROACH_HEIGHT,
            events_dt=[
                0.005,
                0.005,
                1.0,
                0.1,
                0.05,
                0.05,
                0.0025,
                1.0,
                0.008,
                0.08,
            ],
        )
        self._initialized = True

    def on_update(self, current_time: float, delta_time: float):
        if not self._initialized:
            try:
                self._initialize()
            except Exception:
                # Physics may not be ready on the first playback tick.
                return

        if self._controller.is_done():
            # Start the sequence again and keep repeating until Stop is pressed.
            self._controller.reset(end_effector_initial_height=self.APPROACH_HEIGHT)

        current_positions = self._robot.get_joint_positions()
        if current_positions is None:
            return

        actions = self._controller.forward(
            picking_position=self.PICK_POSITION,
            placing_position=self.PLACE_POSITION,
            current_joint_positions=current_positions,
            end_effector_offset=np.array([0.0, 0.0, 0.0]),
        )

        # Limit only the seven arm joints. Gripper commands remain unchanged.
        if actions.joint_positions is not None:
            targets = list(actions.joint_positions)
            max_delta = self.MAX_JOINT_SPEED * max(delta_time, 1.0 / 240.0)

            for joint_index in range(min(7, len(targets))):
                target = targets[joint_index]
                if target is None:
                    continue

                error = target - current_positions[joint_index]
                limited_error = np.clip(error, -max_delta, max_delta)
                targets[joint_index] = current_positions[joint_index] + limited_error

            actions.joint_positions = targets

        self._robot.get_articulation_controller().apply_action(actions)

    def on_stop(self):
        self._initialized = False
        self._robot = None
        self._controller = None
