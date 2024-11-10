from __future__ import annotations
from dataclasses import dataclass, field
import logging
from typing import NamedTuple, Optional

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
        dead_keys: set[int | None] = set()
        for key, key_bind_list in self.key_binds.items():
            binds_to_remove: list[KeyBind] = []
            key_bind: KeyBind
            for key_bind in key_bind_list:
                if key_bind.bind_name == new_key_bind.bind_name:
                    # Can't directly remove in the loop, could skip one.
                    binds_to_remove.append(key_bind)
            removed_bind: KeyBind
            for removed_bind in binds_to_remove:
                key_bind_list.remove(removed_bind)
            if not key_bind_list:
                dead_keys.add(key)
        # Clean up any empty lists
        for key in dead_keys:
            self.key_binds.pop(key)

        self.key_binds.setdefault(new_key, []).append(new_key_bind)

    def get_bound_key(self, bind_name: str) -> tuple[int | None, int | None]:
        """
        Finds the current key that binds to the given bind name, and
        returns it in a tuple with the bound mod keys.

        :param bind_name: Name of the bind being used.
        :return: Tuple containing two ints, first representing the number for
        a pygame key, the second a bitmask int representing pygame mod keys.
        :raises ValueError: Raised if the bind name is not found.
        """
        key: int | None
        key_bind_list: list[KeyBind]
        key_bind: KeyBind
        for key, key_bind_list in self.key_binds.items():
            for key_bind in key_bind_list:
                if key_bind.bind_name == bind_name:
                    return key, key_bind.mod
        raise ValueError(f"Bind name: {bind_name} not found.")

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

    def merge(self, other: KeyMap) -> None:
        """
        Uses the supplied other map to rebind any existing keys to match the other map.
        Adds any binds from other map into the current key map, and preserves any other
        binds it already holds.

        :param other: Key map to be merged.
        """
        for key, bind_list in other.key_binds.items():
            for bind in bind_list:
                self.rebind(bind, key)

    def pack_binds(self) -> dict:
        """
        Packages binds into a serializable dictionary that is more easily saved.
        """
        packed_dict: dict[str, list] = {}
        for key_code, binds in self.key_binds.items():
            key_name = "null"
            if key_code:
                key_name = pygame.key.name(key_code)
            bind_list = [(bind.bind_name, bind.mod) for bind in binds]
            packed_dict.update({key_name: bind_list})

        return packed_dict
