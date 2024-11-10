import json
from typing import TextIO

from .key_manager import FileParser
from .key_map import KeyMap, KeyBind

import pygame


class JSONParser(FileParser):

    def load(self, in_file: TextIO) -> KeyMap:
        # with open(self.file_path, "r") as file:
        maps = json.load(in_file)
        return self.unpack_binds(maps)

    def save(self, key_map: KeyMap, out_file: TextIO) -> None:
        maps = key_map.pack_binds()
        json.dump(maps, out_file)

    def unpack_binds(self, maps: dict) -> KeyMap:
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
