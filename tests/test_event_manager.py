import pathlib
import sys
import threading
from typing import Callable, cast, Type
import unittest
from weakref import WeakSet

import pygame

sys.path.append(str(pathlib.Path.cwd()))

from src.simple_events import getEventManager  # noqa: E402
from src.simple_events.event_manager import EventManager  # noqa: E402


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

    def test_sequential_tag(self) -> None:

        @self.event_manager.register(self.test_event)
        @self.event_manager.sequential
        def test_func() -> None:
            pass

        self.assertHasAttr(test_func, "_runs_sequential")

    def test_concurrent_tag(self) -> None:

        @self.event_manager.register(self.test_event)
        @self.event_manager.concurrent
        @self.event_manager.sequential
        def test_func() -> None:
            pass

        self.assertNotHasAttr(test_func, "_runs_sequential")

    def test_register(self) -> None:

        @self.event_manager.register(self.test_event)
        def test_func() -> None:
            pass

        event_dict = self.event_manager._listeners.get(self.test_event, {})
        listeners = event_dict.get(True)
        self.assertIn(
            test_func,
            cast(list[Callable], listeners),
        )

    def test_register_sequential(self) -> None:

        @self.event_manager.register(self.test_event)
        @self.event_manager.sequential
        def test_func() -> None:
            pass

        @self.event_manager.register(self.test_event)
        def test_func2() -> None:
            pass

        event_dict = self.event_manager._listeners.get(self.test_event, {})
        conc_listeners = event_dict.get(True)
        seq_listeners = event_dict.get(False)
        self.assertNotIn(
            test_func,
            cast(list[Callable], conc_listeners),
        )
        self.assertIn(
            test_func,
            cast(list[Callable], seq_listeners),
        )
        self.assertNotIn(
            test_func2,
            cast(list[Callable], seq_listeners),
        )
        self.assertIn(
            test_func2,
            cast(list[Callable], conc_listeners),
        )

    def test_deregister(self) -> None:

        @self.event_manager.register(self.test_event)
        @self.event_manager.register(self.test_event2)
        def test_func(_) -> None:
            pass

        self.event_manager.deregister(test_func, self.test_event)

        event_dict = self.event_manager._listeners.get(self.test_event)
        assert event_dict
        call_list = event_dict.get(True)
        assert call_list is not None

        self.assertNotIn(test_func, call_list)

        event_dict2 = self.event_manager._listeners.get(self.test_event2)
        assert event_dict2
        call_list2 = event_dict2.get(True)
        assert call_list2

        self.assertIn(test_func, call_list2)

    def test_deregister_all(self) -> None:

        @self.event_manager.register(self.test_event)
        @self.event_manager.register(self.test_event2)
        def test_func(_) -> None:
            pass

        self.event_manager.deregister(test_func)

        event_dict = self.event_manager._listeners.get(self.test_event)
        assert event_dict
        call_list = event_dict.get(True)
        assert call_list is not None

        self.assertNotIn(test_func, call_list)

        event_dict2 = self.event_manager._listeners.get(self.test_event2)
        assert event_dict2
        call_list2 = event_dict2.get(True)
        assert call_list2 is not None

        self.assertNotIn(test_func, call_list2)

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
                WeakSet[TestClass],
                self.event_manager._class_listener_instances.get(TestClass),
            ),
        )
        event_dict = self.event_manager._class_listeners.get(self.test_event, {})
        listeners = event_dict.get(True, [])
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

        event_dict = self.event_manager._class_listeners.get(self.test_event, {})
        listeners = event_dict.get(True, [])
        self.assertIsNotNone(listeners)

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

        event_dict = self.event_manager._class_listeners.get(self.test_event, {})
        listeners = event_dict.get(True, [])
        self.assertIsNotNone(listeners)

        listener_pair = (TestClass.test_method, TestClass)
        # Verify method/object pair are detached from the event
        self.assertNotIn(
            listener_pair, cast(list[tuple[Callable, Type[object]]], listeners)
        )

    def test_event_purge(self) -> None:

        @self.event_manager.register(self.test_event)
        @self.event_manager.register(self.test_event2)
        def test_func(_) -> None:
            pass

        @self.event_manager.register(self.test_event)
        @self.event_manager.register(self.test_event2)
        def test_func2(_) -> None:
            pass

        self.event_manager.purge_event(self.test_event)
        # Verify both have been cleared from test_event

        self.assertNotIn(
            self.test_event,
            self.event_manager._listeners,
        )
        # But both need to remain in test_event2

        event_dict2 = self.event_manager._listeners.get(self.test_event2, {})
        self.assertIn(
            test_func,
            cast(list[Callable], event_dict2.get(True)),
        )
        self.assertIn(
            test_func2,
            cast(list[Callable], event_dict2.get(True)),
        )

    def test_notify_concurrent(self) -> None:

        example_var = False
        example_var2 = False
        lock = threading.Lock()

        @self.event_manager.register(self.test_event)
        def test_func(_) -> None:
            nonlocal example_var
            lock.acquire()
            example_var = True
            lock.release()

        @self.event_manager.register(self.test_event)
        @self.event_manager.sequential
        def test_func2(_) -> None:
            nonlocal example_var2
            example_var2 = True

        local_event = pygame.event.Event(self.test_event2)
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.event_manager.notify_concurrent(event)
        # Make sure only the correct event is responded to
        self.assertFalse(example_var)
        self.assertFalse(example_var2)
        local_event = pygame.event.Event(self.test_event)
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.event_manager.notify_concurrent(event)
        self.assertTrue(example_var)
        self.assertFalse(example_var2)

    def test_notify_class_concurrent(self) -> None:

        lock = threading.Lock()

        @self.event_manager.register_class
        class TestClass:
            """
            Simple class for testing
            """

            def __init__(self):
                self.test_var = False
                self.test_var2 = False

            @self.event_manager.register_method(self.test_event2)
            def test_method(self, _):
                lock.acquire()
                self.test_var = True
                lock.release()

            @self.event_manager.register_method(self.test_event2)
            @self.event_manager.sequential
            def test_method2(self, _):
                self.test_var2 = True

        test_class_list: list[TestClass] = []

        for _ in range(3):
            test_class_list.append(TestClass())

        local_event = pygame.Event(self.test_event)
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.event_manager.notify_concurrent(event)
        for item in test_class_list:
            self.assertFalse(item.test_var)
            self.assertFalse(item.test_var2)

        local_event = pygame.Event(self.test_event2)
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.event_manager.notify_concurrent(event)
        for item in test_class_list:
            self.assertTrue(item.test_var)
            self.assertFalse(item.test_var2)

    def test_notify_sequential(self) -> None:

        example_var = False
        example_var2 = False
        lock = threading.Lock()

        @self.event_manager.register(self.test_event)
        def test_func(_) -> None:
            nonlocal example_var
            lock.acquire()
            example_var = True
            lock.release()

        @self.event_manager.register(self.test_event)
        @self.event_manager.sequential
        def test_func2(_) -> None:
            nonlocal example_var2
            example_var2 = True

        local_event = pygame.event.Event(self.test_event2)
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.event_manager.notify_sequential(event)
        # Make sure only the correct event is responded to
        self.assertFalse(example_var)
        self.assertFalse(example_var2)
        local_event = pygame.event.Event(self.test_event)
        pygame.event.post(local_event)
        for event in pygame.event.get():
            self.event_manager.notify_sequential(event)
        self.assertFalse(example_var)
        self.assertTrue(example_var2)

    def test_notify_class_sequential(self) -> None:

        lock = threading.Lock()

        @self.event_manager.register_class
        class TestClass:
            """
            Simple class for testing
            """

            def __init__(self):
                self.test_var = False
                self.test_var2 = False

            @self.event_manager.register_method(self.test_event2)
            def test_method(self, _):
                lock.acquire()
                self.test_var = True
                lock.release()

            @self.event_manager.register_method(self.test_event2)
            @self.event_manager.sequential
            def test_method2(self, _):
                self.test_var2 = True

        test_class_list: list[TestClass] = []

        for _ in range(3):
            test_class_list.append(TestClass())

        local_event = pygame.Event(self.test_event)
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.event_manager.notify_sequential(event)
        for item in test_class_list:
            self.assertFalse(item.test_var)
            self.assertFalse(item.test_var2)

        local_event = pygame.Event(self.test_event2)
        pygame.event.post(local_event)

        for event in pygame.event.get():
            self.event_manager.notify_sequential(event)
        for item in test_class_list:
            self.assertFalse(item.test_var)
            self.assertTrue(item.test_var2)


if __name__ == "__main__":
    pygame.init()
    unittest.main()
