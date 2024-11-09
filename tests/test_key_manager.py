import pathlib
import sys
import threading
from typing import Callable, cast
import unittest

import pygame

sys.path.append(str(pathlib.Path.cwd()))

from src.event_handler.key_manager import getKeyListener, KeyBind, KeyMap  # noqa: E402


class TestKeyMap(unittest.TestCase):

    def setUp(self) -> None:
        self.keymap = KeyMap()

    def tearDown(self) -> None:
        self.keymap.key_binds.clear()

    def test_rebind(self) -> None:
        bind_name = "test_bind"
        start_key = pygame.K_9
        start_mod = pygame.KMOD_ALT
        test_bind = KeyBind(bind_name=bind_name, mod=start_mod)

        self.keymap.key_binds.setdefault(start_key, []).append(test_bind)

        new_key = pygame.K_0

        self.keymap.rebind(test_bind, new_key)

        self.assertNotIn(
            test_bind, cast(list[KeyBind], self.keymap.key_binds.get(start_key))
        )
        self.assertIn(
            test_bind, cast(list[KeyBind], self.keymap.key_binds.get(new_key))
        )

    def test_get_bound_key(self) -> None:
        bind_name = "test_bind"
        start_key = pygame.K_9
        start_mod = pygame.KMOD_ALT
        test_bind = KeyBind(bind_name=bind_name, mod=start_mod)

        self.keymap.key_binds.setdefault(start_key, []).append(test_bind)

        key, mod = cast(tuple[int | None, int], self.keymap.get_bound_key(bind_name))
        empty = self.keymap.get_bound_key("unbound_name")
        self.assertEqual(key, start_key)
        self.assertEqual(start_mod, mod)
        self.assertIsNone(empty)

    def test_remove_bind(self) -> None:
        bind_name = "test_bind"
        start_key = pygame.K_9
        start_mod = pygame.KMOD_ALT
        test_bind = KeyBind(bind_name=bind_name, mod=start_mod)

        self.keymap.key_binds.setdefault(start_key, []).append(test_bind)

        new_key = pygame.K_0

        self.keymap.key_binds.setdefault(new_key, []).append(test_bind)

        self.keymap.remove_bind(bind_name, start_key)

        self.assertNotIn(
            test_bind, cast(list[KeyBind], self.keymap.key_binds.get(start_key))
        )
        self.assertIn(
            test_bind, cast(list[KeyBind], self.keymap.key_binds.get(new_key))
        )

        self.keymap.remove_bind(bind_name)

        self.assertNotIn(
            test_bind, cast(list[KeyBind], self.keymap.key_binds.get(start_key))
        )
        self.assertNotIn(
            test_bind, cast(list[KeyBind], self.keymap.key_binds.get(new_key))
        )


class TestKeyListener(unittest.TestCase):

    def setUp(self) -> None:
        self.key_listener = getKeyListener("TestCase")

    def tearDown(self) -> None:
        self.key_listener._key_hooks.clear()

    def test_bind(self) -> None:

        def test_func(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.bind("test_bind2")(test_func)

        self.assertIn("test_bind0", self.key_listener._key_hooks.keys())
        self.assertIn("test_bind1", self.key_listener._key_hooks.keys())
        self.assertIn("test_bind2", self.key_listener._key_hooks.keys())
        self.assertIn(
            test_func,
            cast(list[Callable], self.key_listener._key_hooks.get("test_bind0")),
        )
        self.assertIn(
            test_func,
            cast(list[Callable], self.key_listener._key_hooks.get("test_bind1")),
        )
        self.assertIn(
            test_func,
            cast(list[Callable], self.key_listener._key_hooks.get("test_bind2")),
        )

    def test_unbind(self) -> None:

        def test_func(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.bind("test_bind2")(test_func)

        self.key_listener.unbind(test_func, "test_bind0")

        self.assertNotIn(
            test_func,
            cast(list[Callable], self.key_listener._key_hooks.get("test_bind0")),
        )
        self.assertIn(
            test_func,
            cast(list[Callable], self.key_listener._key_hooks.get("test_bind1")),
        )
        self.assertIn(
            test_func,
            cast(list[Callable], self.key_listener._key_hooks.get("test_bind2")),
        )

    def test_clear_bind(self) -> None:

        def test_func(_) -> None:
            pass

        def test_func2(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind0")(test_func2)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.clear_bind("test_bind0")

        # No assertEmpty, so this will have to do.
        self.assertFalse(self.key_listener._key_hooks.get("test_bind0"))
        self.assertIsNotNone(self.key_listener._key_hooks.get("test_bind0"))
        self.assertIn(
            test_func,
            cast(list[Callable], self.key_listener._key_hooks.get("test_bind1")),
        )

        self.key_listener.clear_bind("test_bind0", True)

        self.assertIsNone(self.key_listener._key_hooks.get("test_bind0"))

    def test_notify(self) -> None:

        example_var = False
        lock = threading.Lock()

        def test_func(_) -> None:
            nonlocal example_var
            lock.acquire()
            example_var = True
            lock.release()

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind9", pygame.K_9, pygame.KMOD_NONE)(test_func)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="1", key=pygame.K_1, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            if event.type == pygame.KEYUP or event.type == pygame.KEYDOWN:
                self.key_listener.notify(event)
        # False, because the wrong key was pressed
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            if event.type == pygame.KEYUP or event.type == pygame.KEYDOWN:
                self.key_listener.notify(event)
        # False, because Alt isn't held
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_ALT
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            if event.type == pygame.KEYUP or event.type == pygame.KEYDOWN:
                self.key_listener.notify(event)
        # True, because both 0 and Alt are pressed
        self.assertTrue(example_var)

        # Reset example var for other binding test
        example_var = False

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            if event.type == pygame.KEYUP or event.type == pygame.KEYDOWN:
                self.key_listener.notify(event)
        # True, because exact key combo match
        self.assertTrue(example_var)

        # Reset again
        example_var = False

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_ALT
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            if event.type == pygame.KEYUP or event.type == pygame.KEYDOWN:
                self.key_listener.notify(event)
        # True, despite Alt also being pressed
        self.assertTrue(example_var)


if __name__ == "__main__":
    pygame.init()
    unittest.main()
