import threading
import asyncio
import xbmc
from modules.kodi_utils import logger

ADDON_ID = "script.liberator"

class AsyncManager:
    """
    Manages a single background thread and an associated asyncio event loop.
    This allows a synchronous Kodi service to submit non-blocking tasks.
    """
    
    _loop: asyncio.AbstractEventLoop = None
    _thread: threading.Thread = None

    @classmethod
    def _run_loop_in_thread(cls):
        """
        Target function for the background thread.
        Sets up and runs the asyncio event loop.
        """
        logger("Liberator","AsyncManager: Background loop starting...")
        cls._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(cls._loop)
        cls._loop.run_forever()
        logger("Liberator","AsyncManager: Background loop finished.")

    @classmethod
    def start_background_loop(cls):
        """
        Starts the background thread and its asyncio event loop.
        This should be called once by the service.
        """
        if cls._thread and cls._thread.is_alive():
            logger("Liberator","AsyncManager: Loop already running.")
            return

        cls._thread = threading.Thread(target=cls._run_loop_in_thread, daemon=True)
        cls._thread.start()
        logger("Liberator","AsyncManager: Background loop started in thread.")

    @classmethod
    def stop_background_loop(cls):
        """
        Stops the event loop and joins the thread.
        This should be called once when the service is shutting down.
        """
        if not cls._loop or not cls._thread or not cls._thread.is_alive():
            logger("Liberator","AsyncManager: Loop is not running.")
            return

        logger("Liberator","AsyncManager: Stopping background loop...")
        
        # This part is critical for a clean shutdown
        # Get all the tasks running on the loop
        tasks = [t for t in asyncio.all_tasks(cls._loop) if not t.done()]
        
        # Cancel all pending tasks
        for task in tasks:
            task.cancel()

        # Run the loop briefly to allow cancelled tasks to finish
        cls._loop.call_soon_threadsafe(cls._loop.stop)
        
        # Wait for the thread to exit
        cls._thread.join()

        # Clean up
        cls._loop = None
        cls._thread = None
        logger("Liberator","AsyncManager: Loop successfully stopped.")
        
    @classmethod
    def submit_to_background(self, coro):
        """Submits a coroutine to the event loop from another thread."""
        if not asyncio.iscoroutine(coro):
            logger("Liberator", "AsyncManager: Submitted task is not a coroutine.")
            return False

        if not self._loop or not self._loop.is_running():
            logger("Liberator", "AsyncManager: Event loop is not running. Cannot submit task.")
            return False

        # This is the correct, thread-safe way to submit a coroutine
        # to a running event loop in a different thread.
        future = asyncio.run_coroutine_threadsafe(coro, self._loop)
        
        # You can optionally wait for the result or catch exceptions.
        # For our use case, we just submit and don't wait for a response.
        return True