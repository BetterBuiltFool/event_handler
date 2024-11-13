from __future__ import annotations

from abc import ABC, abstractmethod
import functools
from typing import Callable, Type
from weakref import WeakSet

import pygame


class BaseManager(ABC):

    def __init__(self, handle: str) -> None:
        self.handle: str = handle
        # Registered object as key, instances of object as values
        self._class_listener_instances: dict[Type[object], WeakSet[object]] = {}
        # Assigned object as key, associated methods as values
        self._assigned_classes: dict[Type[object], list[Callable]] = {}

    def sequential(self, func: Callable) -> Callable:
        """
        Marks a function as to be run sequentially.

        :param func: The function to be tagged
        :return: the tagged function
        """
        # None is smallest data type at 16 bytes
        # Lowest impact from being attached long term.
        setattr(func, "_runs_sequential", None)
        return func

    def concurrent(self, func: Callable) -> Callable:
        """
        Marks a function as to be run concurrently via threading.
        Removes a sequential mark if one exists.

        :param func: The function to be cleared
        :return: the cleared function
        """
        if hasattr(func, "_runs_sequential"):
            delattr(func, "_runs_sequential")
        return func

    def register_class(self, cls: Type[object]) -> Type[object]:
        """
        Prepares a class for event handling.
        This will hijack the class's init method to push its instances to
        the registering body.

        It will also go through and clean up the assigned methods.
        """
        # Mypy will throw an error here because it thinks this is illegal.
        # Hijacking an init is illegal? Guess I'm going to jail then.
        cls.__init__ = self._modify_init(cls.__init__)  # type: ignore
        # Add all of the tagged methods to the callables list
        for method in cls.__dict__.values():
            if not hasattr(method, "_assigned_managers"):
                continue  # No point checking something untagged.
            _assigned_managers = getattr(method, "_assigned_managers", [])
            self._verify_manager(cls, method, _assigned_managers)
            if len(_assigned_managers) == 0:
                # We cleaned up the assignments to this handler, but other handlers
                # might have yet to check. If all have cleaned up, we can remove the
                # hanging attribute.
                delattr(method, "_assigned_managers")
                # Now there's no sign we modified the method.

        return cls

    def notify(self, event: pygame.Event) -> None:
        """
        Finds all listeners for a given event, and calls them in a new thread

        :param event: _description_
        """
        self.notify_concurrent(event)
        self.notify_sequential(event)

    @abstractmethod
    def notify_concurrent(self, event: pygame.Event) -> None: ...

    @abstractmethod
    def notify_sequential(self, event: pygame.Event) -> None: ...

    def _add_instance(self, cls: Type[object], instance: object) -> None:
        """
        Adds the instance into the collection of instances

        :param cls: The class of the instance
        :param instance: The new instance being captured
        """
        self._class_listener_instances.setdefault(cls, WeakSet()).add(instance)

    @abstractmethod
    def _capture_method(
        self, cls: Type[object], method: Callable, tag_data: tuple
    ) -> None: ...

    def _tag_method(self, method: Callable, tag_data: tuple) -> Callable:
        """
        Applies a tag attribute to a method that is being registered.

        :param method: Method being registered
        :param tag_data: Pertinent data for the concrete manager
        :return: The tagged method
        """
        # Tagging a method with an attribute for later reading?
        # This reeks of "cleverness"
        # Hope it's not too clever for me to debug.

        # Although I suppose if you're reading this, it got published, which means
        # I got it to work properly.
        assigned_managers: list[tuple[BaseManager, tuple]] = []
        if hasattr(method, "_assigned_managers"):
            # Deja vu? This isn't the first assignment, so we need to pull the
            # previous ones first.
            assigned_managers = getattr(method, "_assigned_managers", [])
        assigned_managers.append((self, tag_data))
        setattr(method, "_assigned_managers", assigned_managers)
        return method

    def _verify_manager(
        self,
        cls: Type[object],
        method: Callable,
        managers: list[tuple[BaseManager, tuple]],
    ) -> None:
        """
        Checks the list of assigned managers for a method and captures it if it is
        assigned to the calling manager

        :param cls: Class of the object being processed
        :param method: Method of cls being registered
        :param managers: list of managers and tag data.
        """
        _indexes_to_remove: list[int] = []
        for index, (manager, tag_data) in enumerate(managers):
            # A manager could be assigned multiple times for multiple events.
            if manager is not self:
                continue
            self._capture_method(cls, method, tag_data)
            # Whoops, undefined behavior
            # managers.pop(index)
            _indexes_to_remove.append(index)
            break
        # Need to clean up the processed indices to we can remove the tag attribute
        # from the method.
        for index in reversed(_indexes_to_remove):
            managers.pop(index)

    def _modify_init(self, init: Callable) -> Callable:
        """
        Extracts the class and instance being generated, and puts them into a
        dict, so that the method can be called upon it

        :param init: The initializer function of a class being registered.
        :return: The modified init function
        """
        functools.wraps(init)  # Needs this

        def wrapper(*args, **kwds):
            # args[0] of a non-class, non-static method is the instance
            # This is called whenever the class is instantiated,
            # and the instance is extracted and can be stored
            instance = args[0]
            cls = instance.__class__
            # No need to check for the instance, each only calls this once
            self._add_instance(cls, instance)
            # self._class_listener_instances.setdefault(cls, WeakSet()).add(instance)
            return init(*args, **kwds)

        return wrapper
