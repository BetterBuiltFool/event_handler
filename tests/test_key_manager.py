from io import StringIO
import pathlib
import sys
import threading
from typing import Callable, cast, Type
import unittest

import pygame

sys.path.append(str(pathlib.Path.cwd()))

from src.event_handler.key_manager import (  # noqa: E402
    getKeyListener,
    KeyListener,
)

from src.event_handler.key_map import (  # noqa: E402
    KeyBind,
    KeyMap,
)

from src.event_handler.file_parser import (  # noqa: E402
    JSONParser,
)


class TestKeyMap(unittest.TestCase):

    def setUp(self) -> None:
        self.keymap = KeyMap()

    def tearDown(self) -> None:
        self.keymap.key_binds.clear()

    def test_generate_bind(self):
        bind_name = "test_bind"
        key = pygame.K_9
        mod = pygame.KMOD_ALT

        self.keymap.generate_bind(bind_name, key, mod)

        test_bind = KeyBind(bind_name, mod)
        self.assertIn(test_bind, self.keymap.key_binds.get(key, []))

    def test_rebind(self) -> None:
        bind_name = "test_bind"
        start_key = pygame.K_9
        start_mod = pygame.KMOD_ALT
        test_bind = KeyBind(bind_name=bind_name, mod=start_mod)

        self.keymap.generate_bind(bind_name, start_key, start_mod)

        new_key = pygame.K_0

        self.keymap.rebind(test_bind, new_key)

        self.assertNotIn(test_bind, self.keymap.key_binds.get(start_key, []))
        self.assertIn(test_bind, self.keymap.key_binds.get(new_key, []))

    def test_get_bound_key(self) -> None:
        bind_name = "test_bind"
        start_key = pygame.K_9
        start_mod = pygame.KMOD_ALT

        self.keymap.generate_bind(bind_name, start_key, start_mod)

        key, mod = cast(tuple[int | None, int], self.keymap.get_bound_key(bind_name))
        self.assertRaises(ValueError, self.keymap.get_bound_key, "unbound_name")
        self.assertEqual(key, start_key)
        self.assertEqual(start_mod, mod)

    def test_remove_bind(self) -> None:
        bind_name = "test_bind"
        start_key = pygame.K_9
        start_mod = pygame.KMOD_ALT
        test_bind = KeyBind(bind_name=bind_name, mod=start_mod)

        self.keymap.generate_bind(bind_name, start_key, start_mod)

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

    def test_merge(self) -> None:
        other_map = KeyMap()

        for i in range(3):
            self.keymap.generate_bind(f"bind{i}", pygame.K_0)

        for i in range(2, 5):
            other_map.generate_bind(f"bind{i}", pygame.K_1)

        self.keymap.merge(other_map)

        expected_key = pygame.K_0
        try:
            for i in range(5):
                key = pygame.K_0 if i < 2 else pygame.K_1
                expected_key = key
                self.assertEqual(key, self.keymap.get_bound_key(f"bind{i}")[0])
        except ValueError:
            self.fail(
                f"Expected key {pygame.key.name(expected_key)}, "
                f"but couldn't find 'bind{i}'"
            )

    def test_pack_binds(self) -> None:

        for i in range(3):
            self.keymap.generate_bind(f"bind{i}", pygame.K_0)
        self.keymap.generate_bind("bind3", None)

        packed_dict = self.keymap.pack_binds()

        comp_dict = {
            "0": [("bind0", None), ("bind1", None), ("bind2", None)],
            "null": [("bind3", None)],
        }

        self.assertDictEqual(packed_dict, comp_dict)


class TestJSONParser(unittest.TestCase):

    def test_unpack_binds(self) -> None:

        keymap = KeyMap()

        for i in range(3):
            keymap.generate_bind(f"bind{i}", pygame.K_0)
        keymap.generate_bind("bind3", None)

        packed = keymap.pack_binds()

        unpacked = JSONParser.unpack_binds(packed).key_binds

        comp_dict = {
            pygame.K_0: [
                KeyBind("bind0", None),
                KeyBind("bind1", None),
                KeyBind("bind2", None),
            ],
            None: [("bind3", None)],
        }

        self.assertDictEqual(unpacked, comp_dict)

    def test_save(self) -> None:

        keymap = KeyMap()

        for i in range(3):
            keymap.generate_bind(f"bind{i}", pygame.K_0)
        keymap.generate_bind("bind3", None)

        outfile = StringIO()

        JSONParser.save(keymap, outfile)

        outfile.seek(0)

        json_string = (
            r'{"0": [["bind0", null], ["bind1", null], ["bind2", null]],'
            r' "null": [["bind3", null]]}'
        )

        self.assertEqual(outfile.read(), json_string)

    def test_load(self) -> None:

        keymap = KeyMap()

        for i in range(3):
            keymap.generate_bind(f"bind{i}", pygame.K_0)
        keymap.generate_bind("bind3", None)

        json_string = (
            r'{"0": [["bind0", null], ["bind1", null], ["bind2", null]],'
            + r' "null": [["bind3", null]]}'
        )

        print(json_string)

        infile = StringIO()
        infile.write(json_string)
        infile.seek(0)

        new_map = JSONParser.load(infile)

        for key in new_map.key_binds:
            self.assertEqual(new_map.key_binds.get(key), keymap.key_binds.get(key))


class TestKeyListener(unittest.TestCase):

    def assertHasAttr(self, obj, intendedAttr: str):
        testBool = hasattr(obj, intendedAttr)

        self.assertTrue(testBool, msg=f"{obj=} lacks an attribute, {intendedAttr=}")

    def assertNotHasAttr(self, obj, intendedAttr: str):
        testBool = hasattr(obj, intendedAttr)

        self.assertFalse(
            testBool, msg=f"{obj=} has unexpected attribute, {intendedAttr=}"
        )

    def setUp(self) -> None:
        self.key_listener = getKeyListener("TestCase")

    def tearDown(self) -> None:
        self.key_listener.key_map.key_binds.clear()
        self.key_listener._key_hooks.clear()
        self.key_listener._assigned_classes.clear()
        self.key_listener._class_listener_binds.clear()
        self.key_listener._class_listeners.clear()
        self.key_listener._class_listener_instances.clear()

    def test_bind(self) -> None:

        def test_func(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.bind("test_bind2")(test_func)

        self.assertIn("test_bind0", self.key_listener._key_hooks.keys())
        self.assertIn("test_bind1", self.key_listener._key_hooks.keys())
        self.assertIn("test_bind2", self.key_listener._key_hooks.keys())

        bind0_dict = self.key_listener._key_hooks.get("test_bind0")
        assert bind0_dict
        bind0_list = bind0_dict.get(pygame.KEYDOWN)
        self.assertIn(
            test_func,
            cast(list[Callable], bind0_list),
        )

        bind1_dict = self.key_listener._key_hooks.get("test_bind1")
        assert bind1_dict
        bind1_list = bind1_dict.get(pygame.KEYDOWN)
        self.assertIn(
            test_func,
            cast(list[Callable], bind1_list),
        )

        bind2_dict = self.key_listener._key_hooks.get("test_bind2")
        assert bind2_dict
        bind2_list = bind2_dict.get(pygame.KEYDOWN)
        self.assertIn(
            test_func,
            cast(list[Callable], bind2_list),
        )

    def test_unbind(self) -> None:

        def test_func(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.bind("test_bind2")(test_func)

        self.key_listener.unbind(test_func, "test_bind0")

        bind0_dict = self.key_listener._key_hooks.get("test_bind0")
        assert bind0_dict
        bind0_list = bind0_dict.get(pygame.KEYDOWN)
        self.assertNotIn(
            test_func,
            cast(list[Callable], bind0_list),
        )

        bind1_dict = self.key_listener._key_hooks.get("test_bind1")
        assert bind1_dict
        bind1_list = bind1_dict.get(pygame.KEYDOWN)
        self.assertIn(
            test_func,
            cast(list[Callable], bind1_list),
        )

        bind2_dict = self.key_listener._key_hooks.get("test_bind2")
        assert bind2_dict
        bind2_list = bind2_dict.get(pygame.KEYDOWN)
        self.assertIn(
            test_func,
            cast(list[Callable], bind2_list),
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
        bind1_dict = self.key_listener._key_hooks.get("test_bind1")
        assert bind1_dict
        bind1_list = bind1_dict.get(pygame.KEYDOWN)
        self.assertIn(
            test_func,
            cast(list[Callable], bind1_list),
        )

        self.key_listener.clear_bind("test_bind0", True)

        self.assertIsNone(self.key_listener._key_hooks.get("test_bind0"))

    def test_bind_method(self) -> None:

        class TestClass:
            @self.key_listener.bind_method("test_bind")
            def test_method(self, _):
                pass

        self.assertHasAttr(TestClass.test_method, "_assigned_listeners")
        assigned_listener_sets: list[
            tuple[KeyListener, str, int | None, int | None, int]
        ] = getattr(TestClass.test_method, "_assigned_listeners")
        assigned_listeners = [set[0] for set in assigned_listener_sets]
        self.assertIn(self.key_listener, assigned_listeners)

    def test_register_class(self) -> None:

        @self.key_listener.register_class
        class TestClass:
            @self.key_listener.bind_method("test_bind")
            def test_method(self, _):
                pass

        test_instance = TestClass()

        # Verify attribute cleanup
        self.assertNotHasAttr(TestClass.test_method, "_assigned_listeners")
        # Verify class in assigned classes
        self.assertIn(TestClass, self.key_listener._assigned_classes.keys())
        # Verify method in listeners
        self.assertIn(
            TestClass.test_method, self.key_listener._class_listener_binds.keys()
        )
        self.assertIn(
            test_instance,
            cast(
                list[TestClass],
                self.key_listener._class_listener_instances.get(TestClass),
            ),
        )
        bound_listeners: dict[int, list[tuple[Callable, Type[object]]]] = (
            self.key_listener._class_listeners.get("test_bind", {})
        )
        self.assertTrue(bound_listeners)
        listeners: list[tuple[Callable, Type[object]]] = bound_listeners.get(
            pygame.KEYDOWN, []
        )
        self.assertTrue(listeners)
        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are associated with the event
        self.assertIn(listener_pair, listeners)

    def test_unbind_method(self) -> None:

        @self.key_listener.register_class
        class TestClass:
            @self.key_listener.bind_method("test_bind")
            def test_method(self, _):
                pass

            @self.key_listener.bind_method("test_bind")
            def test_method2(self, _):
                pass

        # Variable is for GC purposes
        # Don't want to bother with turning gc off
        test_instance = TestClass()  # noqa: F841

        self.key_listener.unbind_method(TestClass.test_method)
        self.assertNotIn(
            TestClass.test_method, self.key_listener._class_listener_binds.keys()
        )
        bound_listeners: dict[int, list[tuple[Callable, Type[object]]]] = (
            self.key_listener._class_listeners.get("test_bind", {})
        )
        self.assertTrue(bound_listeners)
        listeners: list[tuple[Callable, Type[object]]] = bound_listeners.get(
            pygame.KEYDOWN, []
        )
        self.assertTrue(listeners)
        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are associated with the event
        self.assertNotIn(listener_pair, listeners)

    def test_deregister_class(self) -> None:

        @self.key_listener.register_class
        class TestClass:
            @self.key_listener.bind_method("test_bind")
            def test_method(self, _):
                pass

        # Variable is for GC purposes
        # Don't want to bother with turning gc off
        test_instance = TestClass()  # noqa: F841

        self.key_listener.deregister_class(TestClass)
        # Verify method removed from listeners
        self.assertNotIn(
            TestClass.test_method, self.key_listener._class_listener_binds.keys()
        )
        self.assertNotIn(TestClass, self.key_listener._class_listener_instances.keys())
        bound_listeners: dict[int, list[tuple[Callable, Type[object]]]] = (
            self.key_listener._class_listeners.get("test_bind", {})
        )
        self.assertTrue(bound_listeners)
        listeners: list[tuple[Callable, Type[object]]] = bound_listeners.get(
            pygame.KEYDOWN, []
        )
        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are associated with the event
        self.assertNotIn(listener_pair, listeners)

    def test_notify_simple(self) -> None:

        example_var = False
        lock = threading.Lock()

        def test_func(_) -> None:
            nonlocal example_var
            lock.acquire()
            example_var = True
            lock.release()

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind9", pygame.K_9, None)(test_func)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="1", key=pygame.K_1, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify(event)
        # False, because the wrong key was pressed
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify(event)
        # False, because Alt isn't held
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_ALT
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
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
            self.key_listener.notify(event)
        # True, despite Alt also being pressed
        self.assertTrue(example_var)

    def test_notify_class(self) -> None:

        lock = threading.Lock()

        @self.key_listener.register_class
        class TestClass:
            """
            Simple class for testing
            """

            def __init__(self):
                self.test_var = False

            @self.key_listener.bind_method("test_bind", pygame.K_0)
            def test_method(self, _):
                lock.acquire()
                self.test_var = True
                lock.release()

        test_class_list: list[TestClass] = []

        for i in range(3):
            test_class_list.append(TestClass())

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.key_listener.notify(event)
        for item in test_class_list:
            self.assertFalse(item.test_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.key_listener.notify(event)
        for item in test_class_list:
            self.assertTrue(item.test_var)


if __name__ == "__main__":
    pygame.init()
    unittest.main()
