import numpy as np
import logging
import random
import constants

from players.g6_player.data import Move
from timing_maze_state import TimingMazeState


class G6_Player:
    def __init__(
        self,
        rng: np.random.Generator,
        logger: logging.Logger,
        precomp_dir: str,
        maximum_door_frequency: int,
        radius: int,
    ) -> None:
        """Initialise the player with the basic amoeba information
        Args:
            maximum_door_frequency (int): the maximum frequency of doors
            radius (int): the radius of the drone
        """

        self.rng = rng
        self.logger = logger
        self.maximum_door_frequency = maximum_door_frequency
        self.radius = radius
        self.known_target = False
        # Data structure to hold state information about the doors inside the radius
        self.curr_maze = {}
        self.seen = np.zeros((100, 100))
        self.curr_pos = (0, 0)
        self.turn = 0

        # a random unseen cell which the agent tries to navigate towards
        self.search_target = (0, 0)

        # the horizontal (1st idx) and vertical (2nd idx) edge indices
        self.edges = [None, None]

        # tracking variables for inward spiral
        self.phase = 0
        self.layer = 0

    def move(self, current_percept: TimingMazeState) -> int:
        self.turn += 1

        self.__update_maze(current_percept)

        # seen_count = np.sum(self.seen)

        movement = self.__move(current_percept)
        self.__update_curr_pos(movement)

        return movement.value

    def __move(self, current_percept: TimingMazeState) -> Move:
        if not current_percept.is_end_visible:
            # SEARCH FOR TARGET
            return self.__explore()

        # GO TO TARGET
        return self.__exploit(current_percept)

    def __update_maze(self, curr_state: TimingMazeState):
        # Update current maze with new info from the drone
        for cell in curr_state.maze_state:
            cell_row = (cell[0] + self.curr_pos[0]) % 100
            cell_col = (cell[1] + self.curr_pos[1]) % 100

            self.seen[cell_row][cell_col] = True

            self.__update_edges(cell)

    def __update_edges(self, cell):
        # if we haven't found both edges...
        if self.edges[0] is None or self.edges[1] is None:
            # ... and the cell is a boundary
            # update the boundaries
            if cell[3] == constants.BOUNDARY:
                if self.edges[0] is None and cell[2] in (
                    constants.LEFT,
                    constants.RIGHT,
                ):
                    self.edges[0] = cell[0] + self.curr_pos[0]
                elif self.edges[1] is None and cell[2] in (
                    constants.UP,
                    constants.DOWN,
                ):
                    self.edges[1] = cell[1] + self.curr_pos[1]

    def __convert_state(self, curr_state: TimingMazeState):
        # Update self.curr_maze with new state information
        pass

    def __update_curr_pos(self, movement: Move):
        # TODO: If our move is banned by the simulator, we need to reverse our position
        match movement:
            case Move.LEFT:
                self.curr_pos = (
                    (self.curr_pos[0] - 1) % 100,
                    self.curr_pos[1] % 100,
                )
            case Move.RIGHT:
                self.curr_pos = (
                    (self.curr_pos[0] + 1) % 100,
                    self.curr_pos[1] % 100,
                )
            case Move.UP:
                self.curr_pos = (
                    (self.curr_pos[0]) % 100,
                    (self.curr_pos[1] - 1) % 100,
                )
            case Move.DOWN:
                self.curr_pos = (
                    (self.curr_pos[0]) % 100,
                    (self.curr_pos[1] + 1) % 100,
                )

    def __explore(self) -> Move:
        """
        Move towards the southeast corner and perform inward spiral
        """
        found_right_boundary = True if self.curr_pos[0] == self.edges[0] else False
        found_down_boundary = True if self.curr_pos[1] == self.edges[1] else False
        if not found_right_boundary:
            return self.find_boundary(constants.RIGHT)
        if not found_down_boundary:
            return self.find_boundary(constants.DOWN)
        return self.inward_spiral()

    def find_boundary(self, direction) -> Move:
        """
        Traverse to right/down boundary by setting search target to the farthest right/down
        direction. If edge is detected between current position and search target, set
        search target to edge.
        """
        if direction == constants.RIGHT:
            self.search_target = (constants.map_dim-1, 0)
            if self.edges is not None and self.__border_between_target_and_curr(
                self.edges[0], self.search_target[0], self.curr_pos[0]
            ):
                self.search_target[0] = self.edges[0]
            return Move.RIGHT
        
        if direction == constants.DOWN:
            self.search_target = (0, constants.map_dim-1)
            if self.edges is not None and self.__border_between_target_and_curr(
                self.edges[1], self.search_target[1], self.curr_pos[1]
            ):
                self.search_target[1] = self.edges[1]
            return Move.DOWN

    def inward_spiral(self):
        """
        Perform clockwise inward spiral from southeast corner.
        """
        # Set inward spiral phase and layer, and update search target
        if self.curr_pos == self.search_target:
            self.adjust_phase_and_target()
        
        return self.__find_best_move_towards_search_target()

    def adjust_phase_and_target(self):
        if self.phase + 1 == 5:
            self.layer += 1
        self.phase = (self.phase + 1) % 5
        
        # Set search target so that radius touches southeast corner of previous layer
        if self.phase == 0:
            offset = int(np.floor(self.radius / np.sqrt(2)))
            offset = 2 * offset if self.layer > 0 else offset
            self.search_target = (self.curr_pos[0] - offset, self.curr_pos[1] - offset)    

        # Set search target so that radius touches southwest corner of previous layer
        elif self.phase == 1:
            offset = constants.map_dim - (int(np.floor(self.radius / np.sqrt(2))) * 2 +
                                          4 * self.radius * self.layer)
            self.search_target[0] = self.curr_pos[0] - offset

        # Set search target so that radius touches northwest corner of previous layer
        elif self.phase == 2:
            offset = constants.map_dim - (int(np.floor(self.radius / np.sqrt(2))) * 2 +
                                          4 * self.radius * self.layer)
            self.search_target[1] = self.curr_pos[1] - offset

        # Set search target so that radius touches northeast corner of previous layer
        elif self.phase == 3:
            offset = constants.map_dim - (int(np.floor(self.radius / np.sqrt(2))) * 2 +
                                          4 * self.radius * self.layer)
            self.search_target[0] = self.curr_pos[0] + offset

        # Set search target so that radius touches southeast corner of previous layer
        elif self.phase == 4:
            offset = constants.map_dim - (int(np.floor(self.radius / np.sqrt(2))) * 2 +
                                          4 * self.radius * self.layer)
            self.search_target[1] = self.curr_pos[1] + offset

    # def __explore(self) -> Move:
    #     # if the current search target has been found
    #     # find a new target
    #     if self.seen[self.search_target[0], self.search_target[1]]:
    #         self.__calculate_new_target()

    #     return self.__find_best_move_towards_search_target()

    def __find_best_move_towards_search_target(self) -> Move:
        """
        Given an unexplored search target at self.search_target,
        Finds the best move towards that target
        Considers borders and selects a nice pythagorean route instead of straight lines
        (even though it doesn't really matter)
        """
        horizontal_dist = self.search_target[0] - self.curr_pos[0]
        vertical_dist = self.search_target[1] - self.curr_pos[1]

        # prioritize the axis with a greater distance
        # for no real reason other than it looks nicer
        # (and might be better later on)
        if abs(horizontal_dist) >= abs(vertical_dist):
            # search target is to the right
            if horizontal_dist >= 0:
                # check whether the border is between the target and current,
                # if so, go the other direction
                if self.edges[0] is not None and self.__border_between_target_and_curr(
                    self.edges[0], self.search_target[0], self.curr_pos[0]
                ):
                    return Move.LEFT
                return Move.RIGHT
            else:
                if self.edges[0] is not None and self.__border_between_target_and_curr(
                    self.edges[0], self.search_target[0], self.curr_pos[0]
                ):
                    return Move.RIGHT
                return Move.LEFT
        else:
            # search target is to the south
            if vertical_dist >= 0:
                if self.edges[1] is not None and self.__border_between_target_and_curr(
                    self.edges[1], self.search_target[1], self.curr_pos[1]
                ):
                    return Move.UP
                return Move.DOWN
            else:
                if self.edges[1] is not None and self.__border_between_target_and_curr(
                    self.edges[1], self.search_target[1], self.curr_pos[1]
                ):
                    return Move.DOWN
                return Move.UP

    def __calculate_new_target(self):
        """
        Calculates a new search target for the agent to navigate towards
        """
        new_row = self.rng.integers(0, 100)
        new_col = self.rng.integers(0, 100)
        # TODO: this gets very inefficient when more cells have been explored
        # For a certain threshold of explored cells, this should be dropped
        # But this is not meant to be performant.
        while self.seen[new_row][new_col]:
            new_row = self.rng.integers(0, 100)
            new_col = self.rng.integers(0, 100)

        self.search_target = (new_row, new_col)
        print(f"NEW TARGET: {self.search_target}")

    def __border_between_target_and_curr(
        self, border: int, target: int, curr: int
    ) -> bool:
        """
        Takes a target coordinate, border coordinate and current coordinate.
        Returns True if the border is between the target and current

        Let's consider an example using the x-axis:
        you're at [25, x] and want to get to [45, x], but the horizontal border is at 35. Then your global coordinates (in x-axis)
        are [89, x], and the target is really at [9, x]. You must go the opposite way to approach the target, LEFT from [25, x] to [-55, x]
        """

        # check whether the border is between the target and current
        return sorted([target, border, curr])[1] == border

    def __exploit(self, current_state: TimingMazeState) -> Move:
        if random.random() < 0.1:
            return random.choice(list(Move))

        if 0 > current_state.end_x:
            return Move.LEFT

        if 0 < current_state.end_x:
            return Move.RIGHT

        if 0 > current_state.end_y:
            return Move.UP

        if 0 < current_state.end_y:
            return Move.DOWN

        return Move.WAIT
