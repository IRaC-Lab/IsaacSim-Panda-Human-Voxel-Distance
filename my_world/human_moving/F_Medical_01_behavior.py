# Copyright (c) 2022, NVIDIA CORPORATION.  All rights reserved.
#
# NVIDIA CORPORATION and its licensors retain all intellectual property
# and proprietary rights in and to this software, related documentation
# and any modifications thereto.  Any use, reproduction, disclosure or
# distribution of this software and related documentation without an express
# license agreement from NVIDIA CORPORATION is strictly prohibited.

from __future__ import annotations

import carb
import omni.anim.graph.core as ag
from omni.anim.people.scripts.global_agent_manager import GlobalAgentManager
from omni.anim.people.scripts.navigation_manager import NavigationManager
from omni.kit.scripting import BehaviorScript

from omni.anim.people.scripts.commands.goto import *
from omni.anim.people.scripts.utils import Utils


class CharacterBehavior(BehaviorScript):
    """
    Character controller for female_adult_medical_01.

    The character repeatedly moves between:
    - start/origin position: (2.5, -3.0, 0.0)
    - target position:       (2.5,  0.0, 0.0)
    """

    def on_init(self):
        """
        Called when a script is attached to characters and when a stage is loaded. Uses renew_character_state() to initialize character state.
        """
        self.renew_character_state()

    def on_play(self):
        """
        Called when entering runtime (when clicking play button). Uses renew_character_state() to initialize character state.
        """
        self.renew_character_state()

    def on_stop(self):
        """
        Called when exiting runtime (when clicking stop button). Uses on_destroy() to clear state.
        """
        self.on_destroy()

    def on_destroy(self):
        """
        Clears character state by deleting global variable instances.
        """
        self.character_name = None
        if self.navigation_manager is not None:
            self.navigation_manager.destroy()
            self.navigation_manager = None

        if self.global_character_manager is not None:
            self.global_character_manager.destroy()
            self.global_character_manager = None

    def renew_character_state(self):
        """
        Defines character variables and loads settings.
        """
        self.character_name = "female_adult_medical_01"

        # This stage has no baked NavMesh. Use a direct straight-line path for
        # the fixed round trip instead of calling query_shortest_path().
        self.navmeshEnabled = False
        self.avoidanceOn = False

        carb.log_info("Character name is {}".format(self.character_name))
        self.character = None
        self.current_command = None
        self.loop_commands = None
        self.navigation_manager = None
        self.global_character_manager = None
        self.commands = []
        self.command_execution_failed = False

    # force the character to end current command
    def end_current_command(self):
        if self.current_command is not None:
            self.current_command.force_quit_command()

    def get_agent_name(self):
        return self.character_name

    def init_character(self):
        """
        Initializes global variables and fetches animation graph attached to the character. Called after entering runtime as ag.get_character() can only be used in runtime.
        """
        self.character = ag.get_character(str(self.prim_path))
        if self.character is None:
            return False

        self.global_character_manager = GlobalAgentManager.get_instance()
        self.global_character_manager.add_agent(str(self.prim_path), self)
        self.navigation_manager = NavigationManager(str(self.prim_path), self.navmeshEnabled, self.avoidanceOn)
        if not self.navigation_manager:
            return False

        self.commands = self.get_simulation_commands()

        # Add a GoTo back to the original position to form the loop.
        originPos, originRot = Utils.get_character_transform(self.character)
        originAngle = Utils.convert_to_angle(originRot)
        self.commands.append(["GoTo", str(originPos[0]), str(originPos[1]), str(originPos[2]), str(originAngle)])
        self.loop_commands = self.commands.copy()

        self.character.set_variable("Action", "None")
        carb.log_info("Initialize the character")
        return True

    def get_simulation_commands(self):
        # init_character() appends a GoTo back to the original position, so this
        # one target command creates the round-trip path.
        return [["GoTo", "2.5", "0.0", "0.0", "0"]]

    # get character's position
    def get_current_position(self):
        return Utils.get_character_pos(self.character)

    def get_command(self, command):
        """
        Returns an instance of a command object based on the command.

        :param list[str] command: list of strings describing the command.
        :return: instance of a command object.
        :rtype: python object
        """
        if command[0] == "GoTo":
            return GoTo(self.character, command, self.navigation_manager)

        carb.log_error("Unsupported command: {}".format(command[0]))
        return None

    def get_origin_command_string(self, command):
        line = self.character_name
        for str in command:
            if str != self.character_name:
                line = line + " " + str
        return line

    def execute_command(self, commands, delta_time):
        """
        Executes commands in commands list in sequence. Removes a command once completed.

        :param list[list] commands: list of commands.
        :param float delta_time: time elapsed since last execution.
        """
        while not self.current_command:
            if not commands:
                return
            next_cmd = self.get_command(commands[0])
            if next_cmd:
                self.current_command = next_cmd
            else:
                commands.pop(0)  # Skip the command that cannot be executed
        try:
            if self.current_command.execute(delta_time):
                commands.pop(0)
                self.current_command = None
        except Exception as error:
            carb.log_error(
                "{}: command execution failed: {!r}".format(
                    self.get_origin_command_string(self.current_command.command), error
                )
            )
            self.current_command.exit_command()
            commands.pop(0)
            self.current_command = None
            # Do not reload a broken infinite loop on every frame.
            self.command_execution_failed = True

    def on_update(self, current_time: float, delta_time: float):
        """
        Called on every update. Initializes character at start, publishes character positions and executes character commands.
        :param float current_time: current time in seconds.
        :param float delta_time: time elapsed since last update.
        """
        if self.character is None:
            if not self.init_character():
                return

        if self.commands:
            self.execute_command(self.commands, delta_time)

        elif not self.command_execution_failed and self.loop_commands:
            self.commands = self.loop_commands.copy()
