import json

from .key_manager import FileParser
from .key_map import KeyMap, KeyBind

import pygame


class JSONParser(FileParser):

    def __init__(self, file_path, key_map=None):
        super().__init__(file_path, key_map)

    def load(self) -> KeyMap:
        with open(self.file_path, "r") as file:
            maps = json.load(file)
            self.key_map = self.unpack_binds(maps)
        return self.key_map

    def save(self) -> None:
        if not self.key_map:
            raise ValueError("Cannot save key map; Parser has no key map.")
        with open(self.file_path, "w") as file:
            maps = self.key_map.pack_binds()
            json.dump(maps, file)

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
