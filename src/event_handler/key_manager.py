from __future__ import annotations

from abc import ABC, abstractmethod
import functools
import logging
from pathlib import Path
import threading
from typing import Callable, Optional, TextIO, Type
from weakref import WeakSet

# import file_parser
from .key_map import KeyBind, KeyMap

import pygame

logger: logging.Logger = logging.getLogger(__name__)


class FileParser(ABC):

    @staticmethod
    @abstractmethod
    def load(in_file: TextIO) -> KeyMap: ...

    @staticmethod
    @abstractmethod
    def save(key_map: KeyMap, out_file: TextIO) -> None: ...

    @staticmethod
    @abstractmethod
    def unpack_binds(maps: dict) -> KeyMap: ...


class KeyListener:
    _listeners: dict[str, KeyListener] = {}
    key_map: KeyMap = KeyMap()

    def __init__(self, handle: str) -> None:
        self.handle: str = handle

        # Workflow:
        # Key event -> send key to key map
        # Key map -> bind name, mod keys
        # Check mod keys, bind name -> dict w/ event types
        # Feed event type -> get callable
        # Call the callable

        # --------Basic function assignment--------
        # Meta dict, string bind name as key, then event type as key to get callable
        self._key_hooks: dict[str, dict[int, list[Callable]]] = {}

        # Workflow:
        # Key event -> send key to key map
        # Key map -> bind name, mod keys
        # Check mod keys, bind name -> dict w/ event types
        # Feed event type -> get callable
        # Call the callable

        # --------Class method assignment--------
        # Meta dict, string bind name as key, then Pygame event key, method and
        # affected object as values
        self._class_listeners: dict[
            str, dict[int, list[tuple[Callable, Type[object]]]]
        ] = {}
        # Registered object as key, instances of object as values
        # Instances are unique, so make it a set for weak reference
        self._class_listener_instances: dict[Type[object], WeakSet[object]] = {}
        # Inversion of _class_listeners. Method as key, bind name
        self._class_listener_binds: dict[Callable, list[str]] = {}
        # Assigned object as key, associated methods as values
        self._assigned_classes: dict[Type[object], list[Callable]] = {}

    def bind(
        self,
        key_bind_name: str,
        default_key: Optional[int] = None,
        default_mod: Optional[int] = None,
        event_type: int = pygame.KEYDOWN,
    ) -> Callable:
        """
        Adds a bind field to the key registry, and associates the following
        callable with that field so when the key associated with the field is
        pressed, the callable is called. If the field does not exist, it
        is created.

        :param key_bind_name: Reference name for the binding function.
        Callable events will be hooked by this name.
        :param default_key:
        Pygame key constant used to fill the registry if the bind doesn't
        exist or does not have an assigned key, defaults to None
        :param default_mod: Mod keys required for activating the key bind. None means
        the bind works with any mod keys pressed. pygame.KMOD_NONE means it requires no
        mod keys to be pressed. If using multiple, use bitwise OR to combine, defaults
        to None
        """
        self._generate_bind(key_bind_name, default_key, default_mod)

        def decorator(responder: Callable) -> Callable:
            # Regardless, add the responder to the bind within our hook dict
            hooks: dict[int, list[Callable]] = self._key_hooks.setdefault(
                key_bind_name, {}
            )
            listeners = hooks.setdefault(event_type, [])
            if responder not in listeners:
                listeners.append(responder)
            return responder

        return decorator

    def rebind(
        self,
        key_bind_name: str,
        new_key: int | None,
        new_mod: Optional[int] = None,
    ) -> tuple[int | None, int] | None:
        """
        Attempts to assign the new key info the the named bind.
        Generates a warning if the bind is not registered.

        :param key_bind_name: Name of the bind to be reassigned
        :param default_key: Pygame key to be assigned to
        :param default_mod: Pygame mod keys for assignment,
        defaults to None
        :return: A tuple containing the previous key and mod key
        """
        old_bind = self.key_map.get_bound_key(key_bind_name)
        if old_bind:
            logger.warning(
                f"Attempted to rebind '{key_bind_name}' when bind does not"
                " exist. \n Program might be attempting to rebind before"
                " generating binds, or bind name may be incorrect."
            )
            return None
        self.key_map.rebind(
            KeyBind(bind_name=key_bind_name, mod=new_mod), new_key=new_key
        )

        return old_bind

    def unbind(self, func: Callable, bind_name: Optional[str] = None) -> None:
        """
        Removes a callable from the given bind.

        :param func: A Callable previously registered with this Key Listener
        :param bind_name: The bind to be removed from, or all instances, if
        None. Defaults to None.
        """
        if bind_name:
            bind_dict = self._key_hooks.get(bind_name)
            if not bind_dict:
                logger.warning(
                    f"Bind name '{bind_name}' does not exist in KeyListener "
                    f"'{self.handle}'"
                )
                return
            for bind in bind_dict.values():
                if func not in bind:
                    logger.warning(
                        f"Cannot remove function {func.__name__} from '"
                        f"{bind_name}' of KeyListener: {self.handle}.\n"
                        f"Function is not bound to that name."
                    )
                    return
                bind.remove(func)
            return
        for name, bind_dict in self._key_hooks.items():
            if not bind_dict:
                continue
            for bind in bind_dict.values():
                if bind and func in bind:
                    logger.info(
                        f"Removing {func.__name__} from '{name}' in "
                        f"KeyListener: {self.handle}."
                    )
                    bind.remove(func)

    def register_class(self, cls: Type[object]) -> Type[object]:
        """
        Prepares a class for event handling.
        This will hijack the class's init method to push its instances into
        the assigned key listener.

        It will also go through and clean up the assigned methods.
        """
        cls.__init__ = self._modify_init(cls.__init__)  # type: ignore
        # Add all of the tagged methods to the callables list
        logger.debug("Checking for marked methods")
        for _, method in cls.__dict__.items():
            if not hasattr(method, "_assigned_listeners"):
                continue

            logger.debug("Found marked method")

            _assigned_listeners: list[
                tuple[KeyListener, str, int | None, int | None, int]
            ] = getattr(method, "_assigned_listeners", [])

            self._verify_listener(cls, method, _assigned_listeners)

            if len(_assigned_listeners) == 0:
                delattr(method, "_assigned_listeners")

        return cls

    def _verify_listener(
        self,
        cls: Type[object],
        method: Callable,
        listeners: list[tuple[KeyListener, str, int | None, int | None, int]],
    ) -> None:
        """
        Checks the list of assigned managers for a method and captures it if it is
        assigned to the calling manager

        :param cls: Class of the object being processed
        :param method: Callable being registered
        :param managers: list of managers and pygame events being processed.
        """
        _indexes_to_remove: list[int] = []
        for index, (
            listener,
            bind_name,
            default_key,
            default_mod,
            event_type,
        ) in enumerate(listeners):
            logger.debug(f"Found assigned manager: {listener}")
            if listener is not self:
                continue
            self._capture_method(
                cls, method, bind_name, default_key, default_mod, event_type
            )
            _indexes_to_remove.append(index)
            break
        for index in reversed(_indexes_to_remove):
            listeners.pop(index)

    def _capture_method(
        self,
        cls: Type[object],
        method: Callable,
        key_bind_name: str,
        default_key: int | None,
        default_mod: int | None,
        event_type: int,
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

        self._generate_bind(key_bind_name, default_key, default_mod)

        self._class_listeners.setdefault(key_bind_name, {}).setdefault(
            event_type, []
        ).append((method, cls))
        self._class_listener_binds.setdefault(method, []).append(key_bind_name)
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
            self._class_listener_instances.setdefault(cls, WeakSet()).add(instance)
            logger.debug(f"Extracted instance {instance} from {cls}")
            return init(*args, **kwds)

        return wrapper

    def bind_method(
        self,
        key_bind_name: str,
        default_key: Optional[int] = None,
        default_mod: Optional[int] = None,
        event_type: int = pygame.KEYDOWN,
    ) -> Callable:
        """
        Wrapper that marks the method for registration when the class is registered.

        The method's class should be registered with all event managers that have
        registered a method in that class. Failure to do so will leave a dangling
        attribute on those methods.

        :param event_type: Pygame event type that will call the assigned method.
        """

        def decorator(method: Callable) -> Callable:
            # Nearly an exact duplicate of the EventManager version
            assigned_listeners: list[
                tuple[KeyListener, str, int | None, int | None, int]
            ] = []
            if hasattr(method, "_assigned_listeners"):
                assigned_listeners = getattr(method, "_assigned_listeners", [])
            assigned_listeners.append(
                (self, key_bind_name, default_key, default_mod, event_type)
            )
            setattr(method, "_assigned_listeners", assigned_listeners)
            return method

        return decorator

    def deregister_class(self, cls: Type[object]):
        """
        Clears all instances and methods belonging to the supplied class.

        :param cls: The cls being deregistered.
        :raises KeyError: If cls is not contained in the class listeners, this
        error will be raised.
        """
        self._class_listener_instances.pop(cls, None)
        for method in self._assigned_classes.get(cls, []):
            self.unbind_method(method)
        self._assigned_classes.pop(cls)

    def unbind_method(self, method: Callable):
        """
        Clears the method from its bindings.

        :param method: Method being unbound
        """
        for bind_name in self._class_listener_binds.get(method, []):
            event_sets = self._class_listeners.get(bind_name, {})
            for event_type, listener_sets in event_sets.items():
                # We don't know the event type for the method,
                # so we need to check all of them
                listener_sets = list(
                    filter(
                        lambda listener_set: method is not listener_set[0],
                        listener_sets,
                    )
                )
                event_sets.update({event_type: listener_sets})
            self._class_listeners.update({bind_name: event_sets})
        self._class_listener_binds.pop(method)

    def clear_bind(self, bind_name: str, eliminate_bind: bool = False) -> None:
        """
        Clears all callables from the specified bind name

        :param bind_name: _description_
        :param eliminate_bind: _description_, defaults to False
        """
        if eliminate_bind:
            bind = self._key_hooks.pop(bind_name, None)
            if bind is None:
                logger.warning(
                    f" Cannot remove bind '{bind_name}';" " bind does not exist."
                )
                return
            self.key_map.remove_bind(bind_name)
            return
        call_list = self._key_hooks.get(bind_name, None)
        class_call_list = self._class_listeners.get(bind_name, None)
        if call_list is None and class_call_list is None:
            logger.warning(f" Bind '{bind_name}' not in key registry.")
            return
        if call_list:
            logger.info(f"Clearing all functions from bind {bind_name}")
            call_list.clear()
        if class_call_list:
            logger.info(f"Clearing all methods from bind {bind_name}")
            class_call_list.clear()

    def _generate_bind(
        self,
        key_bind_name: str,
        default_key: Optional[int] = None,
        default_mod: Optional[int] = None,
    ) -> None:
        """
        Looks for a bind matching the given name.
        Creates the bind if it does not exist.
        Does not overwrite the key of an existing bind.

        :param key_bind_name: Name assigned to the bind.
        :param default_key: Pygame key code assigned to a new bind,
        defaults to None
        :param default_mod: bitmask of pygame modkeys for a new bind,
        defaults to pygame.KMOD_NONE
        """
        if not self.key_map.get_bound_key(key_bind_name):
            self.key_map.key_binds.setdefault(default_key, []).append(
                KeyBind(bind_name=key_bind_name, mod=default_mod)
            )

    def notify(self, event: pygame.Event) -> None:
        key_changed: int | None = getattr(event, "key", None)
        mod_keys: int | None = getattr(event, "mod", None)
        key_binds = self.key_map.key_binds.get(key_changed, [])
        for key_bind in key_binds:
            # Try to match the mod keys. If they don't, move on to the next.
            if not (
                (key_bind.mod is None)
                or (mod_keys is not None and (key_bind.mod & mod_keys))
            ):
                continue
            hooks = self._key_hooks.get(key_bind.bind_name, {})
            # Pass along our event to each callable.
            responders = hooks.get(event.type, [])
            for responder in responders:
                threading.Thread(target=responder, args=(event,)).start()
                # hook(event)

            method_hooks = self._class_listeners.get(key_bind.bind_name, {})
            listeners = method_hooks.get(event.type, [])
            for method, cls in listeners:
                instances = self._class_listener_instances.get(cls, WeakSet())
                for instance in instances:
                    threading.Thread(target=method, args=(instance, event)).start()

    @classmethod
    def load_from_file(cls, file_path: Path, parser: Type[FileParser]) -> None:
        with open(file_path, "r") as file:
            binds = parser.load(file)
            cls.key_map.merge(binds)

    # cls.key_map.key_binds.update(binds.key_binds)
    # raise NotImplementedError("This feature is not yet available")

    @classmethod
    def save_to_file(cls, file_path: Path, parser: Type[FileParser]) -> None:
        with open(file_path, "w") as file:
            parser.save(cls.key_map, file)
        # raise NotImplementedError("This feature is not yet available")


def notifyKeyListeners(event: pygame.Event) -> None:
    """
    Automatically passes the event to all existing KeyListeners

    :param event: Pygame event instance, of type KEYDOWN or KEYUP
    """
    for listener in KeyListener._listeners.values():
        listener.notify(event)


def getKeyListener(handle: str) -> KeyListener:
    return KeyListener._listeners.setdefault(handle, KeyListener(handle))
