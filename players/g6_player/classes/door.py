from constants import *
from math import gcd
import numpy as np
from array import ArrayType


class Door:
    def __init__(self, door_type: int, max_door_freq: int) -> None:
        self.door_type: int = door_type
        self.state: int = CLOSED
        self.max_door_freq: int = max_door_freq
        self.freq: int = 0
        self.cycles_observed: ArrayType[int] = np.zeros(max_door_freq)
        self.complete_observed: bool = False
        self.cycles_open: list[int] = []

    def update_turn(self, state: int, cycle: int):
        """
        Called on every turn
        """

        if not self.complete_observed:
            # Track which turn cycles we have observed this door at
            self.cycles_observed[cycle - 1] = 1
            if self.cycles_observed.sum() == self.max_door_freq:
                self.complete_observed = True

            if state == OPEN:
                self.cycles_open.append(cycle)
                if len(self.cycles_open) > 0:
                    self.__update_freq()
        else:
            pass

    def __update_freq(self):
        """
        Update frequency of door based on previous cycles when open door was detected open
        """
        self.freq = gcd(*self.cycles_open)

