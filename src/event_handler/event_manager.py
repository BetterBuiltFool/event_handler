from __future__ import annotations

import logging
import threading
from typing import Callable, Optional, Type
from weakref import WeakSet

from .base_manager import BaseManager

import pygame

logger: logging.Logger = logging.getLogger(__name__)


class EventManager(BaseManager):
    handlers: dict[str, EventManager] = {}

    def __init__(self, handle: str) -> None:
        super().__init__(handle)

        # --------Basic function assignment--------
        # Pygame event as key, list of functions as values
        self._listeners: dict[int, dict[bool, list[Callable]]] = {}

        # --------Class method assignment--------
        # Pygame event key, method and affected object as values
        self._class_listeners: dict[
            int, dict[bool, list[tuple[Callable, Type[object]]]]
        ] = {}
        # Inversion of _class_listeners. Method as key, event id as values
        self._class_listener_events: dict[Callable, list[int]] = {}

    def register(self, event_type: int) -> Callable:
        def decorator(listener: Callable) -> Callable:
            is_concurrent = not hasattr(listener, "_runs_sequential")
            event_dict = self._listeners.setdefault(event_type, {})
            concurrency_list = event_dict.setdefault(is_concurrent, [])
            concurrency_list.append(listener)
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
            event_dict = self._listeners.get(event_type)
            if not event_dict:
                logger.warning(
                    "No functions are registered to "
                    f"{pygame.event.event_name(event_type)}"
                )
                return
            found = False
            for call_list in event_dict.values():
                if func not in call_list:
                    continue
                found = True
                call_list.remove(func)
            if not found:
                logger.warning(
                    f"Function '{func.__name__}' is not bound to "
                    f"{pygame.event.event_name(event_type)}"
                )
            return
        for event_dict in self._listeners.values():
            if not event_dict:
                continue
            for call_list in event_dict.values():
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

    def _add_instance(self, cls, instance):
        self._class_listener_instances.setdefault(cls, WeakSet()).add(instance)

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
        for event_type in self._class_listener_events.get(method, []):
            event_dict = self._class_listeners.get(event_type, {})
            for concurrency, listener_sets in event_dict.items():
                # Retain only the listeners that are not the method
                listener_sets = list(
                    filter(
                        lambda listener_set: method is not listener_set[0],
                        listener_sets,
                    )
                )
                event_dict.update({concurrency: listener_sets})
            self._class_listeners.update({event_type: event_dict})
        self._class_listener_events.pop(method)

    def purge_event(self, event_type: int) -> None:
        """
        Attempts to clear all functions from the specified event.

        :param event_type: Pygame event type
        """
        self._listeners.pop(event_type, None)
        self._class_listeners.pop(event_type, None)
        # This really simplified things, no?

    def notify_concurrent(self, event):
        functions = self._listeners.get(event.type, {})
        concurrent_funcs = functions.get(True, [])
        methods = self._class_listeners.get(event.type, {})
        concurrent_methods = methods.get(True, [])

        for function in concurrent_funcs:
            threading.Thread(target=function, args=(event,)).start()
        for method, cls in concurrent_methods:
            instances = self._class_listener_instances.get(cls, WeakSet())
            for instance in instances:
                threading.Thread(target=method, args=(instance, event)).start()

    def notify_sequential(self, event):
        functions = self._listeners.get(event.type, {})
        sequential_funcs = functions.get(False, [])
        methods = self._class_listeners.get(event.type, {})
        sequential_methods = methods.get(False, [])

        for function in sequential_funcs:
            function(event)
        for method, cls in sequential_methods:
            instances = self._class_listener_instances.get(cls, WeakSet())
            for instance in instances:
                method(instance, event)


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
