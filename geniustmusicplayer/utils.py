import functools
import inspect
from functools import wraps

from kivy.uix.screenmanager import Screen
from kivy.logger import Logger
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.uix.snackbar import Snackbar
from kivymd.uix.button import MDFlatButton


def create_snackbar(text, callback):
    snackbar = Snackbar(
        text=text,
        snackbar_x="10dp",
        snackbar_y="10dp",
    )
    snackbar.size_hint_x = (
        Window.width - (snackbar.snackbar_x * 2)
    ) / Window.width
    snackbar.buttons = [
        MDFlatButton(
            text="RETRY",
            text_color=(1, 1, 1, 1),
            on_release=callback,
        ),
    ]
    return snackbar


def get_class_that_defined_method(meth):
    if isinstance(meth, functools.partial):
        return get_class_that_defined_method(meth.func)
    if (inspect.ismethod(meth)
        or (inspect.isbuiltin(meth)
            and getattr(meth, '__self__', None) is not None
            and getattr(meth.__self__, '__class__', None))):
        for cls in inspect.getmro(meth.__self__.__class__):
            if meth.__name__ in cls.__dict__:
                return cls
        meth = getattr(meth, '__func__', meth)  # fallback to __qualname__ parsing
    if inspect.isfunction(meth):
        cls = getattr(inspect.getmodule(meth),
                      meth.__qualname__.split('.<locals>', 1)[0].rsplit('.', 1)[0],
                      None)
        if isinstance(cls, type):
            return cls
    return getattr(meth, '__objclass__', None)  # handle special descriptor objects


def log(func):
    """logs entering and exiting functions for debugging."""

    @wraps(func)
    def wrapper(*args, **kwargs):
        cls = get_class_that_defined_method(func)
        if cls is not None:
            cls = cls.__name__
        # Logger.debug("Entering: %s.%s", cls, func.__name__)
        result = func(*args, **kwargs)
        # Logger.debug("Exiting: %s.%s (return value: %s)",
        #             cls, func.__name__, repr(result))
        return result

    return wrapper


@log
def switch_screen(page, name):
    screen = Screen(name=name)
    screen.add_widget(page)
    MDApp.get_running_app().screen_manager.switch_to(screen)
    # app.screen_manager.add_widget(screen)
    # app.screen_manager.current = name
    # for widget in app.screen_manager.children[:]:
    #     if widget.name != name:
    #         print(widget)
    #         app.screen_manager.remove_widget(widget)
