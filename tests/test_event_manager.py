import pathlib
import sys
import threading
import unittest

import pygame

sys.path.append(str(pathlib.Path.cwd()))

from src.event_handler import getEventManager  # noqa: E402


class TestEventManager(unittest.TestCase):

    def setUp(self):
        self.event_manager = getEventManager("TestCase")
        self.test_event = pygame.USEREVENT+1
        self.test_event2 = pygame.USEREVENT+2

    def tearDown(self):
        self.event_manager.listeners.clear()

    def test_register(self):

        def test_func():
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.assertIn(
            test_func,
            self.event_manager.listeners.get(self.test_event)
        )

    def test_deregister(self):

        def test_func(_):
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.event_manager.register(self.test_event2)(test_func)
        self.event_manager.deregister(test_func, self.test_event)
        self.assertNotIn(
            test_func,
            self.event_manager.listeners.get(self.test_event)
        )
        self.assertIn(
            test_func,
            self.event_manager.listeners.get(self.test_event2)
        )

    def test_deregister_all(self):

        def test_func(_):
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.event_manager.register(self.test_event2)(test_func)
        self.event_manager.deregister(test_func)
        self.assertNotIn(
            test_func,
            self.event_manager.listeners.get(self.test_event)
        )
        self.assertNotIn(
            test_func,
            self.event_manager.listeners.get(self.test_event2)
        )

    def test_event_purge(self):

        def test_func(_):
            pass

        def test_func2(_):
            pass

        self.event_manager.register(self.test_event)(test_func)
        self.event_manager.register(self.test_event)(test_func2)
        self.event_manager.register(self.test_event2)(test_func)
        self.event_manager.register(self.test_event2)(test_func2)
        self.event_manager.purge_event(self.test_event)
        # Verify both have been cleared from test_event
        self.assertNotIn(
            test_func,
            self.event_manager.listeners.get(self.test_event)
        )
        self.assertNotIn(
            test_func2,
            self.event_manager.listeners.get(self.test_event)
        )
        # But both need to remain in test_event2
        self.assertIn(
            test_func,
            self.event_manager.listeners.get(self.test_event2)
        )
        self.assertIn(
            test_func2,
            self.event_manager.listeners.get(self.test_event2)
        )

    def test_notify(self):

        example_var = False
        lock = threading.Lock()

        def test_func(_):
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


if __name__ == "__main__":
    pygame.init()
    unittest.main()
