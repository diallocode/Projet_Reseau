from abc import ABC, abstractmethod
from model.Battlefield import Battlefield

class View(ABC):

    @abstractmethod
    def update(self):
        pass

    @abstractmethod
    def set_winner(self, winner_name):
        pass
