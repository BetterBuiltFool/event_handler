from __future__ import annotations

from dataclasses import dataclass, field
import logging
from pathlib import Path
import threading
from typing import Callable, NamedTuple, Optional

import pygame

logger = logging.getLogger(__name__)

KeyBind = NamedTuple("KeyBind",
                     [("bind_name", str),
                      ("mod", int)])


@dataclass
class KeyMap:
    """
    A dictionary of keybind events with associated keys.
    """
    key_binds: dict[int | None, list[KeyBind]] = field(default_factory=dict)

    def rebind(self,
               new_key_bind: KeyBind,
               new_key: Optional[int] = None):
        """
        Takes the given keybind, unbinds it from its current key, and rebinds
        it to the given key. If no key is given, it is put under None, meaning
        the hook is regarded as unbound, and cannot be called.

        :param new_key_bind: Keybind containing the bind name and mod keys.
        :param new_key: Pygame key id, defaults to None
        """
        for key_bind_list in self.key_binds.values():
            binds_to_remove = []
            for key_bind in key_bind_list:
                if key_bind.bind_name == new_key_bind.bind_name:
                    # Can't directly remove in the loop, could skip one.
                    binds_to_remove.append(key_bind)
            for bind in binds_to_remove:
                key_bind_list.remove(bind)

        self.key_binds.setdefault(new_key, []).append(new_key_bind)

    def get_bound_key(self,
                      bind_name: str
                      ) -> tuple[int | None, int] | None:
        """Finds the current key that binds to the given bind name, and
        returns it in a tuple with the bound mod keys.

        If the bind is not used, returns None.

        :param bind_name: Name of the bind being used.
        :return: Tuple containing two ints, first representing the number for
        a pygame key, the second a bitmask int representing pygame mod keys.
        """
        for key, key_bind_list in self.key_binds.items():
            for key_bind in key_bind_list:
                if key_bind.bind_name == bind_name:
                    return key, key_bind.mod
        return None


class KeyListener:
    _listeners: dict[str, KeyListener] = {}

    def __init__(self, handle: str) -> None:
        self.key_map = KeyMap()
        self.key_hooks: dict[str, list[Callable]] = {}
        self.handle = handle

    def bind(
        self,
        key_bind_name: str,
        default_key: Optional[int] = None,
        default_mod: int = pygame.KMOD_NONE
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
        self._generate_bind(
            key_bind_name,
            default_key,
            default_mod
        )

        def decorator(responder: Callable) -> Callable:
            # Regardless, add the responder to the bind within our hook dict
            hooks = self.key_hooks.setdefault(
                key_bind_name, []
            )
            if responder not in hooks:
                hooks.append(responder)
            return responder
        return decorator

    def rebind(
        self,
        key_bind_name: str,
        new_key: Optional[int],
        new_mod: int = pygame.KMOD_NONE
    ) -> tuple[int | None, int] | None:
        """
        Attempts to assign the new key info the the named bind.
        Generates a warning if the bind is not registered.

        :param key_bind_name: Name of the bind to be reassigned
        :param default_key: Pygame key to be assigned to
        :param default_mod: Pygame mod keys for assignment,
        defaults to pygame.KMOD_NONE
        :return: A tuple containing the previous key and mod key
        """
        old_bind = self.key_map.get_bound_key(key_bind_name)
        if old_bind:
            logger.warning(
                f"Attempted to rebind \'{key_bind_name}\' when bind does not"
                " exist. \n Program might be attempting to rebind before"
                " generating binds, or bind name may be incorrect."
            )
            return None
        self.key_map.rebind(
            KeyBind(
                bind_name=key_bind_name,
                mod=new_mod
            ),
            new_key=new_key
        )

        return old_bind

    def _generate_bind(self,
                       key_bind_name: str,
                       default_key: Optional[int] = None,
                       default_mod: int = pygame.KMOD_NONE):
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
            self.key_map.key_binds.setdefault(
                default_key,
                []
            ).append(KeyBind(bind_name=key_bind_name, mod=default_mod))

    def notify(self, event: pygame.Event):
        key_changed = event.key
        mod_keys = event.mod
        key_binds = self.key_map.key_binds.get(key_changed, [])
        for key_bind in key_binds:
            # Try to match the mod keys. If they don't, move on to the next.
            if not (
                (key_bind.mod == pygame.KMOD_NONE)
                or key_bind.mod & mod_keys
            ):
                continue
            hooks = self.key_hooks.get(key_bind.bind_name, [])
            # Pass along our event to each callable.
            for hook in hooks:
                threading.Thread(
                    target=hook,
                    args=(event,)
                ).start()
                # hook(event)

    def load_from_file(self,
                       filepath: Path):
        raise NotImplementedError("This feature is not yet available")

    def save_to_file(self,
                     location: Path):
        raise NotImplementedError("This feature is not yet available")

    @classmethod
    def getKeyListener(cls, handle: str):
        return cls._listeners.setdefault(handle, KeyListener(handle))
