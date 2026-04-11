# -*- coding: utf-8 -*-
import json
import sys
from modules import kodi_utils
from apis.orac_api import _get_data_via_ipc
from indexers.orac_tvshows import orac_tvshows
from indexers.orac_movies import orac_movies

logger = kodi_utils.logger
add_items, set_content, end_directory, set_category, set_view_mode = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_category, kodi_utils.set_view_mode
external, home = kodi_utils.external, kodi_utils.home

def tmdb_tv_discover(params):
    """
    Fetches TV show discovery results from the Orac service based on a filter name.
    """
    handle = int(sys.argv[1])
    is_external, is_home = external(), home()
    
    filter_name = params.get('name')
    if not filter_name:
        logger("orac_external_indexer", "No filter name found in params.")
        end_directory(handle)
        return

#    try:
#        filter_payload = json.loads(filter_name)
#    except json.JSONDecodeError:
#        logger("orac_external_indexer", "Failed to decode JSON from filter payload.")
#        end_directory(handle)
#        return

    ipc_mode = 'discover_tvshow'
    ipc_params = {'name': filter_name}

    logger("orac_external_indexer", f"Making IPC call with mode: {ipc_mode} and params: {ipc_params}")
    result = _get_data_via_ipc(ipc_mode, params=ipc_params)

    if not result:
        logger("orac_external_indexer", "No results received from Orac service for TV shows.")
        end_directory(handle)
        return
    
    tvshow_list = {'list': list(enumerate(result)), 'id_type': 'trakt_dict', 'custom_order': 'true'}
    list_items = orac_tvshows(tvshow_list).worker()

    add_items(handle, list_items)
    set_content(handle, 'tvshows')
    set_category(handle, params.get('name', 'Discover Results'))
    end_directory(handle, cacheToDisc=False if is_external else True)
    if not is_external:
        set_view_mode('view.tvshows', 'tvshows', is_external)

def tmdb_movies_discover(params):
    """
    Fetches movie discovery results from the Orac service based on a filter name.
    """
    handle = int(sys.argv[1])
    is_external, is_home = external(), home()
    
    filter_name = params.get('name')
    if not filter_name:
        logger("orac_external_indexer", "No filter name found in params.")
        end_directory(handle)
        return

    ipc_mode = 'discover_movie'
    ipc_params = {'name': filter_name}

    logger("orac_external_indexer", f"Making IPC call with mode: {ipc_mode} and params: {ipc_params}")
    result = _get_data_via_ipc(ipc_mode, params=ipc_params)

    if not result:
        logger("orac_external_indexer", "No results received from Orac service for movies.")
        end_directory(handle)
        return
    
    movie_list = {'list': list(enumerate(result)), 'id_type': 'trakt_dict', 'custom_order': 'true'}
    list_items = orac_movies(movie_list).worker()

    add_items(handle, list_items)
    set_content(handle, 'movies')
    set_category(handle, params.get('name', 'Discover Results'))
    end_directory(handle, cacheToDisc=False if is_external else True)
    if not is_external:
        set_view_mode('view.movies', 'movies', is_external)

def get_external_indexes(media_type=''):
    """
    Returns a list of external indexes from orac.
    """
    ipc_mode = 'get_external_indexes'
    ipc_params = {'item_type': media_type}
    result = _get_data_via_ipc(ipc_mode, params=ipc_params)
    if result:
        return result
    else:
        logger("orac_external_indexer", "No external indexes found.")
        return []

def remove_external_index(index_id, media_type):
    """
    Removes an external index from orac.
    """
    ipc_mode = 'del_ext_index'
    ipc_params = {'index_id': index_id, 'item_type': media_type}
    result = _get_data_via_ipc(ipc_mode, params=ipc_params)
    if result and result.get('status') == 'success':
        logger("orac_external_indexer", f"Successfully removed external index with ID: {index_id}")
        return True
    else:
        logger("orac_external_indexer", f"Failed to remove external index with ID: {index_id}")
        return False    

