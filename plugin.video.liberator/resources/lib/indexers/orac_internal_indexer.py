# -*- coding: utf-8 -*-
"""
Internal Indexer for Liberator - handles listing, creating, and displaying internal indexes.
These are filtered views of the local library (e.g., movies synced to Orac) based on genre.
"""
import json
import sys
from modules import kodi_utils
from apis.orac_api import _get_data_via_ipc

logger = kodi_utils.logger
add_items, set_content, end_directory, set_category, set_view_mode = (
    kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory,
    kodi_utils.set_category, kodi_utils.set_view_mode
)
make_listitem, build_url, get_icon = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.get_icon
container_refresh = kodi_utils.container_refresh
external, home = kodi_utils.external, kodi_utils.home


def build_internal_indexes_list(params):
    """
    Displays a list of internal indexes with a "Create New Index" option.
    """
    handle = int(sys.argv[1])
    item_type = params.get('item_type', 'movie')
    
    items = []
    
    # Add "Create New Index" option
    create_listitem = make_listitem()
    create_listitem.setLabel('[B]+ Create New Index[/B]')
    create_listitem.setArt({'icon': get_icon('add'), 'poster': get_icon('add')})
    create_url = build_url({'mode': 'orac.internal_index.create', 'item_type': item_type})
    items.append((create_url, create_listitem, True))
    
    # Fetch existing internal indexes from Orac
    result = _get_data_via_ipc('get_internal_indexes', params={'item_type': item_type})
    
    if result and result.get('success'):
        indexes = result.get('indexes', [])
        for index in indexes:
            listitem = make_listitem()
            index_name = index.get('id', 'Unnamed Index')
            listitem.setLabel(index_name)
            listitem.setArt({'icon': get_icon('lists'), 'poster': get_icon('lists')})
            
            # Context menu for edit/delete
            cm = []
            edit_url = build_url({
                'mode': 'orac.internal_index.edit',
                'index_id': index_name,
                'item_type': item_type,
                'parameters': json.dumps(index.get('parameters', {}))
            })
            delete_url = build_url({
                'mode': 'orac.internal_index.delete',
                'index_id': index_name,
                'item_type': item_type
            })
            cm.append(('[B]Edit Index[/B]', 'RunPlugin(%s)' % edit_url))
            cm.append(('[B]Delete Index[/B]', 'RunPlugin(%s)' % delete_url))
            listitem.addContextMenuItems(cm)
            
            # URL to display index contents
            params_dict = index.get('parameters', {})
            is_random = params_dict.get('sort_by') == 'random' or params_dict.get('sort_by_tv') == 'random'
            view_url = build_url({
                'mode': 'orac.internal_index.view',
                'index_id': index_name,
                'item_type': item_type,
                'is_random': 'true' if is_random else 'false'
            })
            items.append((view_url, listitem, True))
    
    add_items(handle, items)
    set_content(handle, 'files')
    set_category(handle, 'Indexes')
    end_directory(handle)
    set_view_mode('view.main')


def view_internal_index_contents(params):
    """
    Displays the contents of an internal index (filtered movies based on genre).
    """
    handle = int(sys.argv[1])
    is_external, is_home = external(), home()
    
    index_id = params.get('index_id')
    item_type = params.get('item_type', 'movie')
    is_random = params.get('is_random') == 'true'
    
    if not index_id:
        logger("orac_internal_indexer", "No index_id provided for view.")
        end_directory(handle)
        return
    
    # Fetch filtered content from Orac
    result = _get_data_via_ipc('internal_index_contents', params={'index_id': index_id, 'item_type': item_type})
    
    if not result or not result.get('success'):
        logger("orac_internal_indexer", f"Failed to fetch contents for index: {index_id}")
        end_directory(handle)
        return
    
    movies_data = result.get('results', [])
    
    if not movies_data:
        logger("orac_internal_indexer", f"No items found for index: {index_id}")
        end_directory(handle)
        return
    
    # Use orac_movies/orac_episodes to display the results
    if item_type == 'movie':
        from indexers.orac_movies import orac_movies
        movie_list = {'list': list(enumerate(movies_data)), 'id_type': 'trakt_dict', 'custom_order': 'true'}
        list_items = orac_movies(movie_list).worker()
    elif item_type == 'tvshow':
        from indexers.orac_tvshows import orac_tvshows
        show_list = {'list': list(enumerate(movies_data)), 'id_type': 'trakt_dict', 'custom_order': 'true'}
        list_items = orac_tvshows(show_list).worker()
    elif item_type == 'episode':
        from indexers.orac_episodes import orac_episodes
        episode_list = {'list': list(enumerate(movies_data)), 'custom_order': 'true'}
        list_items = orac_episodes(episode_list).worker()
    else:
        # Fallback or generic handling
        end_directory(handle)
        return
    
    add_items(handle, list_items)
    set_content(handle, 'tvshows' if item_type == 'tvshow' else ('movies' if item_type == 'movie' else 'episodes'))
    set_category(handle, index_id)
    cache_to_disc = False if (is_external or is_random) else True
    end_directory(handle, cacheToDisc=cache_to_disc)
    if not is_external:
        set_view_mode('view.movies', 'movies', is_external)


def delete_internal_index(params):
    """
    Deletes an internal index.
    """
    index_id = params.get('index_id')
    item_type = params.get('item_type', 'movie')
    
    if not index_id:
        logger("orac_internal_indexer", "No index_id provided for delete.")
        return
    
    result = _get_data_via_ipc('del_internal_index', params={'index_id': index_id, 'item_type': item_type})
    
    if result and result.get('status') == 'success':
        logger("orac_internal_indexer", f"Successfully deleted internal index: {index_id}")
        kodi_utils.notification(f'Index "{index_id}" deleted.')
    else:
        logger("orac_internal_indexer", f"Failed to delete internal index: {index_id}")
        kodi_utils.notification('Failed to delete index.')
    
    container_refresh()
