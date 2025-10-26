import asyncio
from .bot import build_app

async def main():
    app = build_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    print("Bot started. Press Cntr+C to stop.")
    try:
        await asyncio.Event().wait()
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    import os
    if os.name == "nt":
        import asyncio as _a
        _a.set_event_loop_policy(_a.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())