import json
from typing import TextIO

from .key_manager import FileParser
from .key_map import KeyMap, KeyBind
from .joy_map import JoyMap

import pygame


class JSONParser(FileParser):

    @staticmethod
    def load(in_file: TextIO) -> tuple[KeyMap, JoyMap]:
        """
        Converts the given JSON file into a KeyMap and JoyMap

        :param in_file: Target file with the required data.
        :return: Created KeyMap and JoyMap
        """
        maps: dict = json.load(in_file)
        key_map = KeyMap()
        key_map.key_binds = JSONParser._unpack_keys(maps.get("keys", {}))
        joy_map = JoyMap()
        joy_map._joy_binds = JSONParser._unpack_joystick(maps.get("controller", {}))
        return key_map, joy_map

    @staticmethod
    def save(key_map: KeyMap, joy_map: JoyMap, out_file: TextIO) -> None:
        """
        Saves the KeyMap and JoyMap as a JSON string

        :param key_map: KeyMap object being saved
        :param out_file: File receiving the data
        """
        bind_keys = key_map.pack_binds()
        bind_joysticks = joy_map.pack_binds()
        maps = {"keys": bind_keys, "controller": bind_joysticks}
        json.dump(maps, out_file, indent=2)

    @staticmethod
    def _unpack_keys(maps: dict) -> dict:
        """
        Converts the JSON-styled dict into a dict compatible with a KeyMap

        :param maps: JSON-style dictionary of keybinds
        :return: Dictionary compatible with KeyMap
        """
        unpacked_dict: dict[int | None, list[KeyBind]] = {}
        for bind_name, key_data in maps.items():
            key_name, mod = key_data
            key_code = None
            if key_name is not None:
                key_code = pygame.key.key_code(key_name)
            unpacked_dict.setdefault(key_code, []).append(KeyBind(bind_name, mod))
            # binds = [KeyBind(bind_name=bind[0], mod=bind[1]) for bind in bind_list]
            # unpacked_dict.update({key_code: binds})
        return unpacked_dict

    @staticmethod
    def _unpack_joystick(maps: dict) -> dict:
        """
        Converts the JSON-styled dict into a dict compatible with a JoyMap

        :param maps: JSON-style dictionary of joystick binds
        :return: Dictionary compatible with JoyMap
        """
        unpacked_dict: dict[tuple, list[str]] = {}
        for bind_name, joy_data in maps.items():
            joy_data_points: list[tuple] = []
            for data_point in joy_data:
                joy_data_points.append((data_point[0], data_point[1]))
            fixed_joy_data: tuple = tuple(joy_data_points)
            unpacked_dict.setdefault(fixed_joy_data, []).append(bind_name)

        return unpacked_dict
