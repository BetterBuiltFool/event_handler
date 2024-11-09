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

        # --------Basic function assignment--------
        # Pygame event as key, list of functions as values
        self._listeners: dict[int, list[Callable]] = {}

        # --------Class method assignment--------
        # Pygame event key, method and affected object as values
        self._class_listeners: dict[int, list[tuple[Callable, Type[object]]]] = {}
        # Registered object as key, instances of object as values
        self._class_listener_instances: dict[Type[object], list[object]] = {}
        # Inversion of _class_listeners. Method as key, event id as values
        self._class_listener_events: dict[Callable, list[int]] = {}
        # Assigned object as key, associated methods as values
        self._assigned_classes: dict[Type[object], list[Callable]] = {}

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
            if not hasattr(method, "_assigned_managers"):
                continue
            logger.debug("Found marked method")
            _assigned_managers: list[tuple[EventManager, int]] = getattr(
                method, "_assigned_managers", []
            )
            self._verify_manager(cls, method, _assigned_managers)
            if len(_assigned_managers) == 0:
                # We cleaned up the assignments to this handler, but other handlers
                # might have yet to check. If all have cleaned up, we can remove the
                # hanging attribute.
                delattr(method, "_assigned_managers")
                # Now there's no sign we modified the method.

        return cls

    def _verify_manager(
        self,
        cls: Type[object],
        method: Callable,
        managers: list[tuple[EventManager, int]],
    ) -> None:
        """
        Checks the list of assigned managers for a method and captures it if it is
        assigned to the calling manager

        :param cls: Class of the object being processed
        :param method: Callable being registered
        :param managers: list of managers and pygame events being processed.
        """
        _indexes_to_remove: list[int] = []
        for index, (manager, event_type) in enumerate(managers):
            logger.debug(f"Found assigned manager: {manager}")
            if manager is not self:
                continue
            self._capture_method(cls, method, event_type)
            # Whoops, undefined behavior
            # managers.pop(index)
            _indexes_to_remove.append(index)
            break
        # Need to clean up the processed indices to we can remove the tag attribute
        # from the method.
        for index in reversed(_indexes_to_remove):
            managers.pop(index)

    def _capture_method(
        self, cls: Type[object], method: Callable, event_type: int
    ) -> None:
        """
        Adds the method, class, and event into the appropriate dictionaries to ensure
        they can be properly notified.

        :param cls: Class of the object being processed
        :param method: Callable being registered
        :param managers: list of managers and pygame events being processed.
        """
        logger.debug("Found method assigned to self. Registering.")
        logger.debug(f"Registering {method} to {pygame.event.event_name(event_type)}")
        self._class_listeners.setdefault(event_type, []).append((method, cls))
        self._class_listener_events.setdefault(method, []).append(event_type)
        self._assigned_classes.setdefault(cls, []).append(method)

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
        Wrapper that marks the method for registration when the class is registered.

        :param event_type: Pygame event type that will call the assigned method.
        """

        def decorator(method: Callable) -> Callable:
            # Tagging a method with an attribute for later reading?
            # This reeks of "cleverness"
            # Hope it's not too clever for me to debug.

            # Although I suppose if you're reading this, it got published, which means
            # I got it to work properly.
            assigned_managers: list[tuple[EventManager, int]] = []
            if hasattr(method, "_assigned_managers"):
                # Deja vu? This isn't the first assignment, so we need to pull the
                # previous ones first.
                assigned_managers = getattr(method, "_assigned_managers", [])
            assigned_managers.append((self, event_type))
            setattr(method, "_assigned_managers", assigned_managers)
            return method

        return decorator

    def deregister_class(self, cls: Type[object]):
        """
        Clears all instances and listeners that belong to the supplied class.

        :param cls: The cls being deregistered.
        :raises KeyError: If cls is not contained in the class listeners, this
        error will be raised.
        """

    def deregister_method(self, method: Callable):
        """
        Clears the method from the registry so it is no longer called when the assigned
        event is fired.

        :param method: Method whose registration is being revoked.
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
