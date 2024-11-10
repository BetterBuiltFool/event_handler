import json
from typing import TextIO

from .key_manager import FileParser
from .key_map import KeyMap, KeyBind

import pygame


class JSONParser(FileParser):

    @staticmethod
    def load(in_file: TextIO) -> KeyMap:
        maps = json.load(in_file)
        return JSONParser.unpack_binds(maps)

    @staticmethod
    def save(key_map: KeyMap, out_file: TextIO) -> None:
        maps = key_map.pack_binds()
        json.dump(maps, out_file)

    @staticmethod
    def unpack_binds(maps: dict) -> KeyMap:
        unpacked_dict: dict[int | None, list[KeyBind]] = {}
        for key_name, bind_list in maps.items():
            key_code = None
            if key_name != "null":
                key_code = pygame.key.key_code(key_name)
            binds = [KeyBind(bind_name=bind[0], mod=bind[1]) for bind in bind_list]
            unpacked_dict.update({key_code: binds})
        key_map = KeyMap()
        key_map.key_binds = unpacked_dict
        return key_map
