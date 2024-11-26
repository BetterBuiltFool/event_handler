from .base_manager import managerBasicConfig  # noqa: F401
from .event_manager import getEventManager, notifyEventManagers  # noqa: F401, E501
from .key_manager import getKeyListener, notifyKeyListeners  # noqa: F401, E501
from .file_parser import JSONParser  # noqa: F401, E501


def basicConfig(*args, **kwds):
    managerBasicConfig(*args, **kwds)
