from abc import ABC  # , abstractmethod
from typing import Callable


class BaseManager(ABC):

    def sequential(self, func: Callable) -> Callable:
        """
        Marks a function as to be run sequentially.
        Removes a concurrent mark if one exists.

        :param func: The function to be tagger
        :return: the tagged function
        """
        if hasattr(func, "_runs_concurrent"):
            delattr(func, "_runs_concurrent")
        setattr(func, "_runs_sequential", True)
        return func

    def concurrent(self, func: Callable) -> Callable:
        """
        Marks a function as to be run concurrently via threading.
        Removes a sequential mark if one exists.

        :param func: The function to be tagger
        :return: the tagged function
        """
        if hasattr(func, "_runs_sequential"):
            delattr(func, "_runs_sequential")
        setattr(func, "_runs_concurrent", True)
        return func
