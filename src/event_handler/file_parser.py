import json
from typing import TextIO

from .key_manager import FileParser
from .key_map import KeyMap, KeyBind

import pygame


class JSONParser(FileParser):

    @staticmethod
    def load(in_file: TextIO) -> KeyMap:
        """
        Converts the given JSON file into a KeyMap

        :param in_file: Target file with the required data.
        :return: Created KeyMap
        """
        maps = json.load(in_file)
        key_map = KeyMap()
        key_map.key_binds = JSONParser._unpack_binds(maps)
        return key_map

    @staticmethod
    def save(key_map: KeyMap, out_file: TextIO) -> None:
        """
        Saves the KeyMap as a JSON string

        :param key_map: KeyMap object being saved
        :param out_file: File receiving the data
        """
        maps = key_map.pack_binds()
        json.dump(maps, out_file)

    @staticmethod
    def _unpack_binds(maps: dict) -> dict:
        """
        Converts the JSON-styled dict into a dict compatible with a KeyMap

        :param maps: JSON-style dictionary of keybinds
        :return: Dictionary compatible with KeyMap
        """
        unpacked_dict: dict[int | None, list[KeyBind]] = {}
        for key_name, bind_list in maps.items():
            key_code = None
            if key_name != "null":
                key_code = pygame.key.key_code(key_name)
            binds = [KeyBind(bind_name=bind[0], mod=bind[1]) for bind in bind_list]
            unpacked_dict.update({key_code: binds})
        return unpacked_dict
