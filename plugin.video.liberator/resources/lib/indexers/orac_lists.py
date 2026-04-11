import sys
import json
import random
from threading import Thread
from apis import trakt_api
from apis import orac_api
from indexers.orac_movies import orac_movies
from indexers.orac_tvshows import orac_tvshows
from indexers.seasons import single_seasons
from indexers.episodes import build_single_episode
from modules import kodi_utils
from modules.utils import paginate_list
from modules.settings import paginate, page_limit
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmc
from caches.settings_cache import get_setting, set_setting
from urllib.parse import quote_plus
import requests
from caches.base_cache import get_ipc_db_path, connect_database, close_database
from apis.orac_api import _get_data_via_ipc



add_dir, external, sleep, get_icon = kodi_utils.add_dir, kodi_utils.external, kodi_utils.sleep, kodi_utils.get_icon
trakt_icon, fanart, add_item, set_property = get_icon('trakt'), kodi_utils.get_addon_fanart(), kodi_utils.add_item, kodi_utils.set_property
set_content, set_sort_method, set_view_mode, end_directory = kodi_utils.set_content, kodi_utils.set_sort_method, kodi_utils.set_view_mode, kodi_utils.end_directory
make_listitem, build_url, add_items, select_dialog = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.add_items, kodi_utils.select_dialog
nextpage_landscape, get_property, clear_property, focus_index = kodi_utils.nextpage_landscape, kodi_utils.get_property, kodi_utils.clear_property, kodi_utils.focus_index
set_category, home, folder_path = kodi_utils.set_category, kodi_utils.home, kodi_utils.folder_path
logger = kodi_utils.logger

from apis.orac_api import OracClientError

ADDON_ID = 'plugin.video.liberator'
ADDON = xbmcaddon.Addon(ADDON_ID)

# This method shows the three main categories for organizing lists
def orac_lists_manager_categories(params, addon_handle):
    logger("orac_lists_manager_categories", "Displaying list categories")
    
    try:
        # Create three category folders
        categories = [
            {
                'name': 'My Lists',
                'section': 'my_lists',
                'description': 'Personal and liked lists'
            },
            {
                'name': 'Trakt Lists',
                'section': 'trakt',
                'description': 'Trakt generic lists'
            },
            {
                'name': 'TMDB Lists',
                'section': 'tmdb',
                'description': 'TMDB generic lists'
            },
            {
                'name': 'FlixPatrol Lists',
                'section': 'flixpatrol',
                'description': 'FlixPatrol trending lists'
            }
        ]
        
        for category in categories:
            url_params = {
                'mode': 'orac.list.list_manager_filtered',
                'section': category['section'],
                'category_name': category['name']
            }
            
            url = build_url(url_params)
            listitem = make_listitem()
            listitem.setLabel(category['name'])
            listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
            info_tag = listitem.getVideoInfoTag()
            info_tag.setPlot(category['description'])
            
            add_item(addon_handle, url, listitem, False)
        
        set_content(addon_handle, 'files')
        set_category(addon_handle, 'Lists Manager')
        set_sort_method(addon_handle, 'label')
        end_directory(addon_handle)
        set_view_mode('view.main')
        
    except Exception as e:
        logger("orac_lists_manager_categories", f"Error: {e}")
        import traceback
        logger("orac_lists_manager_categories", f"Traceback: {traceback.format_exc()}")
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Error loading list categories: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


# This method gets a list of lists filtered by section, and formats them for display including item count.
# The URL attached to each item drives what happens in routing if the list is selected
def orac_lists_manager_filtered(params, addon_handle):
    logger("orac_lists_manager_filtered", f"Params={params}")
    
    # Get the section filter from params
    section = params.get('section', 'my_lists')
    category_name = params.get('category_name', 'Lists')
    
    list_type = 'my_lists'
    item_type = 'all'

    lists = [] # Initialize your list of lists/categories

    try:
        ipc_params = {'name': list_type, 'item_type': item_type}
        lists = _get_data_via_ipc('get_lists', params=ipc_params)

        if not lists:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "No lists found from Orac.", xbmcgui.NOTIFICATION_INFO)
            logger("Orac Lists", "No lists received from Orac.")
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
            return
        
        # Filter lists based on section
        if section == 'my_lists':
            # My Lists: user is not 'trakt' or 'tmdb' or 'external_index'
            lists = [item for item in lists if item.get('user') not in ['trakt', 'tmdb', 'external_index', 'flixpatrol']]
        elif section == 'trakt':
            # Trakt: user is 'trakt'
            lists = [item for item in lists if item.get('user') == 'trakt']
        elif section == 'tmdb':
            # TMDB: user is 'tmdb' or 'external_index'
            lists = [item for item in lists if item.get('user') in ['tmdb', 'external_index']]
        elif section == 'flixpatrol':
            # FlixPatrol: user is 'flixpatrol'
            lists = [item for item in lists if item.get('user') == 'flixpatrol']
        
        if not lists:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"No lists found in {category_name}.", xbmcgui.NOTIFICATION_INFO)
            logger("Orac Lists", f"No lists in section {section}")
            return

        # New UI: Open Lists Manager Window
        from windows.lists_manager import ListsManager
        window = ListsManager('lists_manager.xml', kodi_utils.addon_path(), lists=lists, category_name=category_name, item_type=item_type)
        selected_list = window.run()
        del window
        
        if selected_list:
            # Navigate to the contents of the selected list
            url_params = {
                'mode': 'orac.list.build_orac_list',
                'user': selected_list.get('user'),
                'slug': selected_list.get('slug'),
                'list_type': list_type,
                'list_name': selected_list.get('name'),
                'item_type': item_type,
                'add_to_library': 'true' if selected_list.get('add_to_library') else 'false'
            }
            url = build_url(url_params)
            # Use Container.Update to navigate within the plugin
            xbmc.executebuiltin(f'Container.Update({url})')
        
        # We don't need to endDirectory if we opened a modal and then navigated? 
        # Actually since this function was called by the plugin router, it expects a directory listing OR a redirect.
        # Since we ran a modal loop blocking, we are still in the original call.
        # If we didn't select anything (cancelled), we should probably show the categories again or go back?
        # But since we are here via a 'folder' click, we are inside "orac.list.list_manager_filtered".
        # If we don't return listitems, we should probably close, or endDirectory empty.
        # Let's just endDirectory(succeeded=False) or True?
        # xbmcplugin.endOfDirectory(addon_handle, succeeded=False) # This usually closes the spinner if active



    except Exception as e:
        logger("get_orac_lists", "An unexpected error occurred: {e}")
        import traceback
        logger("get_orac_lists", "Traceback: {traceback.format_exc()}")
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Error loading Orac list categories: {e}", xbmcaddon.NOTIFICATION_ERROR)



# This method gets a list of lists, and formats them for display including item count. The URL attached to each item drives what happens
# in routing if the list is selected
def get_orac_lists(params, addon_handle): # Added addon_handle parameter
    logger("get_orac_lists", "Params={params}")


    # These variables are used in the _process generator, ensure they are accessible
    # or passed as arguments to _process if it's moved outside
    list_type, randomize_contents, shuffle = params['list_type'], params.get('random', 'false'), params.get('shuffle', 'false') == 'true'
    item_type = params.get('item_type', 'movie') # Use .get() for safety

    lists = [] # Initialize your list of lists/categories

    try:
        ipc_params = {'name': list_type, 'item_type': item_type, 'exclude_empty': 'true'}
        lists = _get_data_via_ipc('get_lists',params=ipc_params)

        if not lists:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "No list categories found from Orac.", xbmcgui.NOTIFICATION_INFO)
            logger("Orac Lists", "No list categories received from Orac.")
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True) # Successfully displayed empty list of lists
            return

        # Group lists by source, preserving insertion order
        from collections import OrderedDict
        grouped = OrderedDict()
        for item in lists:
            source = item.get('source', 'unknown').lower()
            grouped.setdefault(source, []).append(item)

        # Per-source colour palette (AARRGGBB). Unknown sources cycle through the fallback list.
        _SOURCE_COLORS = {
            'trakt':      'FFADD8E6',  # Light Blue
            'mdblist':    'FF90EE90',  # Light Green
            'tmdb':       'FFFFFFB3',  # Light Yellow
            'simkl':      'FFCCB0FF',  # Light Purple
            'flixpatrol': 'FFFFB347',  # Light Orange
            'imdb':       'FFFFB6C1',  # Light Pink
        }
        _COLOR_CYCLE = ['FFADD8E6', 'FF90EE90', 'FFFFFFB3', 'FFCCB0FF', 'FFFFB347', 'FFFFB6C1']
        _cycle_index = [0]  # mutable so the inner function can update it

        def _source_color(src):
            if src in _SOURCE_COLORS:
                return _SOURCE_COLORS[src]
            color = _COLOR_CYCLE[_cycle_index[0] % len(_COLOR_CYCLE)]
            _cycle_index[0] += 1
            return color

        # Define _process as an inner function or ensure its required variables are in scope
        def _process_orac_list_category_items():
            for source, source_items in grouped.items():
                color = _source_color(source)
                # Pre-build items for this group so we can skip the header if nothing survives the filter
                group_tuples = []
                for item in source_items:
                    try:
                        cm = []
                        cm_append = cm.append

                        list_name = item.get('name')
                        user = item.get('user')
                        owner = item.get('owner', user)
                        slug = item.get('slug')
                        item_count = item.get('item_count')
                        add_to_library = item.get('add_to_library', False)

                        if not list_name: continue

                        # CLIENT-SIDE FILTER: Hide Generic Lists (Trakt/TMDB) if not in Library
                        if user in ['trakt', 'tmdb'] and not add_to_library:
                            continue

                        list_name_upper = " ".join(w.capitalize() for w in list_name.split())

                        mode_for_list_contents = 'orac.list.build_orac_list'

                        url_params = {
                            'mode': mode_for_list_contents,
                            'user': owner,
                            'slug': slug,
                            'list_type': list_type,
                            'list_name': list_name,
                            'item_type': item_type,
                            'add_to_library': 'true' if add_to_library else 'false'
                        }
                        if randomize_contents: url_params['random'] = 'true'
                        elif shuffle: url_params['shuffle'] = 'true'

                        url = build_url(url_params)

                        if add_to_library:
                            update = 'Remove'
                        else:
                            update = 'Add'
                        add_to_lib_params = {
                            'mode': 'orac.add_to_library',
                            'list_name': list_name,
                            'item_type': item_type,
                            'url': url,
                            'update': update,
                            'user': owner,
                            'slug': slug
                        }
                        if add_to_library:
                            cm_append(('[B]Remove from Library[/B]', f'RunPlugin({build_url(add_to_lib_params)})'))
                        else:
                            cm_append(('[B]Add to Library[/B]', f'RunPlugin({build_url(add_to_lib_params)})'))

                        # Display: "Name (owner) (xCount)" — coloured to match the section header
                        display = '[COLOR %s]%s [I](%s) (x%s)[/I][/COLOR]' % (color, list_name_upper, owner, str(item_count))

                        listitem = make_listitem()
                        listitem.setLabel(display)
                        listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
                        info_tag = listitem.getVideoInfoTag()
                        info_tag.setPlot(' ')
                        listitem.addContextMenuItems(cm)
                        group_tuples.append((url, listitem, True))
                    except Exception as e:
                        logger("Liberator", f"Lists: Error processing list item: {e}")
                        pass

                # Only emit the header + items if there is at least one item in this group
                if group_tuples:
                    header_url = build_url({'mode': 'noop'})
                    header_listitem = make_listitem()
                    header_listitem.setLabel('[COLOR %s][B]── %s ──[/B][/COLOR]' % (color, source.upper()))
                    header_listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
                    info_tag = header_listitem.getVideoInfoTag()
                    info_tag.setPlot(' ')
                    yield (header_url, header_listitem, False)  # Not a folder so nothing happens on click
                    for t in group_tuples:
                        yield t


        if shuffle:
            returning_to_list = 'orac.list.build_orac_list' in folder_path() # This might need adjustment for the category view
            if returning_to_list:
                try: lists = json.loads(get_property('liberator.orac.lists.order')) # Use a distinct property
                except: pass
            else:
                random.shuffle(lists)
                set_property('liberator.orac.lists.order', json.dumps(lists)) # Use a distinct property
            sort_method = 'none'
        else:
            clear_property('liberator.orac.lists.order') # Use a distinct property
            sort_method = 'none'  # Must use 'none' to preserve grouped insertion order
        
        # Add items using addon_handle
        add_items(addon_handle, list(_process_orac_list_category_items()))
        
        # Set content and category using addon_handle
        set_content(addon_handle, 'files') # Or 'directories' if it fits better
        set_category(addon_handle, params.get('category_name', 'Orac Lists')) # Provide a default category name
        set_sort_method(addon_handle, sort_method)
        end_directory(addon_handle)
        set_view_mode('view.main') # Or a specific view for lists
        if shuffle and not returning_to_list: focus_index(0)

    except Exception as e:
        logger("get_orac_lists", "An unexpected error occurred: {e}")
        import traceback
        logger("get_orac_lists", "Traceback: {traceback.format_exc()}")
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Error loading Orac list categories: {e}", xbmcaddon.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)


# This proc builds a list of items in a list specified in the params
# It calls get_orac_list_contents to get the contents of the list, and then movies.worker or tvshows.worker to process the items
def build_orac_list(params, addon_handle):
    def _process(function, _list, _type):
        if not _list['list']: return
        if _type in ('movies', 'tvshows'): item_list_extend(function(_list).worker(return_tuples=True))
        elif _type == 'seasons': item_list_extend(function(_list['list']))
        else: item_list_extend(function('episode.trakt_list', _list['list']))
    def _paginate_list(data, page_no, paginate_start):
        if use_result: total_pages = 1
        elif paginate_enabled:
            limit = page_limit(is_home)
            data, total_pages = paginate_list(data, page_no, limit, paginate_start)
            if is_home: paginate_start = limit
        else: total_pages = 1
        return data, total_pages, paginate_start
    handle, is_external, is_home, content, list_name = int(sys.argv[1]), external(), home(), 'movies', params.get('list_name')
    try:
        logger('orac', 'build_orac_list')
        threads, item_list = [], []
        item_list_extend = item_list.extend
        user, slug, list_type = '', '', ''
        paginate_enabled = paginate(is_home)
        is_random = params.get('random') == 'true' or params.get('user') == 'external_index'
        cache_to_disc = False if (is_external or is_random) else True
        use_result = 'result' in params
        page_no, paginate_start = int(params.get('new_page', '1')), int(params.get('paginate_start', '0'))
        if page_no == 1 and not is_external: set_property('liberator.exit_params', folder_path())
        if use_result: result = params.get('result', [])
        else:
            user, slug, list_type = params.get('user'), params.get('slug'), params.get('list_type')
            item_type = params.get('item_type', 'null')
# Get a list of the contents of the list
            result = get_orac_list_contents(list_type, user, slug, item_type)
        # If we know the item type, only need to process those
        if item_type == 'movie':
            movie_list = {
                'list': [
                    (i, item)
                    for i, item in enumerate(result)
                ],
                'id_type': 'trakt_dict',
                'custom_order': 'true'
            }

            results = orac_movies(movie_list).worker()
            # results is already a list of listitems in the correct order
            if use_result: 
                return results
            add_items(handle, results)
            set_content(handle, 'movies')
            set_category(handle, list_name)
            end_directory(handle, cacheToDisc=cache_to_disc)
            if not is_external:
                if params.get('refreshed') == 'true': sleep(1000)
                set_view_mode('view.movies', 'movies', is_external)
            return

        if item_type == 'tvshow':
            tvshow_list = {
                'list': [
                    (i, item)
                    for i, item in enumerate(result)
                ],
                'id_type': 'trakt_dict',
                'custom_order': 'true'
            }

            results = orac_tvshows(tvshow_list).worker()
            # results is already a list of listitems in the correct order
            if use_result: 
                return results
            add_items(handle, results)
            set_content(handle, 'tvshows')
            set_category(handle, list_name)
            end_directory(handle, cacheToDisc=cache_to_disc)
            if not is_external:
                if params.get('refreshed') == 'true': sleep(1000)
                set_view_mode('view.tvshows', 'tvshows', is_external)
            return


# The above code handles movies and tvshows, needs to also handle episodes
        process_list, total_pages, paginate_start = _paginate_list(result, page_no, paginate_start)
        all_movies = [(idx, i) for idx, i in enumerate(process_list) if i.get('media_type', i.get('type')) == 'movie']
        all_tvshows = [(idx, i) for idx, i in enumerate(process_list) if i.get('media_type', i.get('type')) in ('show', 'tvshow')]
        all_seasons = [dict(i, custom_order=idx) for idx, i in enumerate(process_list) if i.get('media_type', i.get('type')) == 'season']
        all_episodes = [dict(i, custom_order=idx) for idx, i in enumerate(process_list) if i.get('media_type', i.get('type')) in ('episode', 'episode')]
        movie_list = {'list': all_movies, 'id_type': 'trakt_dict', 'custom_order': 'true'}
        tvshow_list = {'list': all_tvshows, 'id_type': 'trakt_dict', 'custom_order': 'true'}
        season_list = {'list': all_seasons}
        episode_list = {'list': all_episodes}
        content = max([('movies', len(all_movies)), ('tvshows', len(all_tvshows)), ('seasons', len(all_seasons)), ('episodes', len(all_episodes))], key=lambda k: k[1])[0]
        for item in ((orac_movies, movie_list, 'movies'), (orac_tvshows, tvshow_list, 'tvshows'),
                    (single_seasons, season_list, 'seasons'), (build_single_episode, episode_list, 'episodes')):
            threaded_object = Thread(target=_process, args=item)
            threaded_object.start()
            threads.append(threaded_object)
        [i.join() for i in threads]
        item_list.sort(key=lambda k: k[1])
        if use_result: return [i[0] for i in item_list]
        add_items(handle, [i[0] for i in item_list])
        if total_pages > page_no:
            new_page = str(page_no + 1)
            new_params = {'mode': 'orac.list.build_orac_list', 'list_type': list_type, 'list_name': list_name, 'item_type': item_type,
                            'user': user, 'slug': slug, 'paginate_start': paginate_start, 'new_page': new_page}
            add_dir(new_params, 'Next Page (%s) >>' % new_page, handle, 'nextpage', nextpage_landscape)
    except: pass
    set_content(handle, content)
    set_category(handle, list_name)
    end_directory(handle, cacheToDisc=cache_to_disc)
    if not is_external:
        if params.get('refreshed') == 'true': sleep(1000)
        set_view_mode('view.%s' % content, content, is_external)


def orac_fetch_list_items(list_type="watchlist", item_type="movie", user=None):

    params = {'name': list_type, 'item_type': item_type, 'user': user}

    if item_type == 'movie':
        list_items = _get_data_via_ipc('get_movie_list_overview',params=params)
        return list_items

    encoded_list_type = quote_plus(list_type)
    orac_address = get_setting('orac_address')
    if not orac_address: return []
    url = f"http://{orac_address}:5555/list?name={encoded_list_type}&item_type={quote_plus(item_type)}&user={quote_plus(user)}"
    timeout = 10

    try:
        response = requests.get(url, timeout=timeout)
        logger("Orac", f"Fetching list '{list_type}' from {url} with type '{item_type}'")
        if response.status_code == 200:
            data = response.json()
            formatted = []
            if item_type == 'movie':
                # Send back data as received, calling def will format it
                return data  # Added return statement to send back raw data
            elif item_type == 'tvshow':
                for i, show in enumerate(data):
                    trakt_id = show.get("trakt_id")
                    slug = show.get("slug")
                    tmdb_id = show.get("tmdb_id")
                    imdb_id = show.get("imdb_id")
                    title = show.get("title")

                    formatted.append({
                        "media_ids": {
                            "trakt": trakt_id,
                            "slug": slug,
                            "tvdb": "",
                            "imdb": imdb_id,
                            "tmdb": tmdb_id,
                            "tvrage": ""
                        },
                        "title": title,
                        "type": "show",
                        'order': i
                    })
            return formatted
        else:
            logger("Orac", f"Failed to fetch list '{list_type}', HTTP {response.status_code}")
    except Exception as e:
        logger("Orac", f"Error fetching list '{list_type}': {e}")


def get_orac_list_contents(list_type, user, slug, item_type):
    logger('orac','get_orac_list_contents')
    params = {'name': slug, 'item_type': item_type, 'user': user}
    list_items = []
    if item_type == 'movie':
        list_items = _get_data_via_ipc('get_movie_list_overview',params=params)
    elif item_type == 'tvshow':
        list_items = _get_data_via_ipc('get_tvshow_list_overview',params=params)
    elif item_type == 'all':
        list_items = _get_data_via_ipc('get_list_overview',params=params)
    return list_items

def orac_lists_manager_choice(params):
    logger('orac','orac_lists_manager_choice')
    icon = params.get('icon', None) or get_icon('trakt')
    choices = [('Add To Orac List...', 'Add'), ('Remove From Orac List...', 'Remove')]
    list_items = [{'line1': item[0], 'icon': icon} for item in choices]
    kwargs = {'items': json.dumps(list_items), 'heading': 'Orac Lists Manager'}
    choice = select_dialog([i[1] for i in choices], **kwargs)
    if choice == None: return
# Here we need to call orac to get the lists, and then show a select dialog to choose which list to add/remove from
# We provide the tmdb_id and the type (add/remove) in params, orac will give us a suitable list to choose from
    if choice == 'Add':
        item_type = params.get('media_type', 'movie')
        ipc_params = {'name': 'add_list_options', 'item_type': item_type, 'tmdb_id': params.get('tmdb_id')}
        my_lists = _get_data_via_ipc('get_lists',params=ipc_params)
        if not my_lists: return None
        logger('orac',f'my_lists {my_lists}')
        my_lists = [{'name': item['name'], 'display': '[B](%s)[/B] [I]%s[/I]' % (item['source'], item['name'].upper()), 'user': item['user'], 'slug': item['slug'], 'source': item.get('source', 'trakt')} for item in my_lists]
        list_items = [{'line1': item['display'], 'icon': icon} for item in my_lists]
        kwargs = {'items': json.dumps(list_items), 'heading': 'Select Orac List'}
        chosen_list_name = select_dialog([i['name'] for i in my_lists], **kwargs)
        if chosen_list_name is None: return None
        chosen_list = next((item for item in my_lists if item['name'] == chosen_list_name), None)
        if not chosen_list: return None
# Add to the chosen list
        ipc_params = {'tmdb_id': params.get('tmdb_id'), 'user': chosen_list['user'], 'slug': chosen_list['slug'], 'list_name': chosen_list['name'], 'item_type': item_type, 'source': chosen_list['source']}
        result = _get_data_via_ipc('add_to_list',params=ipc_params)
# Display a notification based on result
        if result.get('status') == 'success':
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Added to list '{chosen_list['name']}'", xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Failed to add to list '{chosen_list['name']}': {result.get('message', 'Unknown error')}", xbmcgui.NOTIFICATION_ERROR)
        return result
    elif choice == 'Remove':
        item_type = params.get('media_type', 'movie')
        ipc_params = {'name': 'remove_list_options', 'item_type': item_type, 'tmdb_id': params.get('tmdb_id')}
        my_lists = _get_data_via_ipc('get_lists',params=ipc_params)
        if not my_lists: return None
        logger('orac',f'my_lists {my_lists}')
        my_lists = [{'name': item['name'], 'display': '[B](%s)[/B] [I]%s[/I]' % (item['source'], item['name'].upper()), 'user': item['user'], 'slug': item['slug'], 'source': item.get('source', 'trakt')} for item in my_lists]
        list_items = [{'line1': item['display'], 'icon': icon} for item in my_lists]
        kwargs = {'items': json.dumps(list_items), 'heading': 'Select Orac List'}
        chosen_list_name = select_dialog([i['name'] for i in my_lists], **kwargs)
        if chosen_list_name is None: return None
        chosen_list = next((item for item in my_lists if item['name'] == chosen_list_name), None)
        if not chosen_list: return None
# Remove from the chosen list
        ipc_params = {'tmdb_id': params.get('tmdb_id'), 'user': chosen_list['user'], 'slug': chosen_list['slug'], 'list_name': chosen_list['name'], 'item_type': item_type, 'source': chosen_list['source']}
        result = _get_data_via_ipc('remove_from_list',params=ipc_params)
# Display a notification based on result
        if result.get('status') == 'success':
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Removed from list '{chosen_list['name']}'", xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Failed to remove from list '{chosen_list['name']}': {result.get('message', 'Unknown error')}", xbmcgui.NOTIFICATION_ERROR)
        return result

    return None

def add_orac_list_to_library(params, addon_handle):
    logger('orac','add_orac_list_to_library')
    list_name = params.get('list_name')
    item_type = params.get('item_type', 'movie')
    url = params.get('url')
    update = params.get('update')
    ipc_params = {'name': 'update_library_status', 'list_name': list_name, 'user': params.get('user'), 'slug': params.get('slug'), 'item_type': item_type, 'update': update}
    result = _get_data_via_ipc('update_list_library_status',params=ipc_params)
    if result.get('status') == 'success':
        if update == 'Add':
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Added list '{list_name}' to library", xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Removed list '{list_name}' from library", xbmcgui.NOTIFICATION_INFO)

        # Refresh the list view to reflect the change
        kodi_utils.container_refresh()
        return result
    else:
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Failed to update library status for list '{list_name}': {result.get('message', 'Unknown error')}", xbmcgui.NOTIFICATION_ERROR)
    return None

def unlike_orac_list(params, addon_handle):
    logger('orac','unlike_orac_list')
    list_name = params.get('list_name')
    user = params.get('user')
    slug = params.get('slug')
    ipc_params = {'name': 'unlike_trakt_list', 'list_name': list_name, 'user': user, 'slug': slug}
    result = _get_data_via_ipc('unlike_trakt_list',params=ipc_params)
    if result.get('status') == 'success':
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Unliked Trakt list '{list_name}'", xbmcgui.NOTIFICATION_INFO)

        # Refresh the list view to reflect the change
        kodi_utils.container_refresh()
        return result
    else:
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Failed to unlike Trakt list '{list_name}': {result.get('message', 'Unknown error')}", xbmcgui.NOTIFICATION_ERROR)
    return None

def force_orac_sync(params, addon_handle):
    logger('orac', 'force_orac_sync CALLED')
    try:
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Requesting forced sync...", xbmcgui.NOTIFICATION_INFO)
        
        # We call the service processing of 'force_sync'
        # Params can be empty
        logger('orac', 'Calling _get_data_via_ipc for force_sync')
        result = _get_data_via_ipc('force_sync', params={})
        logger('orac', f'force_sync result: {result}')
        
        if result and result.get('status') == 'started':
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Orac Sync Started.", xbmcgui.NOTIFICATION_INFO)
        else:
            msg = result.get('message', 'Unknown error') if result else 'Timeout/Error'
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Sync request failed: {msg}", xbmcgui.NOTIFICATION_ERROR)
        return result
    except Exception as e:
        logger('orac', f'force_orac_sync FAILED: {e}')
        import traceback
        logger('orac', traceback.format_exc())
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Error: {e}", xbmcgui.NOTIFICATION_ERROR)
        return None
