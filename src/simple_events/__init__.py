import sys
from .base_manager import basicConfig  # noqa: F401
from .event_manager import getEventManager, notifyEventManagers  # noqa: F401, E501
from .key_manager import getKeyListener, notifyKeyListeners  # noqa: F401, E501
from .file_parser import JSONParser  # noqa: F401, E501

if sys.platform == "emscripten":
    # We always want to run in async mode if we're online
    basicConfig(is_async=True)
