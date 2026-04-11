# -*- coding: utf-8 -*-
import sys
from modules import kodi_utils, settings
from modules.utils import jsondate_to_datetime
from apis.orac_api import _get_data_via_ipc
from caches.settings_cache import get_setting
from modules.orac_infotagger import KodiListItemBuilder, build_content_batch
import xbmcgui, xbmcplugin, xbmcaddon

set_view_mode, external, home = kodi_utils.set_view_mode, kodi_utils.external, kodi_utils.home
add_items, set_content, end_directory, set_category = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_category
ep_display_format = settings.single_ep_display_format
watched_indicators_info = settings.watched_indicators
poster_empty, fanart_empty = kodi_utils.empty_poster, kodi_utils.addon_fanart()
content_type = 'episodes'
single_view = 'view.episodes_single'
ADDON = xbmcaddon.Addon('plugin.video.liberator')

def build_episodes_list(params={}):
    handle, is_external, is_home, category_name = int(sys.argv[1]), external(), home(), 'Episodes'
    episodes_data = []

    try:
        if params.get('next_episode'):
            # ipc_params = {'user': get_setting('trakt.user', '')}
            # episodes_data = _get_data_via_ipc('get_next_episodes', params=ipc_params)
            # Remove user param to avoid case sensitivity issues on server
            episodes_data = _get_data_via_ipc('get_next_episodes')
            
            category_name = 'Next Episodes'
            if not episodes_data:
                end_directory(handle, cacheToDisc=False)
                return
        elif params.get('episode_list'):
            tmdb_id = params.get('tmdb_id')
            ipc_params = {'tmdb_id': tmdb_id, 'user': get_setting('trakt.user', '')}
            show_data = _get_data_via_ipc('get_show_details',params=ipc_params)
            if not show_data:
                end_directory(handle, cacheToDisc=False)
                return
            
            category_name = show_data.get('title', 'Episode List')
            show_info = {
                'show_title': show_data.get('title'),
                'show_overview': show_data.get('overview'),
                'show_poster_path': show_data.get('poster_path'),
                'show_fanart_path': show_data.get('fanart_path'),
                'show_clearlogo_path': show_data.get('clearlogo_path'),
                'show_landscape_path': show_data.get('landscape_path'),
                'show_imdb_id': show_data.get('imdb_id'),
                'show_tvdb_id': show_data.get('tvdb_id'),
                'show_trakt_id': show_data.get('trakt_id'),
                'show_tmdb_id': show_data.get('show_tmdb_id')
            }
            requested_season_str = params.get('season')
            all_seasons = show_data.get('seasons', [])

            if requested_season_str and requested_season_str != 'all':
                try:
                    requested_season_num = int(requested_season_str)
                    seasons_to_process = [s for s in all_seasons if s.get('season') == requested_season_num]
                except (ValueError, TypeError):
                    seasons_to_process = []
            else:
                seasons_to_process = all_seasons

            for season_data in seasons_to_process:
                for episode in season_data.get('episodes', []):
                    episode_with_show_info = {**episode, **show_info}
                    episodes_data.append(episode_with_show_info)

        # Use orac_episodes class for workers
        item_list = orac_episodes({'list': list(enumerate(episodes_data)), 'custom_order': 'true'}).worker()
        
        add_items(handle, item_list)
        set_content(handle, content_type)
        set_category(handle, category_name)
        end_directory(handle, cacheToDisc=False)
        set_view_mode(single_view, content_type, is_external)

    except Exception as e:
        import traceback
        from modules.kodi_utils import logger
        logger("Liberator", f"build_episodes_list: An unexpected error occurred: {e}")
        logger("Liberator", f"build_episodes_list: Traceback: {traceback.format_exc()}")
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Error loading episodes: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(handle, succeeded=False)

class orac_episodes:
    def __init__(self, params):
        self.params = params
        self.params_get = self.params.get
        self.list = self.params_get('list', [])
        self.custom_order = self.params_get('custom_order', 'false') == 'true'
        self.is_external = external()
        self.is_home = home()

    def worker(self):
        try:
            display_format = ep_display_format(self.is_external)
            window_command = 'ActivateWindow(Videos,%s,return)' if self.is_external else 'Container.Update(%s)'
            watched_title = 'Orac'

            # Pre-process data for infotagger compatibility
            processed_list = []
            for count, item in self.list:
                # Capture show title before overwriting 'title' with episode title
                item['tvshowtitle'] = item.get('title', item.get('show_title', ''))
                
                item['title'] = item.get('episode_title', '')
                item['overview'] = item.get('episode_overview', item.get('show_overview', ''))
                item['rating'] = item.get('episode_rating', 0.0)
                item['premiered'] = item.get('air_date', '')
                item['studio'] = item.get('network', '')
                processed_list.append((count, item))

            builder = KodiListItemBuilder(poster_empty, fanart_empty)
            
            extra_params = {
                'is_external': self.is_external,
                'watched_title': watched_title,
                'display_format': display_format,
                'window_command': window_command,
                'widget_hide_watched': False,
                'is_folder': False
            }
            
            results = build_content_batch(builder, processed_list, 'episode', extra_params)
            
            if not self.custom_order:
                results.sort(key=lambda k: k[1])
            
            return [i[0] for i in results]

        except Exception as e:
            import traceback
            from modules.kodi_utils import logger
            logger("Liberator", f"orac_episodes worker error: {e}")
            logger("Liberator", f"Traceback: {traceback.format_exc()}")
            return []
