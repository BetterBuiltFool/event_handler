from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import pygame

logger: logging.Logger = logging.getLogger(__name__)


class EventManager:
    handlers: dict[str, EventManager] = {}

    def __init__(self, handle: str) -> None:
        self.handle: str = handle
        self._listeners: dict[int, list[Callable]] = {}

    def register(self, event_type: int) -> Callable:
        def decorator(listener: Callable) -> Callable:
            self._listeners.setdefault(event_type, []).append(listener)
            return listener
        return decorator

    def deregister(self,
                   func: Callable,
                   event_type: Optional[int] = None
                   ) -> None:
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
                    f"Function \'{func.__name__}\' is not bound to "
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
                    f"Removing function \'{func.__name__}\' from "
                    f"{pygame.event.event_name(event)}"
                )
                call_list.remove(func)

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
