from __future__ import annotations

import logging
from typing import Callable, Optional, Type

from .base_manager import BaseManager, _CallableSets

import pygame

logger: logging.Logger = logging.getLogger(__name__)


class EventManager(BaseManager):
    handlers: dict[str, EventManager] = {}

    def __init__(self, handle: str) -> None:
        super().__init__(handle)

        # --------Basic function assignment--------
        # Pygame event as key, list of functions as values
        self._listeners: dict[tuple[int, bool], list[Callable]] = {}

        # --------Class method assignment--------
        # Pygame event key, method and affected object as values
        self._class_listeners: dict[
            tuple[int, bool], list[tuple[Callable, Type[object]]]
        ] = {}
        # Inversion of _class_listeners. Method as key, event id as values
        self._class_listener_events: dict[Callable, list[int]] = {}

    def register(self, event_type: int) -> Callable:
        """
        Takes a callable item such as a function, and places it in the appropriate set
        of functions with the target event. Whenever the event manager is notified of
        the compatible event type, it will call the function.

        :param event_type: Pygame event code
        :return: Returns the registered callable, unchanged.
        """

        def decorator(listener: Callable) -> Callable:
            is_concurrent = not hasattr(listener, "_runs_sequential")
            event_list = self._listeners.setdefault((event_type, is_concurrent), [])
            event_list.append(listener)
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
        for (event, _), call_list in self._listeners.items():
            if event_type is not None and event != event_type:
                continue
            if func in call_list:
                call_list.remove(func)

    def _capture_method(self, cls, method, tag_data):
        """
        Adds the method, class, and event into the appropriate dictionaries to ensure
        they can be properly notified.

        :param cls: Class of the object being processed
        :param method: Callable being captured
        :param tag_data: A tuple containing pertinent registration data
        """
        is_concurrent = not hasattr(method, "_runs_sequential")
        event_type = tag_data[0]  # Only piece of data

        # -----Add to Class Listeners-----
        event_dict = self._class_listeners.setdefault(event_type, {})
        concurrency_list = event_dict.setdefault(is_concurrent, [])
        concurrency_list.append((method, cls))

        # -----Add to Class Listener Events-----
        self._class_listener_events.setdefault(method, []).append(event_type)

        # -----Add to Assigned Classes-----
        self._assigned_classes.setdefault(cls, []).append(method)

    def register_method(self, event_type: int) -> Callable:
        """
        Wrapper that marks the method for registration when the class is registered.

        The method's class should be registered with all event managers that have
        registered a method in that class. Failure to do so will leave a dangling
        attribute on those methods.

        :param event_type: Pygame event type that will call the assigned method.
        """

        def decorator(method: Callable) -> Callable:
            return self._tag_method(method, (event_type,))

        return decorator

    def deregister_class(self, cls: Type[object]):
        """
        Clears all instances and listeners that belong to the supplied class.

        :param cls: The cls being deregistered.
        :raises KeyError: If cls is not contained in the class listeners, this
        error will be raised.
        """
        # Purge instances
        self._class_listener_instances.pop(cls, None)
        # Remove methods from events
        for method in self._assigned_classes.get(cls, []):
            self.deregister_method(method)
        self._assigned_classes.pop(cls)

    def deregister_method(self, method: Callable):
        """
        Clears the method from the registry so it is no longer called when the assigned
        event is fired.

        :param method: Method whose registration is being revoked.
        """
        for (event_type, is_concurrent), listener_set in self._class_listeners.items():
            listener_set = list(
                filter(
                    lambda call_list: method is not call_list[0],
                    listener_set,
                )
            )
            self._class_listeners.update({(event_type, is_concurrent): listener_set})
        self._class_listener_events.pop(method)

    def purge_event(self, event_type: int) -> None:
        """
        Attempts to clear all functions from the specified event.

        :param event_type: Pygame event type
        """
        to_remove: list[tuple[int, bool]] = []
        for event, is_concurrent in self._listeners.keys():
            if event == event_type:
                to_remove.append((event, is_concurrent))
        for key in to_remove:
            # Not including default value since the keys came directly from the
            # dictionary and shouldn't be absent
            # If this errors, it suggests another process is deleting the key first,
            # which could be causing other issues.
            self._listeners.pop(key, None)

        to_remove = []
        for event, is_concurrent in self._class_listeners.keys():
            if event == event_type:
                to_remove.append((event, is_concurrent))
        for key in to_remove:
            self._class_listeners.pop(key, None)

    def _get_callables(self, event) -> _CallableSets:
        return _CallableSets(
            concurrent_functions=self._listeners.get((event.type, True), []),
            sequential_functions=self._listeners.get((event.type, False), []),
            concurrent_methods=self._class_listeners.get((event.type, True), []),
            sequential_methods=self._class_listeners.get((event.type, False), []),
        )


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

    :param handle: A string for identifying an event manager instance.
    """
    return EventManager.handlers.setdefault(handle, EventManager(handle))
