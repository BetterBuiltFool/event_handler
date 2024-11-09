from __future__ import annotations

import functools
import logging
import threading
from typing import Callable, Optional, Type

import pygame

logger: logging.Logger = logging.getLogger(__name__)


class EventManager:
    handlers: dict[str, EventManager] = {}

    def __init__(self, handle: str) -> None:
        self.handle: str = handle
        self._listeners: dict[int, list[Callable]] = {}
        self._class_listeners: dict[int, list[tuple[Callable, Type[object]]]] = {}
        self._class_listener_instances: dict[Type[object], list[object]] = {}

    def register(self, event_type: int) -> Callable:
        def decorator(listener: Callable) -> Callable:
            self._listeners.setdefault(event_type, []).append(listener)
            return listener

        return decorator

    def deregister(self, func: Callable, event_type: Optional[int] = None) -> None:
        """
        Remove the given function from the specified event type. If no event
        type is specified, the function is cleared from all events.

        :param func: Function to be removed from the register.
        :param event_type: Pygame event type to which the function is to be
        removed, defaults to None
        """
        call_list: list[Callable] | None
        if event_type is not None:
            call_list = self._listeners.get(event_type)
            if not call_list:
                logger.warning(
                    "No functions are registered to "
                    f"{pygame.event.event_name(event_type)}"
                )
                return
            if func not in call_list:
                logger.warning(
                    f"Function '{func.__name__}' is not bound to "
                    f"{pygame.event.event_name(event_type)}"
                )
                return
            call_list.remove(func)
            return
        event: int
        for event, call_list in self._listeners.items():
            if not call_list:
                continue
            if func in call_list:
                logger.info(
                    f"Removing function '{func.__name__}' from "
                    f"{pygame.event.event_name(event)}"
                )
                call_list.remove(func)

    def register_class(self, cls: Type[object]) -> Type[object]:
        """
        Prepares a class for event handling.
        This will hijack the class's init method to push its instances into
        the assigned event manager.

        It will also go through and clean up the assigned methods.
        """
        # Mypy will throw an error here because it thinks this is illegal.
        # Hijacking an init is illegal? Guess I'm going to jail then.
        cls.__init__ = self._modify_init(cls.__init__)  # type: ignore
        # Add all of the tagged methods to the callables list
        logger.debug("Checking for marked methods")
        for _, method in cls.__dict__.items():
            if not hasattr(method, "_assigned_doers"):
                continue
            logger.debug("Found marked method")
            assigned_doers: list[tuple[EventManager, int]] = getattr(
                method, "_assigned_managers", []
            )
            for index, (manager, event_type) in enumerate(assigned_doers):
                logger.debug(f"Found assigned doer: {manager}")
                if manager is not self:
                    continue
                logger.debug("Found method assigned to self. Registering.")
                self._class_listeners.setdefault(event_type, []).append((method, cls))
                assigned_doers.pop(index)
                break
            if len(assigned_doers) == 0:
                delattr(method, "_assigned_doers")

        return cls

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
            self._class_listener_instances.setdefault(cls, []).append(instance)
            logger.debug(f"Extracted instance {instance} from {cls}")
            return init(*args, **kwds)

        return wrapper

    def register_method(self, event_type: int) -> Callable:
        """
        Allows for

        :param event_type: _description_
        :return: _description_
        """

        def decorator(method: Callable) -> Callable:
            assigned_managers: list[tuple[EventManager, int]] = []
            if hasattr(method, "_assigned_managers"):
                assigned_managers = getattr(method, "_assigned_managers", [])
            assigned_managers.append((self, event_type))
            setattr(method, "_assigned_managers", assigned_managers)
            print(getattr(method, "_assigned_managers", []))
            return method

        return decorator

    def deregister_class(self, cls: Type[object]):
        """
        Clears all instances and listeners that belong to the supplied class.

        :param cls: The cls being deregistered.
        :raises KeyError: If cls is not contained in the class listeners, this
        error will be raised.
        """

    def purge_event(self, event_type: int) -> None:
        """
        Attempts to clear all functions from the specified event.

        :param event_type: Pygame event type
        """
        call_list: list[Callable] | None = self._listeners.get(event_type)
        if not call_list:
            logger.warning(
                f"Cannot purge event {pygame.event.event_name(event_type)}./n"
                "Event has no registered functions."
            )
            return
        logger.info(
            "Clearing all functions from event "
            f"{pygame.event.event_name(event_type)}"
        )
        call_list.clear()

    def notify(self, event: pygame.Event) -> None:
        """
        Finds all listeners for a given event, and calls them in a new thread

        :param event: _description_
        """
        listeners: list[Callable] = self._listeners.get(event.type, [])
        for listener in listeners:
            threading.Thread(target=listener, args=(event,)).start()
        methods = self._class_listeners.get(event.type, [])
        for method, cls in methods:
            instances = self._class_listener_instances.get(cls, [])
            for instance in instances:
                threading.Thread(target=method, args=(instance, event)).start()


def notifyEventManagers(event: pygame.Event) -> None:
    """
    Passes on the event to all existing EventManagers.

    :param event: Pygame-generated event that is being handled.
    """
    for event_handler in EventManager.handlers.values():
        event_handler.notify(event)


def getEventManager(handle: str) -> EventManager:
    """
    Finds the handler that matches the given handle.
    If one does not exist, it is created.
    """
    return EventManager.handlers.setdefault(handle, EventManager(handle))
