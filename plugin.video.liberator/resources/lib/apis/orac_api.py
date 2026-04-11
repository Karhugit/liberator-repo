import json
import time
import requests
from urllib.parse import unquote, quote_plus
from caches.settings_cache import get_setting, set_setting
from modules import kodi_utils, settings
from modules.utils import sort_list, sort_for_article, get_datetime, timedelta, replace_html_codes, copy2clip, title_key, jsondate_to_datetime as js2date
from modules.thread_manager import make_thread_list
logger = kodi_utils.logger
import asyncio
import xbmcaddon
import xbmcgui
import uuid
from caches.base_cache import get_ipc_db_path, connect_database, close_database
import sqlite3
from modules.kodi_utils import select_dialog


REQUEST_PROP = "REQUEST_PROP_"
RESPONSE_PROP = "RESPONSE_PROP"

class OracClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip('/')

    def _get_json(self, endpoint, params=None, put=False, json_body=None):
        url = f"{self.base_url}/{endpoint}"
        log_msg = f"Requesting URL: {url} with params: {params} and json_body: {json_body}"
        logger("OracClient", f"{log_msg}")
        try:
            if put:
                response = requests.put(url, params=params, json=json_body, timeout=10)
            else:
                response = requests.get(url, params=params, timeout=10)
            
            response.raise_for_status()

            # For PUT requests, an empty body is a valid success response.
            if put and not response.content:
                return {'status': 'ok'}
            
            return response.json()
        except requests.exceptions.RequestException as e:
            logger("OracClient", f"Request error accessing {url}: {e}")
            raise OracClientError(f"Network error connecting to Orac: {e}") from e
        except ValueError as e: # Catches JSON decoding errors
            logger("OracClient", f"Request error accessing {url}: {e}")
            raise OracClientError(f"Network error connecting to Orac: {e}") from e

    def get_movie_list_overview(self, params):
        return self._get_json("list", params=params)

    def get_tvshow_list_overview(self, params):
        return self._get_json("list", params=params)

    def get_list_overview(self, params):
        """Fetches a general list overview from Orac (mixed content)."""
        return self._get_json("list", params=params)

    def get_next_episode_info(self, params=None):
        return self._get_json("next_episodes", params=params)

    def get_movie_details(self, params):
        """Fetches movie details from Orac by movie ID."""
        return self._get_json("movie", params=params)

    def get_show_details(self, params):
        """Fetches show details from Orac by show ID."""
        return self._get_json("show", params=params)

    def get_lists(self, params):
        """Fetches lists from Orac based on type and item_type."""
        return self._get_json("lists", params=params)

    def get_genres(self, params):
        """Fetches genres from Orac."""
        return self._get_json("genres", params=params)

    def get_seasons_overview(self, params):
        """Fetches seasons overview from Orac."""
        return self._get_json("seasons", params=params)

    def discover_movie(self, params):
        """Fetches movie discovery results from Orac."""
        return self._get_json("discover/movie", params=params)

    def discover_tvshow(self, params):
        """Fetches TV show discovery results from Orac."""
        return self._get_json("discover/tvshow", params=params)

    def mark_episode_watched(self, params):
        """Marks an episode as watched in Orac."""
        return self._get_json("watched", params=params, put=True)

    def mark_movie_watched(self, params):
        """Marks a movie as watched in Orac."""
        return self._get_json("watched", params=params, put=True)

    def mark_tvshow_watched(self, params):
        """Marks a TV show as watched in Orac."""
        return self._get_json("watched", params=params, put=True)

    def drop_tvshow(self, params):
        """Drops a TV show in Orac."""
        return self._get_json("drop_tvshow", params=params, put=True)

    def force_orac_sync(self, params=None):
        """Triggers a forced sync on the Orac server."""
        return self._get_json("force_sync", params=params)

    def mark_season_watched(self, params):
        """Marks a season as watched in Orac."""
        return self._get_json("watched", params=params, put=True)

    def search_tmdb(self, params):
        """Searches TMDB via Orac."""
        return self._get_json("search_tmdb", params=params)

    def add_list_options(self, params):
        """Gets list options for a list add request."""
        return self._get_json("add_list_options", params=params)

    def remove_list_options(self, params):
        """Gets list options for a list remove request."""
        return self._get_json("remove_list_options", params=params)

    def add_to_list(self, params):
        """Adds an item to a list via Orac."""
        return self._get_json("add_to_list", params=params, put=True)

    def remove_from_list(self, params):
        """Removes an item from a list via Orac."""
        return self._get_json("remove_from_list", params=params, put=True)

    def update_trakt_tokens(self, params):
        """Updates the Trakt tokens in Orac."""
        return self._get_json("update_trakt_tokens", params=params, put=True)

    def update_simkl_tokens(self, params):
        """Updates the Simkl tokens in Orac."""
        return self._get_json("update_simkl_tokens", params=params, put=True)

    def update_tmdb_tokens(self, params):
        """Updates the TMDB tokens/session in Orac."""
        return self._get_json("update_tmdb_tokens", params=params, put=True)

    def update_mdblist_tokens(self, params):
        return self._get_json("update_mdblist_tokens", params=params, put=True)

    def get_fast_start_episode(self, params):
        """Fetches fast start episode details from Orac."""
        return self._get_json("fast_start_episode", params=params)

    def get_orac_scrape(self, params):
        """Fetches scrape results from Orac."""
        return self._get_json("scrape", params=params)

    def add_ext_index(self, json_body):
        """Adds an external index to Orac."""
        return self._get_json("add_ext_index", json_body=json_body, put=True)

    def del_ext_index(self, params):
        """Deletes an external index from Orac."""
        return self._get_json("del_ext_index", params=params, put=True)

    def get_external_indexes(self, params):
        """Fetches external indexes from Orac."""
        return self._get_json("get_external_indexes", params=params)

    def get_tmdb_keywords(self, params):
        """Fetches TMDB keywords from Orac."""
        return self._get_json("tmdb_keywords", params=params)
    
    def update_list_library_status(self, params):
        """Updates the library status of a list in Orac."""
        return self._get_json("update_list_library_status", params=params, put=True)
    
    def unlike_trakt_list(self, params):
        """Unlikes a list from Trakt in Orac."""
        return self._get_json("unlike_trakt_list", params=params, put=True)

    def get_internal_indexes(self, params):
        """Fetches internal indexes from Orac."""
        return self._get_json("get_internal_indexes", params=params)

    def add_internal_index(self, json_body):
        """Adds an internal index to Orac."""
        return self._get_json("add_internal_index", json_body=json_body, put=True)

    def del_internal_index(self, params):
        """Deletes an internal index from Orac."""
        return self._get_json("del_internal_index", params=params, put=True)

    def internal_index_contents(self, params):
        """Fetches the contents of an internal index from Orac."""
        return self._get_json("internal_index_contents", params=params)

    def get_available_languages(self, params=None):
        """Fetches available languages from Orac."""
        return self._get_json("get_available_languages", params=params)

    def get_all_tags(self, details=False):
        """
        Fetches all tags from Orac.
        Args:
            details (bool): If True, returns tags with item counts.
        """
        params = {'details': 'true'} if details else None
        return self._get_json("tags", params=params)

    def get_tag_items(self, tag_name):
        """Fetches all items associated with a specific tag."""
        return self._get_json(f"tags/{tag_name}/items")

    def get_tags_for_item(self, media_type, tmdb_id):
        """Fetches tags for a specific item from Orac."""
        return self._get_json(f"tags/{media_type}/{tmdb_id}")

    def add_tag_to_item(self, media_type, tmdb_id, tag_name):
        """Adds a tag to an item via Orac."""
        params = {'media_type': media_type, 'tmdb_id': tmdb_id}
        json_body = {'tag': tag_name}
        return self._get_json("add_tag", params=params, json_body=json_body, put=True)

    def remove_tag_from_item(self, media_type, tmdb_id, tag_name):
        """Removes a tag from an item via Orac."""
        params = {'media_type': media_type, 'tmdb_id': tmdb_id, 'tag': tag_name}
        return self._get_json("remove_tag", params=params, put=True)

    def handle_tags(self, params):
        """
        Handles 'tags' mode requests from IPC.
        Dispatches to appropriate method based on 'action' parameter.
        """
        action = params.get('action')
        if action == 'get_all':
            # 'details' param might be passed as string 'true'/'false' from some callers, 
            # but usually params are json decoded dicts.
            details = params.get('details') == 'true' or params.get('details') is True
            return self.get_all_tags(details=details)
        elif action == 'get_items':
            return self.get_tag_items(params.get('tag_name'))
        elif action == 'get_tags_for_item':
            return self.get_tags_for_item(params.get('media_type'), params.get('tmdb_id'))
        elif action == 'get_tags_for_item':
            return self.get_tags_for_item(params.get('media_type'), params.get('tmdb_id'))
        # Add other actions as needed
        return {'success': False, 'error': f'Unknown tag action: {action}'}

    def get_movie_recommendations(self, params):
        """Fetches movie recommendations from Orac."""
        return self._get_json("recommendations/movies", params=params)

    def get_reviews(self, params):
        """Fetches TMDB reviews for a movie or TV show via Orac."""
        return self._get_json("reviews", params=params)

    def mark_undesirable(self, params):
        """Marks a stream as undesirable via Orac."""
        return self._get_json("mark_undesirable", params=params, put=True)


class OracClientError(Exception):
    """Custom exception for Orac client errors."""
    pass        


def _get_data_via_ipc(mode, params=None, json_body=None, timeout=60):
    """
    Sends an IPC request to the Liberator service using a concurrent-safe queue.
    """
    window = xbmcgui.Window(10000)
    request_id = str(uuid.uuid4())
    request_prop_key = f"{REQUEST_PROP}_{request_id}"
    notification_prop = "REQUEST_NOTIFICATION_PROP"
    lock_prop = "IPC_LOCK_PROP"

    request_payload = {
        "uuid": request_id,
        "mode": mode,
        "params": params,
        "json_body": json_body
    }

    # 1. Write the full request payload to a unique property
    window.setProperty(request_prop_key, json.dumps(request_payload))
    logger("get_data", f"Requesting IPC data for mode: {mode} with ID: {request_id}")

    # 2. Acquire a lock to safely append to the notification queue
    start_time_lock = time.time()
    try:
        while time.time() - start_time_lock < 5:
            lock_status = window.getProperty(lock_prop)
            if not lock_status:
                window.setProperty(lock_prop, 'locked')
                break
            time.sleep(0.01)
        else:
            logger("Router", "Failed to acquire IPC lock. Aborting request and cleaning up.")
            window.clearProperty(request_prop_key)
            return None

        # 3. Read the queue, append the request key, and write it back
        queue_str = window.getProperty(notification_prop)
        queue = json.loads(queue_str) if queue_str else []
        queue.append(request_prop_key)
        window.setProperty(notification_prop, json.dumps(queue))
    finally:
        # Always release the lock, even if an error occurred
        window.clearProperty(lock_prop)
    
    # Don't get a response from a put
    if mode.startswith('mark_episode_watched'):
        return {'status': 'ok'}
    
    # Don't get a response from a put
    if mode.startswith('mark_movie_watched'):
        return {'status': 'ok'}
    
    # Don't get a response from a put
    if mode.startswith('mark_tvshow_watched'):
        return {'status': 'ok'}
    
    # Don't get a response from a put
    if mode.startswith('mark_season_watched'):
        return {'status': 'ok'}
        
    if mode.startswith('mark_undesirable'):
        return {'status': 'ok'}
        
    # Don't get a response from a put
    if mode.startswith('drop_tvshow'):
        return {'status': 'ok'}


    # 4. Poll the database for the response
    # This section is simplified as we now only poll the database.
    logger("get_data", f"Polling database for response for ID: {request_id}")
    start_time_db = time.time()
    dbcon = None
    cache_data = None
    while time.time() - start_time_db < timeout:
        try:
            # We poll the database using the unique ID
            dbcon = connect_database('ipc_data_db')
            cursor = dbcon.cursor()
            
            cursor.execute("SELECT data_json FROM requests WHERE uuid = ?", (request_id,))
            cache_data = cursor.fetchone()

            if cache_data:
                # Delete the data after reading it
                cursor.execute("DELETE FROM requests WHERE uuid = ?", (request_id,))
                dbcon.commit()
                break # Exit the loop after success
            
        except sqlite3.OperationalError:
            logger("Router", "Database is locked, retrying...")
            time.sleep(0.01)
            
        finally:
            close_database(dbcon)
        
        time.sleep(0.5) # Poll the database every 500ms

    if cache_data:
        response_json = cache_data[0]
        return json.loads(response_json)
    
    logger("Router", f"Timeout waiting for response for ID: {request_id}")
    return None


def orac_add_to_list(params):
    """Adds an item to a list via Orac IPC call."""
    ipc_params = {
        'list_name': params.get('list_name'),
        'user': params.get('user'),
        'slug': params.get('slug'),
        'tmdb_id': params.get('tmdb_id')
    }
    return _get_data_via_ipc('add_to_list', params=ipc_params)
