<!-- Improved compatibility of back to top link: See: https://github.com/othneildrew/Best-README-Template/pull/73 -->
<a id="readme-top"></a>
<!--
*** Thanks for checking out the Best-README-Template. If you have a suggestion
*** that would make this better, please fork the repo and create a pull request
*** or simply open an issue with the tag "enhancement".
*** Don't forget to give the project a star!
*** Thanks again! Now go create something AMAZING! :D
-->



<!-- PROJECT SHIELDS -->
<!--
*** I'm using markdown "reference style" links for readability.
*** Reference links are enclosed in brackets [ ] instead of parentheses ( ).
*** See the bottom of this document for the declaration of the reference variables
*** for contributors-url, forks-url, etc. This is an optional, concise syntax you may use.
*** https://www.markdownguide.org/basic-syntax/#reference-style-links
-->
[![Contributors][contributors-shield]][contributors-url]
[![Forks][forks-shield]][forks-url]
[![Stargazers][stars-shield]][stars-url]
[![Issues][issues-shield]][issues-url]
[![MIT License][license-shield]][license-url]
<!--
[![LinkedIn][linkedin-shield]][linkedin-url]
-->



<!-- PROJECT LOGO -->
<br />
<!--
<div align="center">
  <a href="https://github.com/BetterBuiltFool/event_handler">
    <img src="images/logo.png" alt="Logo" width="80" height="80">
  </a>
-->

<h3 align="center">Simple Events</h3>

  <p align="center">
    A simple, decorator-based event system for Pygame.
    <br />
    <a href="https://github.com/BetterBuiltFool/event_handler"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <!--
    <a href="https://github.com/BetterBuiltFool/event_handler">View Demo</a>
    ·
    -->
    <a href="https://github.com/BetterBuiltFool/event_handler/issues/new?labels=bug&template=bug-report---.md">Report Bug</a>
    ·
    <a href="https://github.com/BetterBuiltFool/event_handler/issues/new?labels=enhancement&template=feature-request---.md">Request Feature</a>
  </p>
</div>



<!-- TABLE OF CONTENTS -->
<details>
  <summary>Table of Contents</summary>
  <ol>
    <li>
      <a href="#about-the-project">About The Project</a>
    </li>
    <li>
      <a href="#getting-started">Getting Started</a>
      <ul>
        <li><a href="#installation">Installation</a></li>
      </ul>
    </li>
    <li><a href="#usage">Usage</a></li>
      <ul>
        <li><a href="#event-manager">Event Manager</a></li>
        <li><a href="#key-listener">Key Listener</a></li>
        <li><a href="#key-maps">Key Maps</a></li>
        <li><a href="#controller-maps">Controller Maps</a></li>
        <li><a href="#passing-events-to-the-managers">Passing Events to the Managers</a></li>
        <li><a href="#concurrency">Concurrency</a></li>
      </ul>
    <li><a href="#roadmap">Roadmap</a></li>
    <!--<li><a href="#contributing">Contributing</a></li>-->
    <li><a href="#license">License</a></li>
    <li><a href="#contact">Contact</a></li>
    <li><a href="#acknowledgments">Acknowledgments</a></li>
  </ol>
</details>



<!-- ABOUT THE PROJECT -->
## About The Project

<!--
[![Product Name Screen Shot][product-screenshot]](https://example.com)
-->

Simple Events is a simple system that uses decorator syntax to register functions to Pygame events, allowing those function to be fired whenever the assigned event occurs.
It also features a keybind manager, which similarly can assign functions to remappable keybinds and controller binds.

<p align="right">(<a href="#readme-top">back to top</a>)</p>


<!-- GETTING STARTED -->
## Getting Started

Event handler is written in pure python, with no system dependencies, and should be OS-agnostic.

### Installation

Event handler can be installed from the [PyPI][pypi-url] using [pip][pip-url]:

```sh
pip install simple_events
```

and can be imported for use with:
```python
import simple_events
```

Event handler also require Pygame Community edition to be installed.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- USAGE EXAMPLES -->
## Usage

EventManagers and KeyListeners are instantiated like loggers from the built-in python logging library.

<!--
_For more examples, please refer to the [Documentation](https://example.com)_
-->

### Event Manager

```python
import simple_events

LOCAL_MANAGER = simple_events.getEventManager("Example")
```

This will generate an instance with the handle "Example", which will be stored by the manager system. If another module calls for that same handle, both modules will share the same event manager. Modules can even have multiple event managers to allow for control over execution context. Really, you can use as many or as few managers as desired.

The variable to which the event manager is assigned does not need to be written as a constant, though it is recommended for noticeability and avoiding accidental reassignment. The variable name has no special meaning to the event manager system.

Functions are registered using the register decorator along with the Pygame event type it wants to respond to.
For example, we will use pygame.QUIT

```python
@LOCAL_MANAGER.register(pygame.QUIT)
def quit_function(event: pygame.Event) -> None:
    # Do
    # Things
    # Here
    # When
    # Quitting
```

The function can have any syntactically valid name, and can even be used elsewhere as a normal function.

The event manager will pass on the event to the function, so the function must be able to accept an event being passed to it as its first parameter, even if it has no use for event-specific data. This can mean using either an underscore or the *args syntax to ignore the incoming event data.
Decorated functions cannot accept any additional positional arguments, unless using *args. The event manager will not provide any arguments beyond the event, so additional arguments must be optional, and are generally not recommended.

Additionally, a function can be assigned to multiple events.

Alternatively, a function does not need to use decorator syntax for registration.

```python
LOCAL_MANAGER.register(pygame.USEREVENT)(quit_function)
```

This method is useful for late binding a function.


Event managers can also be used on objects!

```python
@LOCAL_MANAGER.register_class
class TestClass:

    @LOCAL_MANAGER.register_method(pygame.QUIT)
    def sample_method(self, event: pygame.Event) -> None:
        # Do
        # The
        # Things
```

With this, the event manager will track all instances of TestClass, and whenever the assigned event is called, it will call the registered methods on all instances. As with regular registered callables, it must be able to accept the event as an argument, but also uses self to allow access to the instance within the function.

Every manager that registers a method in a class should also register that class. If a manager registers a method but not the class, the method cannot be called, and will have a dangling attribute left over from the registration process.

```python
@LOCAL_MANAGER.register_class
class TestClass:

    @LOCAL_MANAGER.register_method(pygame.QUIT)
    def sample_method(self, event: pygame.Event) -> None:
        # Do
        # The
        # Things

    @OTHER_MANAGER.register_method(pygame.QUIT)  # This will not work as expected
    def other_sample_method(self, event: pygame.Event) -> None:
        # Do
        # Other
        # Things
```

Methods cannot be late registered, unlike regular callables. Classes can be late registered, but the event manager will not pick up on existing instances.


For more information on Pygame events, including a list of event type with descriptions, see [here](https://www.pygame.org/docs/ref/event.html)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Key Listener

```python
import simple_events

KEYBINDS = simple_events.getKeyListener("Example")
```

Key Listeners are seperate from event managers and can share handles without conflict.

Key binds are slightly more involved. They require a bind name, and can accept an optional default key as well as mod keys. They have the same function signature requirements as regular event binds.

```python
@KEYBINDS.bind("example_name", pygame.K_p, pygame.KMOD_SHIFT)
def some_function(_):
    # Does
    # Something
    # When
    # Shift+P
    # Is pressed
```

Default key specifies the initial key needed to activate the bind, and can be left blank, but this will make the bind "unbound" and unable to be called.
With a default key set, the mod key specifies what additional mod keys (such as Alt, Control, or Shift) need to be pressed to activate the bind. If none is set, the bind will be called _regardless_ of mod keys. If pygame.KMOD_NONE is used, the bind will fire _only_ if no mod keys are pressed.

Optionally, an event may be specified. By default, it uses key down for key events, and  for controller inputs it will attempt to intuit the desired event. The callable will be called only when the required function is called.

If the event type does not match the input type, the bind will never be called.

```python
@KEYBINDS.bind("example_name", pygame.K_p, pygame.KMOD_SHIFT, pygame.KEYUP)
def some_function(_):
    # Does
    # Something
    # When
    # Shift+P
    # Is pressed
```


If a bind is used for multiple functions, the first processed call is used to establish the default keys.

```python
@KEYBINDS.bind("example2", pygame.K_o)
def func1(_):
    ...

@KEYBINDS.bind("example2", pygame.K_z, pygame.KMOD_CTRL)
def func2(_):
    ...
```

In this example, pressing the "o" key will activate both functions, even though func2 asks for Ctrl+Z.

Key Listeners also work with classes and methods, following similar syntax as the Event Manager.

For more information on pygame and key handling, including a list of key names, see [here](https://www.pygame.org/docs/ref/key.html)

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Key Maps

Key Listeners rely on the Key Map to determine which binds to call when a key is pressed. Every Key Listener uses the same Key Map.

Key Maps can be modified via a Key Listener.

```python
import simple_events

KEYBINDS = simple_events.getKeyListener("Remapper")
@KEYBINDS.bind("example_name", pygame.K_p, pygame.KMOD_SHIFT)
def some_function(_):
    ...

KEYBINDS.rebind("example_name", pygame.K_m, pygame.KMOD_ALT)
```

This changes the key for all functions bound to "example_name", which now get called when Alt+M is pressed instead of Shift+P.

Key Maps can also be saved and loaded from file. This requires a path to the desired file location, including the file name and extension, and a File Parser to convert the data. The File Parser is a static type, and can be passed directly without be instantiated.

```python
import simple_events

KEYBINDS = simple_events.getKeyListener("Saveloader")

KEYBINDS.save_to_file("path/to/the/file.json", JSONParser)
```

In this case, the current KeyMap will be saved to file.json, and will use the JSON format.

A Key Map can be loaded similarly.

```python
import simple_events

KEYBINDS = simple_events.getKeyListener("Saveloader")

KEYBINDS.load_from_file("path/to/source/key_binds.json", JSONParser)
```

This will try to load key_binds.json and merge the key binds into the current Key Map. The loaded key binds take precedence over existing ones, but if a key bind exists in the current map but not the loaded one, it is carried over without modification.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Controller Maps

Also known as JoyMaps.

JoyMaps are to controller event what KeyMaps are to keyboard events. They have many of the same properties to KeyMaps, but use a dictionary of a key and value for the binding.

```python
import simple_events

CONTROLLER = simple_events.getKeyListener("controller_stuff")

@CONTROLLER.bind("example", {"button": 0})
def test_func(_):
    pass
```

In this case, it will look for the "button" attribute of a Joystick event, and will be called on button 0. It should be noted, different controller types label their buttons differently.

Instance-specific attributes like "instance_id" and "value" are disregarded by the Joy Map. 

For more information on pygame and joystick/controller behavior, including examples of button maps, see [here](https://www.pygame.org/docs/ref/joystick.html)


<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Passing Events to the Managers

With functions registered to the managers, you now need to tie the managers into the event queue.

There are two options:

1. Notify All

```python
import simple_events

import pygame

# pygame setup and initialization

while game_is_running:
    # Frame rate handling
    for event in pygame.event.get():
        simple_events.notifyEventManagers(event)
        simple_events.notifyKeyListeners(event)
    # Game Loop stuff

```

This ensures that every manager is being fed events as they happen.

2. Direct Notification

```python
import simple_events

import pygame

# pygame setup and initialization

MANAGER = simple_events.getEventManager("Example") # Remember, the handle needs to be the same as wherever events are assigned
MANAGER2 = simple_events.getEventManager("Example2")
KEYBINDS = simple_events.getKeyListener("Example")

while game_is_running:
    # Frame rate handling
    for event in pygame.event.get():
        MANAGER.notify(event)
        MANAGER2.notify(event)
        KEYBINDS.notify(event)
    # Game Loop stuff

```

The developer must track the managers and is responsible for feeding them the events. This allows greater control over if and when a given manager is activated.
For example, it may be desirable to have a manager that handles menu functions, and another gameplay functions. This way, the game loop can test for game state, and run only the menu functions when in menu, and only gameplay functions while playing.

Additionally, event managers and key listeners support calling _only_ sequential and _only_ concurrent functions and methods, if desired. This may be done using the \[manager\].notify_sequential(event) and \[manager\].notify_concurrent(event) methods, respectively. It should be noted that calling both the general and specific notifies on the same frame will call those functions twice.

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Concurrency

By default, functions are called using Python's threading library. This means that the called functions can be blocked, such as by using time.sleep, without blocking the rest of the program.

_However_, this comes at the cost of thread safety. These functions may be able to change state at unpredictable times, and generate race conditions. Always use caution when dealing with concurrency, and investigate [Python's threading library](https://docs.python.org/3/library/threading.html#threading.Lock) for more info on best practices regarding concurrency.

Optionally, you can use
```python
@KEYLISTENER.sequential
```
to mark a function as sequential. Sequential functions and methods will called after the concurrent functions and methods, and will run one after the other. They lose out on being easily blockable, but reduce the risk of forming race conditions, especially if not sharing resources with any concurrent functions.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ROADMAP -->
## Roadmap

- [ ] Add support for additional formats for saving and loading keybinds.
- [ ] Add a utility for simplifying the default input for controller binds.
<!--
- [ ] Feature 2
- [ ] Feature 3
    - [ ] Nested Feature
-->

See the [open issues](https://github.com/BetterBuiltFool/event_handler/issues) for a full list of proposed features (and known issues).

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTRIBUTING -->
<!--
## Contributing

Contributions are what make the open source community such an amazing place to learn, inspire, and create. Any contributions you make are **greatly appreciated**.

If you have a suggestion that would make this better, please fork the repo and create a pull request. You can also simply open an issue with the tag "enhancement".
Don't forget to give the project a star! Thanks again!

1. Fork the Project
2. Create your Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit your Changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the Branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

<p align="right">(<a href="#readme-top">back to top</a>)</p>

### Top contributors:

<a href="https://github.com/BetterBuiltFool/event_handler/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=BetterBuiltFool/event_handler" alt="contrib.rocks image" />
</a>
-->



<!-- LICENSE -->
## License

Distributed under the MIT License. See `LICENSE.txt` for more information.

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- CONTACT -->
## Contact

Better Built Fool - betterbuiltfool@gmail.com
<!--
 - [@twitter_handle](https://twitter.com/twitter_handle)
-->

Project Link: [https://github.com/BetterBuiltFool/event_handler](https://github.com/BetterBuiltFool/event_handler)

<p align="right">(<a href="#readme-top">back to top</a>)</p>



<!-- ACKNOWLEDGMENTS -->
<!--## Acknowledgments

* []()
* []()
* []()

<p align="right">(<a href="#readme-top">back to top</a>)</p>
-->


<!-- MARKDOWN LINKS & IMAGES -->
<!-- https://www.markdownguide.org/basic-syntax/#reference-style-links -->
[contributors-shield]: https://img.shields.io/github/contributors/BetterBuiltFool/event_handler.svg?style=for-the-badge
[contributors-url]: https://github.com/BetterBuiltFool/event_handler/graphs/contributors
[forks-shield]: https://img.shields.io/github/forks/BetterBuiltFool/event_handler.svg?style=for-the-badge
[forks-url]: https://github.com/BetterBuiltFool/event_handler/network/members
[stars-shield]: https://img.shields.io/github/stars/BetterBuiltFool/event_handler.svg?style=for-the-badge
[stars-url]: https://github.com/BetterBuiltFool/event_handler/stargazers
[issues-shield]: https://img.shields.io/github/issues/BetterBuiltFool/event_handler.svg?style=for-the-badge
[issues-url]: https://github.com/BetterBuiltFool/event_handler/issues
[license-shield]: https://img.shields.io/github/license/BetterBuiltFool/event_handler.svg?style=for-the-badge
[license-url]: https://github.com/BetterBuiltFool/event_handler/blob/main/LICENSE
[linkedin-shield]: https://img.shields.io/badge/-LinkedIn-black.svg?style=for-the-badge&logo=linkedin&colorB=555
[linkedin-url]: https://linkedin.com/in/linkedin_username
[product-screenshot]: images/screenshot.png
[Next.js]: https://img.shields.io/badge/next.js-000000?style=for-the-badge&logo=nextdotjs&logoColor=white
[Next-url]: https://nextjs.org/
[python.org]: https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54
[python-url]: https://www.python.org/
[React.js]: https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB
[React-url]: https://reactjs.org/
[Vue.js]: https://img.shields.io/badge/Vue.js-35495E?style=for-the-badge&logo=vuedotjs&logoColor=4FC08D
[Vue-url]: https://vuejs.org/
[Angular.io]: https://img.shields.io/badge/Angular-DD0031?style=for-the-badge&logo=angular&logoColor=white
[Angular-url]: https://angular.io/
[Svelte.dev]: https://img.shields.io/badge/Svelte-4A4A55?style=for-the-badge&logo=svelte&logoColor=FF3E00
[Svelte-url]: https://svelte.dev/
[Laravel.com]: https://img.shields.io/badge/Laravel-FF2D20?style=for-the-badge&logo=laravel&logoColor=white
[Laravel-url]: https://laravel.com
[Bootstrap.com]: https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white
[Bootstrap-url]: https://getbootstrap.com
[JQuery.com]: https://img.shields.io/badge/jQuery-0769AD?style=for-the-badge&logo=jquery&logoColor=white
[JQuery-url]: https://jquery.com 
[pypi-url]: https://pypi.org/project/project_name/
[pip-url]: https://pip.pypa.io/en/stable/