# -*- coding: utf-8 -*-
import sys
import json
from modules import kodi_utils
from apis.orac_api import _get_data_via_ipc
from indexers.orac_movies import orac_movies

logger = kodi_utils.logger
add_items, set_content, end_directory, set_category, set_view_mode = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_category, kodi_utils.set_view_mode
notification, external, build_url = kodi_utils.notification, kodi_utils.external, kodi_utils.build_url
set_property, get_property, clear_property = kodi_utils.set_property, kodi_utils.get_property, kodi_utils.clear_property
make_listitem, add_dir = kodi_utils.make_listitem, kodi_utils.add_dir

class OracRecommendations:
    def __init__(self, params):
        self.params = params
        self.handle = int(sys.argv[1])
        self.is_external = external()
        self.prop_key = 'orac.recommendations.cache'

    def build_main_menu(self):
        """Fetches data from server and displays 'Top Picks' and Genre Shelves."""
        logger("Liberator", "Building Recommendations Main Menu")
        
        # Check if we have cached data in window property to avoid re-fetching on shelf navigation
        cached_data_str = get_property(self.prop_key)
        if cached_data_str:
            logger("Liberator", "Using cached recommendations data from window property")
            data = json.loads(cached_data_str)
        else:
            logger("Liberator", "Fetching recommendations from server")
            data = _get_data_via_ipc('recommendations_movies', {})
            if data:
                # Cache it
                set_property(self.prop_key, json.dumps(data))
            else:
                notification('No Recommendations Found', 2500)
                end_directory(self.handle)
                return

        # Add "Top Picks" folder
        self._add_folder("Top Picks", 'top_picks')

        # Add Genre Shelves folders
        genres = data.get('genre_shelves', [])
        for i, shelf in enumerate(genres):
            title = shelf.get('title', f"Genre {i+1}")
            self._add_folder(title, 'genre_shelf', index=i)

        set_category(self.handle, "Recommendations")
        end_directory(self.handle)

    def _add_folder(self, name, action, index=None):
        url_params = {
            'mode': 'orac.recommendations.shelf',
            'action': action,
            'name': name
        }
        if index is not None:
            url_params['index'] = index
            
        add_dir(url_params, name, self.handle, isFolder=True)

    def display_shelf(self):
        """Displays the items for a specific shelf (Top Picks or Genre)."""
        action = self.params.get('action')
        index = int(self.params.get('index', -1))
        name = self.params.get('name', 'Recommendations')
        
        cached_data_str = get_property(self.prop_key)
        if not cached_data_str:
            logger("Liberator", "Cache expired, re-fetching recommendations from server")
            data = _get_data_via_ipc('recommendations_movies', {})
            if data:
                set_property(self.prop_key, json.dumps(data))
            else:
                notification("Failed to load recommendations", 3000)
                end_directory(self.handle)
                return
        else:
            data = json.loads(cached_data_str)
        
        items_to_display = []
        if action == 'top_picks':
            items_to_display = data.get('top_picks', [])
        elif action == 'genre_shelf' and index >= 0:
            try:
                items_to_display = data.get('genre_shelves', [])[index].get('items', [])
            except IndexError:
                pass
        
        if not items_to_display:
            notification("No items in this shelf", 2000)
            end_directory(self.handle)
            return

        # Use orac_movies to build list items
        # orac_movies expects {'list': [...], 'id_type': 'trakt_dict' ...}
        # The items we have are TMDB movie objects. 
        # orac_movies.worker usually expects (count, item_dict).
        
        # We need to adapt the data structure. Orac movies worker expects a list of (count, data) tuples? 
        # Check orac_movies.py: "for count, item in self.list:" if not dict.
        # It takes `self.list`. 
        
        # Let's format it as a list of dicts directly if orac_movies supports it, or enumerated list.
        # existing code: `item_list = {'list': list(enumerate(result)), ...}`
        
        # Prepare list for orac_movies
        # orac_infotagger expects 'tmdb_id', but API returns 'id'.
        formatted_items = []
        tmdb_image_base = 'https://image.tmdb.org/t/p/w500'
        
        for i, item in enumerate(items_to_display):
            # Ensure tmdb_id
            if 'id' in item and 'tmdb_id' not in item:
                item['tmdb_id'] = item['id']
            
            # Ensure full image URLs
            for key in ['poster_path', 'backdrop_path']:
                val = item.get(key)
                if val and isinstance(val, str) and val.startswith('/'):
                    item[key] = f"{tmdb_image_base}{val}"
            
            # Ensure year
            if 'release_date' in item and 'year' not in item:
                item['year'] = item['release_date'][:4] if item['release_date'] else '2050'

            formatted_items.append((i, item))
            
        formated_list = formatted_items
        
        # We need to make sure `item_dict` has keys `orac_movies` expects.
        # Our items have Keys from TMDB directly (from server recommendations_handler).
        # orac_movies uses `orac_infotagger.build_content_batch`.
        # We might need to map keys if they differ.
        # Server returns standard TMDB movie object keys + 'final_score'.
        # orac_infotagger expects standard TMDB keys? 
        # Let's assume standard keys (id, title, poster_path, etc.) work.
        
        list_items = orac_movies({'list': formated_list, 'id_type': 'tmdb_id'}).worker()
        
        add_items(self.handle, list_items)
        set_content(self.handle, 'movies')
        set_category(self.handle, name)
        end_directory(self.handle)
        set_view_mode('view.movies', 'movies', self.is_external)

def build_recommendations(params):
    OracRecommendations(params).build_main_menu()

def display_shelf(params):
    OracRecommendations(params).display_shelf()
