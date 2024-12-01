from io import StringIO
import json
import pathlib
import sys
import threading
from typing import Callable, cast
import unittest

import pygame

sys.path.append(str(pathlib.Path.cwd()))

from src.simple_events.key_manager import (  # noqa: E402
    getKeyListener,
    KeyListener,
)

from src.simple_events.key_map import (  # noqa: E402
    KeyBind,
    KeyMap,
)

from src.simple_events.joy_map import (  # noqa: E402
    JoyMap,
)

from src.simple_events.file_parser import (  # noqa: E402
    _get_parser_from_path,
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
            "bind0": ("0", None),
            "bind1": ("0", None),
            "bind2": ("0", None),
            "bind3": (None, None),
        }

        self.assertDictEqual(packed_dict, comp_dict)


class TestJoyMap(unittest.TestCase):

    def setUp(self):
        self.joymap = JoyMap()

    def tearDown(self):
        self.joymap._joy_binds.clear()

    def test_convert_event(self):
        joystick_data = {"button": 0}
        converted_data = self.joymap._convert_event(joystick_data)

        match_data = (("button", 0),)

        self.assertEqual(converted_data, match_data)

        event = pygame.Event(pygame.JOYBUTTONDOWN, button=0, instance_id=0, joy=0)

        converted_data = self.joymap._convert_event(event)

        self.assertEqual(converted_data, match_data)

        event = pygame.Event(
            pygame.JOYAXISMOTION, axis=0, instance_id=0, joy=0, value=0.5
        )

        match_data = (("axis", 0),)

        converted_data = self.joymap._convert_event(event)

        self.assertEqual(converted_data, match_data)

        event = pygame.Event(
            pygame.JOYHATMOTION, hat=0, instance_id=0, joy=0, value=(0, 0)
        )

        match_data = (("hat", 0),)

        converted_data = self.joymap._convert_event(event)

        self.assertEqual(converted_data, match_data)

    def test_convert_pairs(self):
        key_data = (("button", 0),)
        converted_data = self.joymap._convert_pairs(key_data)

        match_data = {"button": 0}

        self.assertEqual(converted_data, match_data)

    def test_generate_bind(self):
        bind_name = "test_bind"
        joystick_data = {"button": 0}
        self.joymap.generate_bind(bind_name, joystick_data)

        match_data = (("button", 0),)

        self.assertIn(bind_name, self.joymap._joy_binds.get(match_data, []))

    def test_get(self):
        bind_name = "test_bind"
        joystick_data = {"button": 0}
        self.joymap.generate_bind(bind_name, joystick_data)

        event = pygame.Event(pygame.JOYBUTTONDOWN, button=0, instance_id=0, joy=0)

        bind_list = self.joymap.get(event)

        self.assertIn(bind_name, bind_list)

    def test_get_bound_joystick_event(self):
        bind_name = "test_bind"
        joystick_data = {"button": 0}
        self.joymap.generate_bind(bind_name, joystick_data)

        returned_data = self.joymap.get_bound_joystick_event(bind_name)

        self.assertEqual(returned_data, joystick_data)

    def test_remove_bind(self):
        bind_name = "test_bind"
        joystick_data = {"button": 0}
        self.joymap.generate_bind(bind_name, joystick_data)

        match_data = (("button", 0),)

        self.assertIn(bind_name, self.joymap._joy_binds.get(match_data, []))

        self.joymap.remove_bind(bind_name)

        self.assertNotIn(bind_name, self.joymap._joy_binds.get(match_data, []))

    def test_rebind(self):
        bind_name = "test_bind"
        joystick_data = {"button": 0}
        self.joymap.generate_bind(bind_name, joystick_data)

        match_data = (("button", 0),)

        self.assertIn(bind_name, self.joymap._joy_binds.get(match_data, []))

        new_joystick_data = {"button": 1}

        new_match_data = (("button", 1),)

        self.joymap.rebind(bind_name, new_joystick_data)

        self.assertNotIn(bind_name, self.joymap._joy_binds.get(match_data, []))

        self.assertIn(bind_name, self.joymap._joy_binds.get(new_match_data, []))

    def test_merge(self):
        bind_name = "test_bind"
        joystick_data = {"button": 0}
        self.joymap.generate_bind(bind_name, joystick_data)

        match_data1 = (("button", 0),)

        bind_name2 = "test_bind2"
        joystick_data2 = {"button": 0}
        self.joymap.generate_bind(bind_name2, joystick_data2)

        self.assertIn(bind_name, self.joymap._joy_binds.get(match_data1, []))
        self.assertIn(bind_name2, self.joymap._joy_binds.get(match_data1, []))

        other_map = JoyMap()

        bind_name3 = "test_bind2"
        joystick_data3 = {"button": 1}
        other_map.generate_bind(bind_name3, joystick_data3)

        self.joymap.merge(other_map)

        new_match_data = (("button", 1),)

        self.assertIn(bind_name, self.joymap._joy_binds.get(match_data1, []))
        self.assertNotIn(bind_name2, self.joymap._joy_binds.get(match_data1, []))
        self.assertIn(bind_name2, self.joymap._joy_binds.get(new_match_data, []))

    def test_pack_binds(self):
        bind_name = "test_bind"
        joystick_data = {"button": 0}
        self.joymap.generate_bind(bind_name, joystick_data)

        bind_name2 = "test_bind2"
        joystick_data2 = {"button": 0}
        self.joymap.generate_bind(bind_name2, joystick_data2)

        test_dict = {"test_bind": (("button", 0),), "test_bind2": (("button", 0),)}

        packed_dict = self.joymap.pack_binds()

        self.assertEqual(test_dict, packed_dict)


class TestFileParser(unittest.TestCase):

    def test_json(self):
        path = pathlib.PurePath("sample.json")

        self.assertIs(_get_parser_from_path(path), JSONParser)

        new_path = pathlib.PurePath("unsupported.py")

        with self.assertRaises(ValueError):
            _get_parser_from_path(new_path)


class TestJSONParser(unittest.TestCase):

    def test_unpack_keys(self) -> None:

        keymap = KeyMap()

        for i in range(3):
            keymap.generate_bind(f"bind{i}", pygame.K_0)
        keymap.generate_bind("bind3", None)

        packed = keymap.pack_binds()

        unpacked = JSONParser._unpack_keys(packed)

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
        joymap = JoyMap()

        for i in range(3):
            keymap.generate_bind(f"bind{i}", pygame.K_0)
        keymap.generate_bind("bind3", None)

        outfile = StringIO()

        JSONParser.save(keymap, joymap, outfile)

        outfile.seek(0)

        maps = {"keys": keymap.pack_binds(), "controller": joymap.pack_binds()}

        json_string = json.dumps(maps, indent=2)

        out_string = outfile.read()

        self.assertEqual(out_string, json_string)

    def test_load(self) -> None:

        keymap = KeyMap()

        for i in range(3):
            keymap.generate_bind(f"bind{i}", pygame.K_0)
        keymap.generate_bind("bind3", None)

        json_string = (
            r'{"keys": '
            r'{"bind0": ["0", null], "bind1": ["0", null], '
            r'"bind2": ["0", null], "bind3": [null, null]}, '
            r'"controller": {}'
            r"}"
        )

        infile = StringIO()
        infile.write(json_string)
        infile.seek(0)

        new_map, _ = JSONParser.load(infile)

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

    def test_sequential_tag(self) -> None:

        @self.key_listener.bind("test_bind1")
        @self.key_listener.sequential
        def test_func() -> None:
            pass

        self.assertHasAttr(test_func, "_runs_sequential")

    def test_concurrent_tag(self) -> None:

        @self.key_listener.bind("test_bind1")
        @self.key_listener.concurrent
        @self.key_listener.sequential
        def test_func() -> None:
            pass

        self.assertNotHasAttr(test_func, "_runs_sequential")

    def test_bind(self) -> None:

        def test_func(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.bind("test_bind2")(test_func)

        found_bind0 = False
        found_bind1 = False
        found_bind2 = False

        for bind_name, _, _ in self.key_listener._key_hooks.keys():
            match bind_name:
                case "test_bind0":
                    found_bind0 = True
                case "test_bind1":
                    found_bind1 = True
                case "test_bind2":
                    found_bind2 = True

        self.assertTrue(
            found_bind0,
            msg=f"'test_bind0' not found in {self.key_listener._key_hooks.keys()}",
        )
        self.assertTrue(
            found_bind1,
            msg=f"'test_bind1' not found in {self.key_listener._key_hooks.keys()}",
        )
        self.assertTrue(
            found_bind2,
            msg=f"'test_bind2' not found in {self.key_listener._key_hooks.keys()}",
        )

        callables = self.key_listener._get_callables(
            pygame.Event(pygame.KEYDOWN, key=pygame.K_0, mod=pygame.KMOD_ALT)
        )

        callables2 = self.key_listener._get_callables(
            pygame.Event(pygame.KEYDOWN, key=pygame.K_1)
        )

        self.assertIn(test_func, callables.concurrent_functions)

        self.assertIn(test_func, callables2.concurrent_functions)

        bind2_list = self.key_listener._key_hooks.get(
            ("test_bind2", True, pygame.KEYDOWN), []
        )
        self.assertIn(test_func, bind2_list)

    def test_bind_sequential(self) -> None:

        @self.key_listener.sequential
        def test_func(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.bind("test_bind2")(test_func)

        found_bind0 = False
        found_bind1 = False
        found_bind2 = False

        for bind_name, _, _ in self.key_listener._key_hooks.keys():
            match bind_name:
                case "test_bind0":
                    found_bind0 = True
                case "test_bind1":
                    found_bind1 = True
                case "test_bind2":
                    found_bind2 = True

        self.assertTrue(
            found_bind0,
            msg=f"'test_bind0' not found in {self.key_listener._key_hooks.keys()}",
        )
        self.assertTrue(
            found_bind1,
            msg=f"'test_bind1' not found in {self.key_listener._key_hooks.keys()}",
        )
        self.assertTrue(
            found_bind2,
            msg=f"'test_bind2' not found in {self.key_listener._key_hooks.keys()}",
        )

        callables = self.key_listener._get_callables(
            pygame.Event(pygame.KEYDOWN, key=pygame.K_0, mod=pygame.KMOD_ALT)
        )

        callables2 = self.key_listener._get_callables(
            pygame.Event(pygame.KEYDOWN, key=pygame.K_1)
        )

        self.assertIn(test_func, callables.sequential_functions)

        self.assertIn(test_func, callables2.sequential_functions)

        bind2_list = self.key_listener._key_hooks.get(
            ("test_bind2", False, pygame.KEYDOWN), []
        )
        self.assertIn(test_func, bind2_list)

    def test_unbind(self) -> None:

        def test_func(_) -> None:
            pass

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind1", pygame.K_1)(test_func)

        self.key_listener.bind("test_bind2")(test_func)

        self.key_listener.unbind(test_func, "test_bind0")

        bind0_list = self.key_listener._key_hooks.get(
            ("test_bind0", True, pygame.KEYDOWN), []
        )
        self.assertNotIn(
            test_func,
            cast(list[Callable], bind0_list),
        )

        bind1_list = self.key_listener._key_hooks.get(
            ("test_bind1", True, pygame.KEYDOWN), []
        )
        self.assertIn(
            test_func,
            cast(list[Callable], bind1_list),
        )

        bind2_list = self.key_listener._key_hooks.get(
            ("test_bind2", True, pygame.KEYDOWN), []
        )
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

        bind0_list = self.key_listener._key_hooks.get(
            ("test_bind0", True, pygame.KEYDOWN), []
        )
        self.assertFalse(bind0_list)
        self.assertIsNotNone(bind0_list)

        bind1_list = self.key_listener._key_hooks.get(
            ("test_bind1", True, pygame.KEYDOWN), []
        )
        self.assertIn(
            test_func,
            cast(list[Callable], bind1_list),
        )

        self.key_listener.clear_bind("test_bind0", True)

        bind0_list = self.key_listener._key_hooks.get(
            ("test_bind0", True, pygame.KEYDOWN), []
        )

        binds = [
            True
            for (bind_name, _, _) in self.key_listener._key_hooks
            if bind_name == "test_bind0"
        ]

        self.assertFalse(any(binds))

    def test_bind_method(self) -> None:

        class TestClass:
            @self.key_listener.bind_method("test_bind")
            def test_method(self, _):
                pass

        self.assertHasAttr(TestClass.test_method, "_assigned_managers")
        assigned_listener_sets: list[
            tuple[KeyListener, str, int | None, int | None, int]
        ] = getattr(TestClass.test_method, "_assigned_managers")
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
        listeners = self.key_listener._class_listeners.get(
            ("test_bind", True, pygame.KEYDOWN), []
        )
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

        listeners = self.key_listener._class_listeners.get(
            ("test_bind", True, pygame.KEYDOWN), []
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

        listeners = self.key_listener._key_hooks.get(
            ("test_bind", True, pygame.KEYDOWN), []
        )
        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are associated with the event
        self.assertNotIn(listener_pair, listeners)

    def test_notify_concurrent(self) -> None:

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
            self.key_listener.notify_concurrent(event)
        # False, because the wrong key was pressed
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_concurrent(event)
        # False, because Alt isn't held
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_ALT
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_concurrent(event)
        # True, because both 0 and Alt are pressed
        self.assertTrue(example_var)

        # Reset example var for other binding test
        example_var = False

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_concurrent(event)
        # True, because exact key combo match
        self.assertTrue(example_var)

        # Reset again
        example_var = False

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_ALT
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_concurrent(event)
        # True, despite Alt also being pressed
        self.assertTrue(example_var)

    def test_notify_class_concurrent(self) -> None:

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
            self.key_listener.notify_concurrent(event)
        for item in test_class_list:
            self.assertFalse(item.test_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.key_listener.notify_concurrent(event)
        for item in test_class_list:
            self.assertTrue(item.test_var)

    def test_notify_sequential(self) -> None:

        example_var = False

        @self.key_listener.sequential
        def test_func(_) -> None:
            nonlocal example_var
            example_var = True

        self.key_listener.bind("test_bind0", pygame.K_0, pygame.KMOD_ALT)(test_func)

        self.key_listener.bind("test_bind9", pygame.K_9, None)(test_func)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="1", key=pygame.K_1, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_concurrent(event)
        # False, because the wrong key was pressed
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_sequential(event)
        # False, because Alt isn't held
        self.assertFalse(example_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_ALT
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_sequential(event)
        # True, because both 0 and Alt are pressed
        self.assertTrue(example_var)

        # Reset example var for other binding test
        example_var = False

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_sequential(event)
        # True, because exact key combo match
        self.assertTrue(example_var)

        # Reset again
        example_var = False

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_ALT
        )
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.key_listener.notify_sequential(event)
        # True, despite Alt also being pressed
        self.assertTrue(example_var)

    def test_notify_class_sequential(self) -> None:

        @self.key_listener.register_class
        class TestClass:
            """
            Simple class for testing
            """

            def __init__(self):
                self.test_var = False

            @self.key_listener.bind_method("test_bind", pygame.K_0)
            @self.key_listener.sequential
            def test_method(self, _):
                self.test_var = True

        test_class_list: list[TestClass] = []

        for i in range(3):
            test_class_list.append(TestClass())

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="9", key=pygame.K_9, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.key_listener.notify_sequential(event)
        for item in test_class_list:
            self.assertFalse(item.test_var)

        local_event = pygame.event.Event(
            pygame.KEYDOWN, unicode="0", key=pygame.K_0, mod=pygame.KMOD_NONE
        )
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.key_listener.notify_sequential(event)
        for item in test_class_list:
            self.assertTrue(item.test_var)


if __name__ == "__main__":
    pygame.init()
    unittest.main()
