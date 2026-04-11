# -*- coding: utf-8 -*-
import sys
from modules import kodi_utils, settings
from modules.utils import get_datetime
logger = kodi_utils.logger
from apis.orac_api import _get_data_via_ipc
from modules.orac_infotagger import KodiListItemBuilder, build_content_batch

poster_empty, fanart_empty, set_category, home = kodi_utils.empty_poster, kodi_utils.addon_fanart(), kodi_utils.set_category, kodi_utils.home
add_items, set_content, end_directory, set_view_mode = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_view_mode
build_url, external = kodi_utils.build_url, kodi_utils.external
watched_indicators_info, widget_hide_watched, show_specials = settings.watched_indicators, settings.widget_hide_watched, settings.show_specials
view_mode, content_type = 'view.seasons', 'seasons'

def build_season_list(params):
    handle, is_external, is_home = int(sys.argv[1]), external(), home()
# Fetch metadata from orac for the seasons
    tmdb_id = params.get('tmdb_id', None)
    if not tmdb_id:
        logger('build_season_list', 'No TMDB ID provided.')
        end_directory(handle, cacheToDisc=False)
        return

    ipc_params = {'tmdb_id': tmdb_id, 'user': settings.get_setting('trakt.user', '')}
    show_data = _get_data_via_ipc('get_show_details',params=ipc_params)
    if not show_data:
        logger('build_season_list', f'Failed to get show data for tmdb_id: {tmdb_id}')
        end_directory(handle, cacheToDisc=False)
        return

    # Prepare data for batch processing
    season_data = show_data.get('seasons', [])
    
    # Filter and sort seasons
    if show_specials():
        season_data.sort(key=lambda i: (i.get('season', 1) == 0, i.get('season', 1)))
    else:
        season_data = [i for i in season_data if i.get('season', 1) != 0]
        season_data.sort(key=lambda k: k.get('season', 1))

    # The infotagger expects a list of (position, meta) tuples
    metadata_list = list(enumerate(season_data))

    # Prepare extra_params for the builder
    current_date = get_datetime()
    extra_params = {
        'show_tmdb_id': tmdb_id,
        'show_title': show_data.get('title', ''),
        'show_poster': show_data.get('poster_path') or poster_empty,
        'show_fanart': show_data.get('fanart_path') or fanart_empty,
        'show_clearlogo': show_data.get('clearlogo_path', ''),
        'show_landscape': show_data.get('landscape_path', ''),
        'total_seasons': show_data.get('total_seasons', len(season_data)),
        'is_external': is_external,
        'is_anime': 'anime' in [genre.lower() for genre in show_data.get('genres', [])],
        'widget_hide_watched': is_home and widget_hide_watched(),
        'watched_title': 'Orac',
        'current_date_str': current_date.strftime('%Y-%m-%d')
    }

    # Initialize and run the batch builder
    builder = KodiListItemBuilder(poster_empty, fanart_empty)
    results = build_content_batch(builder, metadata_list, 'season', extra_params)

    if not results:
        logger('build_season_list', f'Batch builder returned no items for {tmdb_id}')
        end_directory(handle, cacheToDisc=False)
        return

    # Sort by position (which is the original season order) and get the listitems
    results.sort(key=lambda k: k[1])
    list_items = [item[0] for item in results]

    add_items(handle, list_items)
    category_name = show_data.get('title', 'Seasons')
    set_content(handle, content_type)
    set_category(handle, category_name)
    end_directory(handle, cacheToDisc=False if is_external else True)
    set_view_mode(view_mode, content_type, is_external)
