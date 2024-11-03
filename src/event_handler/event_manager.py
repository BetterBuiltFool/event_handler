from __future__ import annotations

import logging
import threading
from typing import Callable, Optional

import pygame

logger = logging.getLogger(__name__)


class EventManager:
    handlers: dict[str, EventManager] = {}

    def __init__(self, handle: str) -> None:
        self.handle = handle
        self.listeners: dict[int, list[Callable]] = {}

    def register(self, event_type: int):
        def decorator(listener: Callable):
            self.listeners.setdefault(event_type, []).append(listener)
            return listener
        return decorator

    def deregister(self, func: Callable, event_type: Optional[int] = None):
        """
        Remove the given function from the specified event type. If no event
        type is specified, the function is cleared from all events.

        :param func: Function to be removed from the register.
        :param event_type: Pygame event type to which the function is to be
        removed, defaults to None
        """
        if event_type is not None:
            call_list = self.listeners.get(event_type)
            if not call_list:
                logger.warning(
                    "No functions are registered to "
                    f"{pygame.event.event_name(event_type)}"
                )
                return
            if func not in call_list:
                logger.warning(
                    f"Function \'{func.__name__} is not bound to "
                    f"{pygame.event.event_name(event_type)}"
                )
                return
            call_list.remove(func)
        else:
            for event, call_list in self.listeners.items():
                if func in call_list:
                    logger.info(
                        f"Removing function \'{func.__name__} from "
                        f"{pygame.event.event_name(event)}"
                    )
                    call_list.remove(func)

    def purge_event(self, event_type: int):
        """
        Attempts to clear all functions from the specified event.

        :param event_type: Pygame event type
        """
        call_list = self.listeners.get(event_type)
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

    def notify(self, event: pygame.Event):
        """
        Finds all listeners for a given event, and calls them in a new thread

        :param event: _description_
        """
        listeners = self.listeners.get(event.type, [])
        for listener in listeners:
            threading.Thread(target=listener, args=(event,)).start()

    @classmethod
    def notify_all(cls, event: pygame.Event):
        """
        Passes on the event to all know handlers.

        :param event: Pygame-generated event that is being handled.
        """
        for event_handler in cls.handlers.values():
            event_handler.notify(event)

    @classmethod
    def getEventManager(cls, handle: str) -> EventManager:
        """
        Finds the handler that matches the given handle.
        If one does not exist, it is created.
        """
        return cls.handlers.setdefault(handle, EventManager(handle))
