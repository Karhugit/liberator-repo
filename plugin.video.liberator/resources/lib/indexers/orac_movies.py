# -*- coding: utf-8 -*-
import sys
from modules import meta_lists
from modules import kodi_utils, settings
from modules.utils import manual_function_import, get_datetime, get_current_timestamp, paginate_list, jsondate_to_datetime
from modules.orac_infotagger import KodiListItemBuilder, build_content_batch
from modules.watched_status import get_database, watched_info_movie, get_watched_status_movie
logger = kodi_utils.logger
from modules.thread_manager import make_thread_list_enumerate, make_thread_list_multi_arg

make_listitem, build_url, nextpage_landscape = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.nextpage_landscape
string, external, add_items, add_dir, get_property = str, kodi_utils.external, kodi_utils.add_items, kodi_utils.add_dir, kodi_utils.get_property
set_content, end_directory, set_view_mode, folder_path = kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode, kodi_utils.folder_path
poster_empty, fanart_empty, set_property = kodi_utils.empty_poster, kodi_utils.addon_fanart(), kodi_utils.set_property
sleep, xbmc_actor, set_category = kodi_utils.sleep, kodi_utils.xbmc_actor, kodi_utils.set_category
add_item, home = kodi_utils.add_item, kodi_utils.home
watched_indicators, widget_hide_next_page = settings.watched_indicators, settings.widget_hide_next_page
widget_hide_watched, media_open_action, page_limit, paginate = settings.widget_hide_watched, settings.media_open_action, settings.page_limit, settings.paginate
tmdb_api_key, mpaa_region = settings.tmdb_api_key, settings.mpaa_region
personal = {'favorites_movies': ('modules.favorites', 'get_favorites'),
'watched_movies': ('modules.watched_status', 'get_watched_items'), 'recent_watched_movies': ('modules.watched_status', 'get_recently_watched')}
view_mode, content_type = 'view.movies', 'movies'
run_plugin, container_update = 'RunPlugin(%s)', 'Container.Update(%s)'

# A class is used here, called via Movies(params).worker() it starts an instance of the class with the params passed to it, and discards the instance after use. Init sets up the parameters and variables needed for the class methods.
class orac_movies:
    def __init__(self, params):
        self.params = params
        self.params_get = self.params.get
        self.category_name = self.params_get('category_name', None) or self.params_get('name', None) or 'Movies'
        self.id_type, self.list, self.action = self.params_get('id_type', 'tmdb_id'), self.params_get('list', []), self.params_get('action', None)
        self.items, self.new_page, self.total_pages, self.is_external, self.is_home = [], {}, None, external(), home()
        self.widget_hide_next_page = self.is_home and widget_hide_next_page()
        self.widget_hide_watched = self.is_home and widget_hide_watched()
        self.custom_order = self.params_get('custom_order', 'false') == 'true'
        self.paginate_start = int(self.params_get('paginate_start', '0'))
        self.append = self.items.append
        self.movieset_list_active = False

    def worker(self, return_tuples=False):
            
        try:
            # Initialize basic settings
            self.current_date, self.current_time = get_datetime(), get_current_timestamp()
            self.tmdb_api_key, self.mpaa_region = tmdb_api_key(), mpaa_region()
            self.watched_indicators = watched_indicators()
            self.watched_title = 'Orac'
            self.window_command = 'ActivateWindow(Videos,%s,return)' if self.is_external else 'Container.Update(%s)'
                
            # Open action settings
            open_action = media_open_action('movie')
            self.open_movieset = open_action in (2, 3) and not self.movieset_list_active
            self.open_extras = open_action in (1, 3)
                
            # Initialize infotagger system (required for batch processing)
            try:
                import modules.orac_infotagger as orac_infotagger
                    
                # Set required globals in infotagger module
                orac_infotagger.build_url = build_url
                orac_infotagger.make_listitem = make_listitem
                orac_infotagger.logger = logger
                orac_infotagger.run_plugin = run_plugin
                orac_infotagger.container_update = container_update
                orac_infotagger.string = string
                orac_infotagger.poster_empty = poster_empty
                orac_infotagger.fanart_empty = fanart_empty
                    
                builder = KodiListItemBuilder(poster_empty, fanart_empty)
                logger("Liberator", "InfoTagger batch system initialized")
                    
            except Exception as e:
                logger("Liberator", f"Failed to initialize infotagger for batch processing: {str(e)}")
                raise Exception("Batch processing requires infotagger system")
                
            # Set up batch processing parameters
            base_extra_params = {
                'open_movieset': self.open_movieset,
                'open_extras': self.open_extras,
                'is_external': self.is_external,
                'movieset_list_active': self.movieset_list_active,
                'widget_hide_watched': getattr(self, 'widget_hide_watched', False),
                'watched_title': self.watched_title,
                'window_command': self.window_command,
                'current_date': self.current_date
            }
                
            # Perform batch processing
            results = build_content_batch(builder, self.list, 'movie', base_extra_params)
                
            # Handle custom order vs sorted order
            if not self.custom_order:
                # For sorted order, sort by position
                results.sort(key=lambda k: k[1])
            
            if return_tuples:
                self.items = results
            else:
                self.items = [result[0] for result in results]
                
                
        except Exception as e:
            import traceback
            logger("Liberator", f"Batch processing failed: {str(e)}")
            logger("Liberator", f"Traceback: {traceback.format_exc()}")
            self.items = []
            logger("Liberator", "Batch processing failed - returning empty list")
            
        return self.items
