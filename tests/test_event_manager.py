import pathlib
import sys
import threading
from typing import Callable, cast, Type
import unittest

import pygame

sys.path.append(str(pathlib.Path.cwd()))

from src.event_handler import getEventManager  # noqa: E402
from src.event_handler.event_manager import EventManager  # noqa: E402


class TestEventManager(unittest.TestCase):

    def assertHasAttr(self, obj, intendedAttr: str):
        testBool = hasattr(obj, intendedAttr)

        self.assertTrue(testBool, msg=f"{obj=} lacks an attribute, {intendedAttr=}")

    def assertNotHasAttr(self, obj, intendedAttr: str):
        testBool = hasattr(obj, intendedAttr)

        self.assertFalse(
            testBool, msg=f"{obj=} has unexpected attribute, {intendedAttr=}"
        )

    def setUp(self) -> None:
        self.event_manager = getEventManager("TestCase")
        self.test_event = pygame.USEREVENT + 1
        self.test_event2 = pygame.USEREVENT + 2

    def tearDown(self) -> None:
        self.event_manager._listeners.clear()

    def test_register(self) -> None:

        def test_func() -> None:
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.assertIn(
            test_func,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event)),
        )

    def test_deregister(self) -> None:

        def test_func(_) -> None:
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.event_manager.register(self.test_event2)(test_func)
        self.event_manager.deregister(test_func, self.test_event)
        self.assertNotIn(
            test_func,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event)),
        )
        self.assertIn(
            test_func,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event2)),
        )

    def test_deregister_all(self) -> None:

        def test_func(_) -> None:
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.event_manager.register(self.test_event2)(test_func)
        self.event_manager.deregister(test_func)
        self.assertNotIn(
            test_func,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event)),
        )
        self.assertNotIn(
            test_func,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event2)),
        )

    def test_register_method(self) -> None:

        class TestClass:
            @self.event_manager.register_method(self.test_event)
            def test_method(self, _):
                pass

        self.assertHasAttr(TestClass.test_method, "_assigned_managers")
        assigned_managers_pairs: list[tuple[EventManager, int]] = getattr(
            TestClass.test_method, "_assigned_managers"
        )
        assigned_managers = [pair[0] for pair in assigned_managers_pairs]
        self.assertIn(self.event_manager, assigned_managers)

    def test_register_class(self) -> None:

        @self.event_manager.register_class
        class TestClass:
            @self.event_manager.register_method(self.test_event)
            def test_method(self, _):
                pass

        test_instance = TestClass()

        # Verify attribute cleanup
        self.assertNotHasAttr(TestClass.test_method, "_assigned_managers")
        # Verify class in assigned classes
        self.assertIn(TestClass, self.event_manager._assigned_classes.keys())
        # Verify method in listeners
        self.assertIn(
            TestClass.test_method, self.event_manager._class_listener_events.keys()
        )
        self.assertIn(
            test_instance,
            cast(
                list[TestClass],
                self.event_manager._class_listener_instances.get(TestClass),
            ),
        )
        listeners = self.event_manager._class_listeners.get(self.test_event)
        self.assertIsNotNone(listeners)
        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are associated with the event
        self.assertIn(
            listener_pair, cast(list[tuple[Callable, Type[object]]], listeners)
        )

    def test_deregister_method(self) -> None:

        @self.event_manager.register_class
        class TestClass:
            @self.event_manager.register_method(self.test_event)
            def test_method(self, _):
                pass

        TestClass()

        self.event_manager.deregister_method(TestClass.test_method)

        # Verify method removed from listeners
        self.assertNotIn(
            TestClass.test_method, self.event_manager._class_listener_events.keys()
        )

        listeners = self.event_manager._class_listeners.get(self.test_event)
        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are detached from the event
        self.assertNotIn(
            listener_pair, cast(list[tuple[Callable, Type[object]]], listeners)
        )

    def test_deregister_class(self) -> None:

        @self.event_manager.register_class
        class TestClass:
            @self.event_manager.register_method(self.test_event)
            def test_method(self, _):
                pass

        TestClass()

        self.event_manager.deregister_class(TestClass)

        self.assertNotIn(TestClass, self.event_manager._assigned_classes.keys())

        # Verify method removed from listeners
        self.assertNotIn(
            TestClass.test_method, self.event_manager._class_listener_events.keys()
        )
        self.assertNotIn(TestClass, self.event_manager._class_listener_instances.keys())
        listeners = self.event_manager._class_listeners.get(self.test_event)
        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are detached from the event
        self.assertNotIn(
            listener_pair, cast(list[tuple[Callable, Type[object]]], listeners)
        )

    def test_event_purge(self) -> None:

        def test_func(_) -> None:
            pass

        def test_func2(_) -> None:
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.event_manager.register(self.test_event)(test_func2)
        self.event_manager.register(self.test_event2)(test_func)
        self.event_manager.register(self.test_event2)(test_func2)
        self.event_manager.purge_event(self.test_event)
        # Verify both have been cleared from test_event
        self.assertNotIn(
            test_func,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event)),
        )
        self.assertNotIn(
            test_func2,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event)),
        )
        # But both need to remain in test_event2
        self.assertIn(
            test_func,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event2)),
        )
        self.assertIn(
            test_func2,
            cast(list[Callable], self.event_manager._listeners.get(self.test_event2)),
        )

    def test_notify_simple(self) -> None:

        example_var = False
        lock = threading.Lock()

        def test_func(_) -> None:
            nonlocal example_var
            lock.acquire()
            example_var = True
            lock.release()

        self.event_manager.register(self.test_event)(test_func)
        local_event = pygame.event.Event(self.test_event2)
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.event_manager.notify(event)
        # Make sure only the correct event is responded to
        self.assertFalse(example_var)
        local_event = pygame.event.Event(self.test_event)
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.event_manager.notify(event)
        self.assertTrue(example_var)

    def test_notify_class(self) -> None:

        lock = threading.Lock()

        @self.event_manager.register_class
        class TestClass:
            """
            Simple class for testing
            """

            def __init__(self):
                self.test_var = False

            @self.event_manager.register_method(self.test_event2)
            def test_method(self, _):
                lock.acquire()
                self.test_var = True
                lock.release()

        test_class_list: list[TestClass] = []

        for i in range(3):
            test_class_list.append(TestClass())

        local_event = pygame.Event(self.test_event)
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.event_manager.notify(event)
        for item in test_class_list:
            self.assertFalse(item.test_var)

        local_event = pygame.Event(self.test_event2)
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.event_manager.notify(event)
        for item in test_class_list:
            self.assertTrue(item.test_var)


if __name__ == "__main__":
    pygame.init()
    unittest.main()
