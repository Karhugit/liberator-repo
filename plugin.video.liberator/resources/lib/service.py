# -*- coding: utf-8 -*-
import xbmc, xbmcgui
import json
import threading
from concurrent.futures import ThreadPoolExecutor
import time
from apis.orac_api import OracClient, OracClientError
from caches.base_cache import get_ipc_db_path, connect_database, close_database
import sqlite3
from caches.settings_cache import get_setting
import xbmcaddon
import concurrent.futures
import asyncio

from modules.async_manager import AsyncManager


pause_services_prop = 'liberator.pause_services'
firstrun_update_prop = 'liberator.firstrun_update'
current_skin_prop = 'liberator.current_skin'

ADDON = xbmcaddon.Addon('plugin.video.liberator')
REQUEST_PROP = 'REQUEST_PROP'
RESPONSE_PROP = 'RESPONSE_PROP'

def logger(heading, function):
    xbmc.log('###%s###: %s' % (heading, function), 1)


def _initialize_orac_client():
    """
    Initializes the OracClient instance from addon settings.
    Displays notifications if the address is not set or invalid.
    """
    orac_address = get_setting('orac_address')

    if not orac_address:
        logger("Orac",  "No Orac address set in addon settings.")
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Orac address not set. Please check addon settings.", xbmcgui.NOTIFICATION_ERROR)
        return None # Indicate initialization failed

    # Ensure it starts with http:// or https://, default to http:// if missing
    if not orac_address.startswith(('http://', 'https://')):
        orac_address = f"http://{orac_address}"

    # Append default port :5555 if no port is specified (basic check)
    if ':' not in orac_address.split('/')[-1] and not orac_address.endswith(':5555'):
        orac_address = f"{orac_address}:5555"
        
    try:
        orac_client = OracClient(orac_address)
        logger("Orac", "Client initialized with base URL: {orac_client.base_url}")
        return orac_client
    except Exception as e:
        logger("Orac", f"Failed to initialize Orac client: {e}")
        return None

class LiberatorService(xbmc.Monitor):
    def __init__(self, OracClient, db_path):
        super().__init__()
        self.window = xbmcgui.Window(10000)
        self.orac_client = OracClient
        self.db_path = db_path
        self.dbcon = connect_database('ipc_data_db')
        if not self.dbcon:
            logger("Liberator", "Service: Could not connect to database.")
            self.mon.abort()
        self._setup_database()
        logger("Liberator", "Service: Initialized and listening.")
        # Add a flag to control the run loop
        self._abort_flag = threading.Event()
        # Define the dispatch table
        self._dispatch_table = {
            'get_next_episodes': self.orac_client.get_next_episode_info,
            'get_movie_list_overview': self.orac_client.get_movie_list_overview,
            'get_tvshow_list_overview': self.orac_client.get_tvshow_list_overview,
            'get_lists': self.orac_client.get_lists,
            'get_genres': self.orac_client.get_genres,
            'get_movie_details': self.orac_client.get_movie_details,
            'get_show_details': self.orac_client.get_show_details,
            'discover_movie': self.orac_client.discover_movie,
            'discover_tvshow': self.orac_client.discover_tvshow,
            'mark_episode_watched': self.orac_client.mark_episode_watched,
            'mark_movie_watched': self.orac_client.mark_movie_watched,
            'search_tmdb': self.orac_client.search_tmdb,
            'add_list_options': self.orac_client.add_list_options,
            'remove_list_options': self.orac_client.remove_list_options,
            'add_to_list': self.orac_client.add_to_list,
            'remove_from_list': self.orac_client.remove_from_list,
            'update_trakt_tokens': self.orac_client.update_trakt_tokens,
            'update_simkl_tokens': self.orac_client.update_simkl_tokens,
            'get_fast_start_episode': self.orac_client.get_fast_start_episode,
            'add_ext_index': self.orac_client.add_ext_index,
            'del_ext_index': self.orac_client.del_ext_index,
            'get_external_indexes': self.orac_client.get_external_indexes,
            'get_tmdb_keywords': self.orac_client.get_tmdb_keywords,
            'update_list_library_status': self.orac_client.update_list_library_status,
            'unlike_trakt_list': self.orac_client.unlike_trakt_list,
            'get_list_overview': self.orac_client.get_list_overview,
            'force_sync': self.orac_client.force_orac_sync,
            'get_seasons_overview': self.orac_client.get_seasons_overview,
            'get_orac_scrape': self.orac_client.get_orac_scrape,
            'mark_tvshow_watched': self.orac_client.mark_tvshow_watched,
            'drop_tvshow': self.orac_client.drop_tvshow,
            'mark_season_watched': self.orac_client.mark_season_watched,
            'get_internal_indexes': self.orac_client.get_internal_indexes,
            'add_internal_index': self.orac_client.add_internal_index,
            'del_internal_index': self.orac_client.del_internal_index,
            'internal_index_contents': self.orac_client.internal_index_contents,
            'update_tmdb_tokens': self.orac_client.update_tmdb_tokens,
            'update_mdblist_tokens': self.orac_client.update_mdblist_tokens,
            'update_aiostreams_settings': self.orac_client.update_aiostreams_settings,
            'get_available_languages': self.orac_client.get_available_languages,
            'get_available_languages': self.orac_client.get_available_languages,
            'tags': self.orac_client.handle_tags,
            'recommendations_movies': self.orac_client.get_movie_recommendations,
            'get_reviews': self.orac_client.get_reviews,
            'mark_undesirable': self.orac_client.mark_undesirable,
            'get_providers': self.orac_client.get_watch_providers,
            'get_collections': self.orac_client.get_collections,
        }
        self.log_counter = 0
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)



    def _setup_database(self):
        try:
            #Connect to the database using the path defined in the constants
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS requests (
                    uuid TEXT PRIMARY KEY,
                    data_json TEXT,
                    timestamp REAL
                )
            """)
            conn.commit()
            conn.close()
        except Exception as e:
            logger("Liberator", f"Service: Failed to set up database: {e}")

    async def _process_request_async(self, request_data_str):
        logger("Liberator", f"Service: Processing request data: {request_data_str}")
        if not self.db_path:
            logger("Liberator", "Service: No database path available.")
            return
        dbcon = None
        try:
            request_data = json.loads(request_data_str)
            request_id = request_data.get("uuid")
            mode = request_data.get("mode")
            params = request_data.get("params", {})
            json_body = request_data.get("json_body")

            orac_method = self._dispatch_table.get(mode)
            if not orac_method:
                raise ValueError(f"Unknown mode: {mode}")

            log_msg = f"Service: Sending orac request '{request_id}' for mode '{mode}'"
            if params: log_msg += f" with params: {params}"
            if json_body: log_msg += f" with json_body: {json_body}"
            logger("Liberator", log_msg)

            if json_body:
                orac_response = await asyncio.get_event_loop().run_in_executor(
                    self.executor, lambda: orac_method(json_body)
                )
            else:
                orac_response = await asyncio.get_event_loop().run_in_executor(
                    self.executor, lambda: orac_method(params)
                )


            # Open a new connection for this specific task
            dbcon = sqlite3.connect(self.db_path, timeout=20.0)
            cursor = dbcon.cursor()
            
            cursor.execute(
                "INSERT INTO requests (uuid, data_json, timestamp) VALUES (?, ?, ?)",
                (request_id, json.dumps(orac_response), time.time())
            )
            dbcon.commit()
            
            logger("Liberator", f"Service: Wrote data for '{request_id}' to DB.")

        except OracClientError as e:
            logger("Liberator", f"Service: Orac client error for request '{request_id}' (mode: {mode}): {e}")
            # On Orac failure, write an empty response to the DB immediately
            try:
                dbcon = sqlite3.connect(self.db_path, timeout=20.0)
                cursor = dbcon.cursor()
                cursor.execute(
                    "INSERT INTO requests (uuid, data_json, timestamp) VALUES (?, ?, ?)",
                    (request_id, json.dumps(None), time.time())
                )
                dbcon.commit()
                logger("Liberator", f"Service: Wrote empty response for failed request '{request_id}' to DB.")
            except Exception as db_e:
                logger("Liberator", f"Service: Failed to write empty response to DB for '{request_id}': {db_e}")
            
        except Exception as e:
            logger("Liberator", f"Service: Failed to process request '{request_id}' for mode '{mode}': {e}")
            error_payload = {"error": str(e), "status": "error"}
            if dbcon:
                try:
                    cursor = dbcon.cursor()
                    cursor.execute(
                        "INSERT INTO requests (uuid, data_json, timestamp) VALUES (?, ?, ?)",
                        (request_id, json.dumps(error_payload), time.time())
                    )
                    dbcon.commit()
                except Exception as db_e:
                    logger("Liberator", f"Service: Failed to log error to DB for '{request_id}': {db_e}")
        finally:
            if dbcon:
                close_database(dbcon)


    def run(self):
        notification_prop = "REQUEST_NOTIFICATION_PROP"
        
        while not self._abort_flag.is_set():
            queue_str = self.window.getProperty(notification_prop)
#            logger("Liberator", f"Service: Checking notification queue: {queue_str}")

            if queue_str:
                queue = json.loads(queue_str)
                if queue:
                    # Clear the queue immediately to prevent race conditions
                    self.window.clearProperty(notification_prop)
                    
                    # Submit each request in the queue to the async manager
                    
                    for request_prop_key in queue:
                        xbmc.sleep(10)  # Sleep to prevent rapid-fire processing
                        request_data_str = self.window.getProperty(request_prop_key)
                        logger("Liberator", f"Service: Processing request with key: {request_prop_key}")
                        if request_data_str:
                            self.window.clearProperty(request_prop_key)
                            logger("Liberator", f"Service: Submitting request for processing: {request_data_str}")
#                            self.async_manager.submit_to_background(self._process_request_async(request_data_str))
                            AsyncManager.submit_to_background(self._process_request_async(request_data_str))

            xbmc.sleep(100)

    def abort(self):
        """
        Signal the run loop to stop.
        This should be called when the service is shutting down.
        """
        logger("Liberator", "Service: Abort signal received.")
        if self.dbcon:
            close_database(self.dbcon)
            logger("Liberator", "Service: Database connection closed.")

        if self.executor:
            self.executor.shutdown(wait=True)
            logger("Liberator", "Service: Thread pool executor shut down.")

        self._abort_flag.set()
        self.window.clearProperty(REQUEST_PROP)



class SetAddonConstants:
    def run(self):
        logger('Liberator', 'SetAddonConstants Service Starting')
        import xbmcgui, xbmcaddon, xbmcvfs
        addon_object = xbmcaddon.Addon('plugin.video.liberator')
        self.window = xbmcgui.Window(10000)
        _info = addon_object.getAddonInfo
        addon_items = [('liberator.addon_version', _info('version')),
                    ('liberator.addon_path', _info('path')),
                    ('liberator.addon_profile', xbmcvfs.translatePath(_info('profile'))),
                    ('liberator.addon_icon', xbmcvfs.translatePath(_info('icon'))),
                    ('liberator.addon_fanart', xbmcvfs.translatePath(_info('fanart')))]
        for item in addon_items: self.set_property(*item)
        return logger('Liberator', 'SetAddonConstants Service Finished')

    def set_property(self, prop, value):
        self.window.setProperty(prop, value)

class DatabaseMaintenance:
    def run(self):
        logger('Liberator', 'DatabaseMaintenance Service Starting')
        from caches.base_cache import make_databases
        make_databases()
        return logger('Liberator', 'DatabaseMaintenance Service Finished')

class SyncSettings:
    def run(self):
        logger('Liberator', 'SyncSettings Service Starting')
        from caches.settings_cache import sync_settings
        sync_settings()
        logger('Liberator', 'SyncSettings Service Finished')

class CustomFonts:
    def run(self):
        logger('Liberator', 'CustomFonts Service Starting')
        from windows.base_window import FontUtils
        monitor, player, window = xbmc.Monitor(), xbmc.Player(), xbmcgui.Window(10000)
        wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
        window.clearProperty(current_skin_prop)
        font_utils = FontUtils()
        while not monitor.abortRequested():
            font_utils.execute_custom_fonts()
            if window.getProperty(pause_services_prop) == 'true' or is_playing(): sleep = 20
            else: sleep = 10
            wait_for_abort(sleep)
        try: del monitor
        except: pass
        try: del player
        except: pass
        return logger('Liberator', 'CustomFonts Service Finished')



class UpdateCheck:
    def run(self):
        window = xbmcgui.Window(10000)
        if window.getProperty(firstrun_update_prop) == 'true': return
        logger('Liberator', 'UpdateCheck Service Starting')
        from time import time
        from modules.updater import update_check
        from modules.settings import update_action, update_delay
        end_pause = time() + update_delay()
        monitor, player = xbmc.Monitor(), xbmc.Player()
        wait_for_abort, is_playing = monitor.waitForAbort, player.isPlayingVideo
        while not monitor.abortRequested():
            while time() < end_pause: wait_for_abort(1)
            while window.getProperty(pause_services_prop) == 'true' or is_playing(): wait_for_abort(1)
            update_check(update_action())
            break
        window.setProperty(firstrun_update_prop, 'true')
        try: del monitor
        except: pass
        try: del player
        except: pass
        return logger('Liberator', 'UpdateCheck Service Finished')

class WidgetRefresher:
    def run(self):
        logger('Liberator', 'WidgetRefresher Service Starting')
        from time import time
        from caches.settings_cache import get_setting
        from modules.kodi_utils import home, run_plugin
        monitor, player = xbmc.Monitor(), xbmc.Player()
        wait_for_abort, self.is_playing = monitor.waitForAbort, player.isPlayingVideo
        self.window = xbmcgui.Window(10000)
        self.get_setting = get_setting
        self.home = home
        self.window.setProperty('liberator.refresh_widgets', 'true')
        self.set_next_refresh(time())
        wait_for_abort(20)
        while not monitor.abortRequested():
            try:
                wait_for_abort(10)
                self.window.clearProperty('liberator.refresh_widgets')
                offset = int(self.get_setting('liberator.widget_refresh_timer', '60'))
                if offset != self.offset:
                    self.set_next_refresh(time())
                    continue
                if self.condition_check(): continue
                if self.next_refresh < time():
                    run_plugin({'mode': 'refresh_widgets', 'show_notification': self.get_setting('liberator.widget_refresh_notification', 'false')}, block=True)
                    logger('Liberator', 'WidgetRefresher Service - Widgets Refreshed')
                    self.set_next_refresh(time())
            except: pass
        try: del monitor
        except: pass
        try: del player
        except: pass
        return logger('Liberator', 'WidgetRefresher Service Finished')

    def condition_check(self):
        if not self.home(): return True
        if self.next_refresh == None or self.is_playing() or self.window.getProperty(pause_services_prop) == 'true': return True
        if self.window.getProperty('liberator.window_loaded') == 'true': return True 
        try:
            window_stack = json.loads(self.window.getProperty('liberator.window_stack'))
            if window_stack or window_stack == []: return True
        except: pass
        return False

    def set_next_refresh(self, _time):
        self.offset = int(self.get_setting('liberator.widget_refresh_timer', '60'))
        if self.offset: self.next_refresh = _time + (self.offset*60)
        else: self.next_refresh = None

class OracStatusMonitor:
    def run(self):
        logger('Liberator', 'OracStatusMonitor Service Starting')
        from caches.settings_cache import get_setting, set_setting
        from modules.kodi_utils import notification
        import requests

        monitor = xbmc.Monitor()
        wait_for_abort = monitor.waitForAbort
        self.window = xbmcgui.Window(10000)

        # Clear property at start
        self.window.clearProperty('liberator.orac_offline')

        is_online = None

        # Give a small 3-second wait for network/system initialization at boot
        wait_for_abort(3)

        # 30 minutes in seconds = 1800
        interval = 1800

        while not monitor.abortRequested():
            try:
                orac_address = get_setting('orac_address')
                if not orac_address:
                    wait_for_abort(30)
                    continue

                if not orac_address.startswith(('http://', 'https://')):
                    orac_address = f"http://{orac_address}"
                if ':' not in orac_address.split('/')[-1] and not orac_address.endswith(':5555'):
                    orac_address = f"{orac_address}:5555"

                url = f"{orac_address.rstrip('/')}/api/status"

                try:
                    response = requests.get(url, timeout=5)
                    response.raise_for_status()
                    data = response.json()

                    if data.get('status') == 'online':
                        if is_online is False:
                            # State changed from offline to online
                            self.window.clearProperty('liberator.orac_offline')
                            notification('Connected to Orac Server')
                        is_online = True

                        # Sync settings
                        trakt = data.get('trakt', {})
                        simkl = data.get('simkl', {})
                        tmdb = data.get('tmdb', {})
                        mdblist = data.get('mdblist', {})

                        # Trakt
                        if 'user' in trakt:
                            self._sync_setting('trakt.user', trakt['user'])
                        if 'token' in trakt:
                            self._sync_setting('trakt.token', trakt['token'])
                        if 'refresh' in trakt:
                            self._sync_setting('trakt.refresh', trakt['refresh'])
                        if 'expires' in trakt:
                            self._sync_setting('trakt.expires', trakt['expires'])

                        # Simkl
                        if 'user' in simkl:
                            self._sync_setting('simkl.user', simkl['user'])
                        if 'token' in simkl:
                            self._sync_setting('simkl.token', simkl['token'])

                        # TMDb
                        if 'user' in tmdb:
                            self._sync_setting('tmdb.user', tmdb['user'])
                        if 'session_id' in tmdb:
                            self._sync_setting('tmdb.session_id', tmdb['session_id'])

                        # MDbList
                        if 'api' in mdblist:
                            self._sync_setting('mdblist_api', mdblist['api'])

                except Exception as e:
                    # Connection failed
                    if is_online is not False:
                        # State changed to offline (either from None or True)
                        self.window.setProperty('liberator.orac_offline', 'true')
                        notification('Connection to Orac Server Failed!')
                    is_online = False

            except Exception as e:
                logger('Liberator', f'OracStatusMonitor error: {e}')

            # Sleep for the interval, but wake up early if abort is requested
            wait_for_abort(interval)

        try: del monitor
        except: pass
        return logger('Liberator', 'OracStatusMonitor Service Finished')

    def _sync_setting(self, setting_id, remote_value):
        from caches.settings_cache import get_setting, set_setting
        local_value = get_setting(setting_id, 'empty_setting')
        if local_value != remote_value:
            logger('Liberator', f'OracStatusMonitor: Syncing setting {setting_id} from {local_value} -> {remote_value}')
            set_setting(setting_id, remote_value)

class AutoStart:
    def run(self):
        logger('Liberator', 'AutoStart Service Starting')
        from modules.settings import auto_start_liberator
        if auto_start_liberator():
            from modules.kodi_utils import run_addon
            run_addon()
        return logger('Liberator', 'AutoStart Service Finished')

class LiberatorMonitor(xbmc.Monitor):
    def __init__ (self):
        super().__init__()
#		xbmc.Monitor.__init__(self)
        self.executor = None
        self.liberator_service = None
#        self.startServices()

    def run_all_services(self):
        logger('Liberator', 'Starting all services...')
        try:
            # All initialization and startup code goes here
            SetAddonConstants().run()
            DatabaseMaintenance().run()
            SyncSettings().run()

            orac_client_instance = _initialize_orac_client()
            if not orac_client_instance:
                logger('Liberator', 'Orac Client Initialization Failed. Stopping Services.')
                return # Exit the run method gracefully

            ipc_data_db = get_ipc_db_path()
            
            # Start the AsyncManager's background asyncio loop
            AsyncManager.start_background_loop()
            
            # Instantiate the new service
            self.liberator_service = LiberatorService(OracClient=orac_client_instance, db_path=ipc_data_db)
            
            # Use a ThreadPoolExecutor to run all services concurrently
            self.executor = ThreadPoolExecutor(max_workers=4)
            self.executor.submit(CustomFonts().run)
            self.executor.submit(WidgetRefresher().run)
            self.executor.submit(OracStatusMonitor().run)
            
            # We submit the main LiberatorService polling loop as a task
            self.executor.submit(self.liberator_service.run)
            
            AutoStart().run()
            self.additionalService()

            # The main monitor loop just keeps the service alive and responsive
            self.waitForAbort()

        except Exception as e:
            logger('Liberator', f'An unexpected error occurred: {e}')

        finally:
            # THIS IS THE CRITICAL SHUTDOWN LOGIC
            logger('Liberator', 'Abort requested. Shutting down all services...')

            # 1. Gracefully shut down the main LiberatorService loop
            if self.liberator_service:
                # The abort() method should signal the loop to exit
                self.liberator_service.abort() 

            # 2. Shut down the AsyncManager loop
            AsyncManager.stop_background_loop()

            # 3. Shut down the ThreadPoolExecutor gracefully
            if self.executor:
                self.executor.shutdown(wait=True)
                
            logger('Liberator', 'All services shut down gracefully. Exiting.')

    def startServices(self):
        SetAddonConstants().run()
        DatabaseMaintenance().run()
        SyncSettings().run()

        orac_client_instance = _initialize_orac_client()
        if not orac_client_instance:
            logger('Liberator', 'Orac Client Initialization Failed. Stopping Services.')
            exit()

        ipc_data_db = get_ipc_db_path()

        AsyncManager.start_background_loop()
        service = LiberatorService(OracClient=orac_client_instance, db_path=ipc_data_db)
        service.run()

        with ThreadPoolExecutor(max_workers=4) as executor:
            executor.submit(CustomFonts().run)
            executor.submit(WidgetRefresher().run)
            executor.submit(OracStatusMonitor().run)
        AutoStart().run()
        self.additionalService()

    def additionalService(self):
        logger('Liberator', 'Additional Service Starting')

        logger('Liberator', 'Additional Service Finished')

    def onNotification(self, sender, method, data):
        if method in ('GUI.OnScreensaverActivated', 'System.OnSleep'):
            xbmcgui.Window(10000).setProperty(pause_services_prop, 'true')
            logger('OnNotificationActions', 'PAUSING Liberator Services Due to Device Sleep')
        elif method in ('GUI.OnScreensaverDeactivated', 'System.OnWake'):
            xbmcgui.Window(10000).clearProperty(pause_services_prop)
            logger('OnNotificationActions', 'UNPAUSING Liberator Services Due to Device Awake')

logger('Liberator', 'Main Monitor Service Starting')
monitor = LiberatorMonitor()
monitor.run_all_services()
logger('Liberator', 'Main Monitor Service Finished')
