from __future__ import annotations

import threading
from typing import Callable

import pygame


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
