from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import threading
from typing import Callable, NamedTuple, Optional

import pygame

logger: logging.Logger = logging.getLogger(__name__)

KeyBind = NamedTuple("KeyBind", [("bind_name", str), ("mod", int | None)])


@dataclass
class KeyMap:
    """
    A dictionary of keybind events with associated keys.
    """

    key_binds: dict[int | None, list[KeyBind]] = field(default_factory=dict)

    def rebind(self, new_key_bind: KeyBind, new_key: Optional[int] = None) -> None:
        """
        Takes the given keybind, unbinds it from its current key, and rebinds
        it to the given key. If no key is given, it is put under None, meaning
        the hook is regarded as unbound, and cannot be called.

        :param new_key_bind: Keybind containing the bind name and mod keys.
        :param new_key: Pygame key id, defaults to None
        """
        for key_bind_list in self.key_binds.values():
            binds_to_remove: list[KeyBind] = []
            key_bind: KeyBind
            for key_bind in key_bind_list:
                if key_bind.bind_name == new_key_bind.bind_name:
                    # Can't directly remove in the loop, could skip one.
                    binds_to_remove.append(key_bind)
            removed_bind: KeyBind
            for removed_bind in binds_to_remove:
                key_bind_list.remove(removed_bind)

        self.key_binds.setdefault(new_key, []).append(new_key_bind)

    def get_bound_key(self, bind_name: str) -> tuple[int | None, int | None] | None:
        """
        Finds the current key that binds to the given bind name, and
        returns it in a tuple with the bound mod keys.

        If the bind is not used, returns None.

        :param bind_name: Name of the bind being used.
        :return: Tuple containing two ints, first representing the number for
        a pygame key, the second a bitmask int representing pygame mod keys.
        """
        key: int | None
        key_bind_list: list[KeyBind]
        key_bind: KeyBind
        for key, key_bind_list in self.key_binds.items():
            for key_bind in key_bind_list:
                if key_bind.bind_name == bind_name:
                    return key, key_bind.mod
        return None

    def remove_bind(self, bind_name: str, key: Optional[int] = None) -> None:
        """
        Eliminates the specified bind from the specified key, or all instances
        if no key is specified.

        :param bind_name: Name of the bind being removed
        :param key: Integer of pygame key code to search, defaults to None
        """
        key_bind_list: list[KeyBind] | None
        if key is not None:
            key_bind_list = self.key_binds.get(key, None)
            if not key_bind_list:
                logger.warning(
                    f" Cannot remove '{bind_name}';"
                    f" {pygame.key.name(key)} does not have any binds."
                )
                return
            to_remove: list[KeyBind] = []
            for key_bind in key_bind_list:
                if key_bind.bind_name == bind_name:
                    to_remove.append(key_bind)
            for item in to_remove:
                key_bind_list.remove(item)
            if not to_remove:
                logger.warning(
                    f" Cannot remove '{bind_name}';"
                    f" bind does not exist in {pygame.key.name(key)}"
                )
            return
        for key_bind_list in self.key_binds.values():
            to_remove = []
            for key_bind in key_bind_list:
                if key_bind.bind_name == bind_name:
                    to_remove.append(key_bind)
            for item in to_remove:
                key_bind_list.remove(item)
        return None


class KeyListener:
    _listeners: dict[str, KeyListener] = {}

    def __init__(self, handle: str) -> None:
        self.key_map: KeyMap = KeyMap()
        self._key_hooks: dict[str, dict[int, list[Callable]]] = {}
        self.handle: str = handle

    def bind(
        self,
        key_bind_name: str,
        event_type: int,
        default_key: Optional[int] = None,
        default_mod: Optional[int] = None,
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
        :param default_mod: Mod keys required for activating the key bind. If
        using multiple, use bitwise OR to combine, defaults to pygame.KMOD_NONE
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
        new_key: Optional[int],
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
        if call_list is None:
            logger.warning(f" Bind '{bind_name}' not in key registry.")
            return
        call_list.clear()

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

    def load_from_file(self, filepath: Path) -> None:
        raise NotImplementedError("This feature is not yet available")

    def save_to_file(self, location: Path) -> None:
        raise NotImplementedError("This feature is not yet available")


def notifyKeyListeners(event: pygame.Event) -> None:
    """
    Automatically passes the event to all existing KeyListeners

    :param event: Pygame event instance, of type KEYDOWN or KEYUP
    """
    for listener in KeyListener._listeners.values():
        listener.notify(event)


def getKeyListener(handle: str) -> KeyListener:
    return KeyListener._listeners.setdefault(handle, KeyListener(handle))
