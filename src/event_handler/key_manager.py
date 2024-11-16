from __future__ import annotations

from abc import ABC, abstractmethod
import itertools
import logging
from pathlib import Path
from typing import Any, Callable, Optional, overload, TextIO, Type

# import file_parser
from .joy_map import JoyMap
from .key_map import KeyBind, KeyMap
from .base_manager import BaseManager, _CallableSets

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
    def _unpack_binds(maps: dict) -> dict: ...


class KeyListener(BaseManager):
    _listeners: dict[str, KeyListener] = {}
    key_map: KeyMap = KeyMap()
    joy_map: JoyMap = JoyMap()

    def __init__(self, handle: str) -> None:
        super().__init__(handle)

        # --------Basic function assignment--------
        # Meta dict, string bind name as key, then event type as key to get callable
        # get(bind_name).get(concurrency).get(event_type)
        self._key_hooks: dict[str, dict[bool, dict[int, list[Callable]]]] = {}

        # --------Class method assignment--------
        # Meta dict, string bind name as key, then Pygame event key, method and
        # affected object as values
        # get(bind_name).get(concurrency).get(event_type)
        self._class_listeners: dict[
            str, dict[bool, dict[int, list[tuple[Callable, Type[object]]]]]
        ] = {}
        # Inversion of _class_listeners. Method as key, bind name
        self._class_listener_binds: dict[Callable, list[str]] = {}

    def bind(
        self,
        key_bind_name: str,
        default_key: Optional[int] = None,
        default_mod: Optional[int] = None,
        default_joystick_data: Optional[dict] = None,
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
        if default_joystick_data is not None:
            self.joy_map.generate_bind(key_bind_name, default_joystick_data)
        else:
            self.key_map.generate_bind(key_bind_name, default_key, default_mod)

        def decorator(responder: Callable) -> Callable:
            # Regardless, add the responder to the bind within our hook dict
            is_concurrent = not hasattr(responder, "_runs_sequential")
            event_dict = self._key_hooks.setdefault(key_bind_name, {})
            hooks = event_dict.setdefault(is_concurrent, {})
            listeners = hooks.setdefault(event_type, [])
            if responder not in listeners:
                listeners.append(responder)
            return responder

        return decorator

    @overload
    def rebind(
        self,
        key_bind_name: str,
        new_key: Optional[int] = None,
        new_mod: Optional[int] = None,
    ) -> tuple[int | None, int | None] | None: ...

    @overload
    def rebind(
        self,
        key_bind_name: str,
        new_joystick_data: Optional[dict] = None,
    ) -> dict | None: ...

    def rebind(
        self,
        key_bind_name: str,
        *args,
        **kwds,
        # new_key: Optional[int] = None,
        # new_mod: Optional[int] = None,
        # new_joystick_data: Optional[dict] = None,
    ) -> dict | tuple[int | None, int | None] | None:
        """
        Attempts to assign the new key info the the named bind.
        Generates a warning if the bind is not registered.

        :param key_bind_name: Name of the bind to be reassigned
        :param default_key: Pygame key to be assigned to
        :param default_mod: Pygame mod keys for assignment,
        defaults to None
        :return: A tuple containing the previous key and mod key
        """
        new_bind: Any
        if len(args):
            new_bind = args[0]
        elif new_bind := kwds.get("new_key"):
            pass
        if kwds.get("new_joystick_data") or isinstance(new_bind, dict):
            return self._rebind_joystick(key_bind_name, new_bind)
        else:
            mod_keys: int | None
            if len(args) > 1:
                mod_keys = args[1]
            else:
                mod_keys = kwds.get("new_mod", None)
            return self._rebind_key(key_bind_name, new_bind, mod_keys)

    def _rebind_key(
        self,
        key_bind_name: str,
        new_key: Optional[int] = None,
        new_mod: Optional[int] = None,
    ) -> tuple[int | None, int | None] | None:
        old_bind: tuple | None
        try:
            old_bind = self.key_map.get_bound_key(key_bind_name)
        except ValueError:
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

    def _rebind_joystick(
        self,
        key_bind_name: str,
        new_joystick_data: Optional[dict] = None,
    ) -> dict | None:
        old_bind: dict | None
        try:
            old_bind = self.joy_map.get_bound_joystick_event(key_bind_name)
        except ValueError:
            logger.warning(
                f"Attempted to rebind '{key_bind_name}' when bind does not"
                " exist. \n Program might be attempting to rebind before"
                " generating binds, or bind name may be incorrect."
            )
            return None
        self.joy_map.rebind(key_bind_name, new_joystick_data)

        return old_bind

    def unbind(self, func: Callable, bind_name: Optional[str] = None) -> None:
        """
        Removes a callable from the given bind.

        :param func: A Callable previously registered with this Key Listener
        :param bind_name: The bind to be removed from, or all instances, if
        None. Defaults to None.
        """
        if bind_name:
            event_dict = self._key_hooks.get(bind_name)
            if not event_dict:
                logger.warning(
                    f"Bind name '{bind_name}' does not exist in KeyListener "
                    f"'{self.handle}'"
                )
                return
            found = False
            for bind_dict in event_dict.values():
                for bind in bind_dict.values():
                    if func not in bind:
                        continue
                    found = True
                    bind.remove(func)
            if not found:
                logger.warning(
                    f"Cannot remove function {func.__name__} from '"
                    f"{bind_name}' of KeyListener: {self.handle}.\n"
                    f"Function is not bound to that name."
                )
            return
        for event_dict in self._key_hooks.values():
            for bind_dict in event_dict.values():
                if not bind_dict:
                    continue
                for bind in bind_dict.values():
                    if bind and func in bind:
                        bind.remove(func)

    def _capture_method(
        self, cls: Type[object], method: Callable, tag_data: tuple
    ) -> None:
        """
        Adds the method, class, and event into the appropriate dictionaries to ensure
        they can be properly notified.

        :param cls: Class of the object being processed
        :param method: Callable being captured
        :param tag_data: A tuple containing pertinent registration data
        """
        is_concurrent = not hasattr(method, "_runs_sequential")
        key_bind_name: str = tag_data[0]
        default_key: int = tag_data[1]
        default_mod: int = tag_data[2]
        event_type: int = tag_data[3]

        self.key_map.generate_bind(key_bind_name, default_key, default_mod)

        # -----Add to Class Listeners-----
        event_dict = self._class_listeners.setdefault(key_bind_name, {})
        concurrency_dict = event_dict.setdefault(is_concurrent, {})
        listeners = concurrency_dict.setdefault(event_type, [])
        listeners.append((method, cls))

        # -----Add to Class Listener Events-----

        self._class_listener_binds.setdefault(method, []).append(key_bind_name)

        # -----Add to Assigned Classes-----
        self._assigned_classes.setdefault(cls, []).append(method)

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
            return self._tag_method(
                method, (key_bind_name, default_key, default_mod, event_type)
            )

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
            concurrency_dict = self._class_listeners.get(bind_name, {})
            for concurrency, event_dict in concurrency_dict.items():
                for event_type, listener_sets in event_dict.items():
                    # Retain only the listeners that are not the method
                    listener_sets = list(
                        filter(
                            lambda listener_set: method is not listener_set[0],
                            listener_sets,
                        )
                    )
                    event_dict.update({event_type: listener_sets})
                concurrency_dict.update({concurrency: event_dict})
            self._class_listeners.update({bind_name: concurrency_dict})
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

    def _validate_input(self, key_bind: KeyBind, input_data: tuple) -> bool:
        """
        Validates the input data against a key bind to ensure a match

        :param key_bind: Target key bind containing desired input data
        :param input_data: Data coming from the recent input event
        :return: True if the input data matches the bind, otherwise false
        """
        is_valid = False
        # This structure is here to potentially leave room for
        key_changed: int | None = input_data[0]
        mod_keys: int | None = input_data[1]
        if key_changed is not None:
            mod = key_bind.mod
            if mod is None:
                is_valid = True
            elif mod_keys is not None and (mod & mod_keys or mod is mod_keys):
                # mod is mod_keys catches pygame.KMOD_NONE
                is_valid = True
        return is_valid

    def _get_callables(self, event: pygame.Event) -> _CallableSets:
        """
        Calls all registered functions and methods that make use of the given event

        TODO Seperate into notify_concurrent and notify_sequential

        :param event: pygame event to be passed to the callables
        """
        key_changed: int | None = getattr(event, "key", None)
        mod_keys: int | None = getattr(event, "mod", None)
        input_data = (key_changed, mod_keys)
        key_binds = self.key_map.key_binds.get(key_changed, [])
        conc_funcs_lists = []
        seq_funcs_lists = []
        conc_methods_lists = []
        seq_methods_lists = []
        for key_bind in key_binds:
            # Try to match the mod keys. If they don't, move on to the next.
            if not self._validate_input(key_bind, input_data):
                continue
            hooks = self._key_hooks.get(key_bind.bind_name, {})
            conc_funcs_lists.append(hooks.get(True, {}).get(event.type, []))
            seq_funcs_lists.append(hooks.get(False, {}).get(event.type, []))

            method_hooks = self._class_listeners.get(key_bind.bind_name, {})
            conc_methods_lists.append(method_hooks.get(True, {}).get(event.type, []))
            seq_methods_lists.append(method_hooks.get(False, {}).get(event.type, []))
        return _CallableSets(
            concurrent_functions=list(itertools.chain(*conc_funcs_lists)),
            sequential_functions=list(itertools.chain(*seq_funcs_lists)),
            concurrent_methods=list(itertools.chain(*conc_methods_lists)),
            sequential_methods=list(itertools.chain(*seq_methods_lists)),
        )

    @classmethod
    def load_from_file(cls, file_path: Path, parser: Type[FileParser]) -> None:
        """
        Pulls the file from the file path, and uses the supplied parser to convert the
        file into a KeyMap, which is merged with the current KeyMap.

        Binds in the current KeyMap that don't exist in the loaded KeyMap do not change,
        all others are updated to reflect the loaded binds

        :param file_path: path to the file to be loaded
        :param parser: Parser to be used to decode the file.
        Use one that matches the data structure
        """
        with open(file_path, "r") as file:
            binds = parser.load(file)
            cls.key_map.merge(binds)

    @classmethod
    def save_to_file(cls, file_path: Path, parser: Type[FileParser]) -> None:
        """
        Saves the current KeyMap to a file in the requested location.
        Expects the file name and extension to be included.

        :param file_path: Path to the file being saved to
        :param parser: Parser used to encode the file.
        """
        with open(file_path, "w") as file:
            parser.save(cls.key_map, file)


def notifyKeyListeners(event: pygame.Event) -> None:
    """
    Automatically passes the event to all existing KeyListeners

    :param event: Pygame event instance, of type KEYDOWN or KEYUP
    """
    for listener in KeyListener._listeners.values():
        listener.notify(event)


def getKeyListener(handle: str) -> KeyListener:
    """
    Supplies a Key Listener with the given handle. If one exists with that handle,
    the existing Key Listener is given. Otherwise, a new one is created.

    :param handle: String describing the KeyListener.
    """
    return KeyListener._listeners.setdefault(handle, KeyListener(handle))
