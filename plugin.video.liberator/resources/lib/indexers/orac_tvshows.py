# -*- coding: utf-8 -*-
import sys
from modules import meta_lists
from modules import kodi_utils, settings
from modules.utils import manual_function_import, get_datetime, get_current_timestamp, paginate_list
from modules.watched_status import get_database, watched_info_tvshow, get_watched_status_tvshow
from modules.thread_manager import make_thread_list_enumerate, make_thread_list_multi_arg
logger = kodi_utils.logger
from modules.orac_infotagger import KodiListItemBuilder, build_content_batch

string, external, add_items, add_dir = str, kodi_utils.external, kodi_utils.add_items, kodi_utils.add_dir
sleep, add_item, xbmc_actor, home, tmdb_api_key = kodi_utils.sleep, kodi_utils.add_item, kodi_utils.xbmc_actor, kodi_utils.home, settings.tmdb_api_key
set_category, make_listitem, build_url, set_property = kodi_utils.set_category, kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.set_property
set_content, end_directory, set_view_mode, folder_path = kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode, kodi_utils.folder_path
poster_empty, fanart_empty, nextpage_landscape = kodi_utils.empty_poster, kodi_utils.addon_fanart(), kodi_utils.nextpage_landscape
media_open_action, default_all_episodes, page_limit, paginate = settings.media_open_action, settings.default_all_episodes, settings.page_limit, settings.paginate
widget_hide_next_page, widget_hide_watched, watched_indicators = settings.widget_hide_next_page, settings.widget_hide_watched, settings.watched_indicators
mpaa_region = settings.mpaa_region
run_plugin, container_update = 'RunPlugin(%s)', 'Container.Update(%s)'
special = ('tmdb_tv_languages', 'tmdb_tv_networks', 'tmdb_tv_providers', 'tmdb_tv_year', 'tmdb_tv_decade', 'tmdb_tv_recommendations', 'tmdb_tv_genres',
'tmdb_tv_search', 'tmdb_tv_keyword_results', 'tmdb_tv_keyword_results_direct', 'tmdb_anime_year', 'tmdb_anime_decade', 'tmdb_anime_genres',
'tmdb_anime_providers')
personal = {'favorites_tvshows': ('modules.favorites', 'get_favorites'),
'favorites_anime_tvshows': ('modules.favorites', 'get_favorites'), 'watched_tvshows': ('modules.watched_status', 'get_watched_items')}
view_mode, content_type = 'view.tvshows', 'tvshows'

class orac_tvshows:
    def __init__(self, params):
        self.params = params
        self.params_get = self.params.get
        self.category_name = self.params_get('category_name', None) or self.params_get('name', None) or 'TV Shows'
        self.id_type, self.list, self.action = self.params_get('id_type', 'tmdb_id'), self.params_get('list', []), self.params_get('action', None)
        self.items, self.new_page, self.total_pages, self.is_external, self.is_home = [], {}, None, external(), home()
        self.widget_hide_next_page = self.is_home and widget_hide_next_page()
        self.custom_order = self.params_get('custom_order', 'false') == 'true'
        self.paginate_start = int(self.params_get('paginate_start', '0'))
        self.append = self.items.append
        try: 
            self.is_anime = '_anime_' in self.action
        except: 
            self.is_anime = False
    
    def worker(self, short=False, return_tuples=False):
        """Worker that uses batch processing with pre-fetched metadata."""
        logger("Liberator", "TV shows worker started")
        logger("Liberator", f"Processing {len(self.list)} items")
        
        try:
            # Initialize basic settings
            self.all_episodes, self.open_extras = default_all_episodes(), media_open_action('tvshow') == 1
            self.watched_indicators = watched_indicators()
            self.watched_title = 'Orac'
            self.window_command = 'ActivateWindow(Videos,%s,return)' if self.is_external else 'Container.Update(%s)'
            
            builder = KodiListItemBuilder(poster_empty, fanart_empty)
            
            # The self.list already contains (position, metadata) tuples from orac_lists.py
            metadata_list = self.list
            
            # Set up batch processing parameters
            base_extra_params = {
                'all_episodes': self.all_episodes,
                'open_extras': self.open_extras,
                'is_external': self.is_external,
                'is_anime': self.is_anime,
                'widget_hide_watched': self.is_home and widget_hide_watched(),
                'watched_title': self.watched_title,
                'window_command': self.window_command
            }
            
            # Perform batch processing
            if short:
                results = build_content_batch(builder, metadata_list, 'tvshow_short', base_extra_params)
            else:
                results = build_content_batch(builder, metadata_list, 'tvshow', base_extra_params)
            
            # Handle custom order vs sorted order
            if not self.custom_order:
                results.sort(key=lambda k: k[1])
            
            if return_tuples:
                self.items = results
            else:
                self.items = [result[0] for result in results]
            
            logger("Liberator", f"TV shows worker completed successfully with {len(self.items)} items")
            
        except Exception as e:
            import traceback
            logger("Liberator", f"TV shows worker failed: {str(e)}")
            logger("Liberator", f"Traceback: {traceback.format_exc()}")
            self.items = []
        
        return self.items
