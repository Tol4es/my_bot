from telegram.ext import Application
from .start import get_handlers as start_handlers
from .text import get_handlers as text_handlers
from .callbacks import get_handlers as callbacks_handlers
from .admin import get_handlers as admin_handlers

def register_handlers(app: Application) -> None:
    for h in (start_handlers() + admin_handlers() + callbacks_handlers() + text_handlers()):
        app.add_handler(h)