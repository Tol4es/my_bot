from telegram.ext import ApplicationBuilder
from .config import settings
from .logging_setup import setup_logging
from .db.sqlite import init_db
from .handlers import register_handlers

def build_app():
    setup_logging()
    init_db()

    app = (
        ApplicationBuilder()
        .token(settings.token)
        .concurrent_updates(True)
        .build()
    )

    register_handlers(app)
    return app