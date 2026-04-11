
import sys
import json
from modules import kodi_utils
from modules.utils import paginate_list
from modules.settings import paginate, page_limit
import xbmcgui
import xbmcplugin
import xbmcaddon
from apis.orac_api import OracClient

add_dir, external, sleep, get_icon = kodi_utils.add_dir, kodi_utils.external, kodi_utils.sleep, kodi_utils.get_icon
trakt_icon, fanart, add_item, set_property = get_icon('trakt'), kodi_utils.get_addon_fanart(), kodi_utils.add_item, kodi_utils.set_property
set_content, set_sort_method, set_view_mode, end_directory, set_category = kodi_utils.set_content, kodi_utils.set_sort_method, kodi_utils.set_view_mode, kodi_utils.end_directory, kodi_utils.set_category
make_listitem, build_url, add_items = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.add_items
logger = kodi_utils.logger

ADDON = xbmcaddon.Addon('plugin.video.liberator')

def get_orac_client():
    from caches.settings_cache import get_setting
    orac_address = get_setting('orac_address') or '127.0.0.1'
    return OracClient(f"http://{orac_address}:5555")

def tags_manager(params, addon_handle):
    """
    Displays the list of all tags with counts.
    """
    logger("tags_manager", "Displaying tags manager")
    
    try:
        client = get_orac_client()
        response = client.get_all_tags(details=True)
        
        if not response.get('success'):
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Error fetching tags", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return

        tags = response.get('tags', [])
        
        if not tags:
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "No tags found", xbmcgui.NOTIFICATION_INFO)
            # Add a placeholder item? Or just empty directory
            # item = make_listitem()
            # item.setLabel("No tags created yet")
            # add_item(addon_handle, "", item, False)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=True)
            return

        for tag in tags:
            tag_name = tag.get('tag_name')
            total_count = tag.get('total_count', 0)
            movie_count = tag.get('movie_count', 0)
            show_count = tag.get('show_count', 0)
            
            # Format display label
            # e.g. "Action [5 Movies, 2 Shows]"
            counts_parts = []
            if movie_count > 0:
                counts_parts.append(f"{movie_count} Movie{'s' if movie_count != 1 else ''}")
            if show_count > 0:
                counts_parts.append(f"{show_count} Show{'s' if show_count != 1 else ''}")
            
            counts_str = ", ".join(counts_parts)
            if not counts_str:
                counts_str = "Empty"
                
            display_label = f"{tag_name.capitalize()} [I][COLOR gray]({counts_str})[/COLOR][/I]"
            
            url_params = {
                'mode': 'orac.tags.list',
                'tag_name': tag_name
            }
            url = build_url(url_params)
            
            listitem = make_listitem()
            listitem.setLabel(display_label)
            # Use a tag icon if available, or generic folder icon
            # listitem.setArt({'icon': 'DefaultIcon.png'}) 
            
            info_tag = listitem.getVideoInfoTag()
            info_tag.setPlot(f"Browse {tag_name} items")
            
            add_item(addon_handle, url, listitem, True)
            
        set_content(addon_handle, 'files')
        set_category(addon_handle, 'Tag Manager')
        set_sort_method(addon_handle, 'label')
        end_directory(addon_handle)
        set_view_mode('view.main')
        
    except Exception as e:
        logger("tags_manager", f"Error: {e}")
        import traceback
        logger("tags_manager", f"Traceback: {traceback.format_exc()}")
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Error loading items: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)

def build_tag_list(params, addon_handle):
    """
    Displays the mixed list of items for a specific tag.
    Uses orac_lists logic to build the list items.
    """
    tag_name = params.get('tag_name')
    logger("build_tag_list", f"Building list for tag: {tag_name}")
    
    try:
        from indexers.orac_lists import build_orac_list
        # We can re-use build_orac_list logic? 
        # build_orac_list takes 'list_type', 'user', 'slug' and calls get_orac_list_contents.
        # But here we have a tag, not a list.
        # It's better to manually fetch items and then call orac_movies/orac_tvshows workers.
        # But wait, orac_movies/tvshows expect specific list format.
        
        client = get_orac_client()
        response = client.get_tag_items(tag_name)
        
        if not response.get('success'):
            xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), "Error fetching tag items", xbmcgui.NOTIFICATION_ERROR)
            xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
            return
            
        items = response.get('items', [])
        
        # Separate movies and shows
        movie_items = [i for i in items if i.get('media_type') == 'movie']
        show_items = []
        for i in items:
            if i.get('media_type') in ('show', 'tvshow'):
                if 'show_tmdb_id' in i and 'tmdb_id' not in i:
                    i['tmdb_id'] = i['show_tmdb_id']
                show_items.append(i)
        
        # We need to format these items for orac_movies/tvshows workers.
        # They expect dicts with 'trakt_id', 'tmdb_id', etc.
        # Our enriched items from server should have this.
        
        # Construct lists for workers
        movie_list_data = {
            'list': [(idx, item) for idx, item in enumerate(movie_items)],
            'id_type': 'trakt_dict',
            'custom_order': 'true' # Preserve server order? Or sort?
        }
        
        show_list_data = {
            'list': [(idx, item) for idx, item in enumerate(show_items)],
            'id_type': 'trakt_dict',
            'custom_order': 'true'
        }

        # Run workers to build listitems only if we have items
        all_listitems = []
        
        if movie_items:
            from indexers.orac_movies import orac_movies
            movies_worker = orac_movies(movie_list_data)
            movie_listitems = movies_worker.worker()
            all_listitems.extend(movie_listitems)
            
        if show_items:
            from indexers.orac_tvshows import orac_tvshows
            shows_worker = orac_tvshows(show_list_data)
            show_listitems = shows_worker.worker()
            all_listitems.extend(show_listitems)
            
        # Sort mixed list alpha? Or by date? 
        # For now, maybe just append. Or sort by label.
        # The user might prefer movies then shows, or mixed.
        # Let's sort by label (title)
        # all_listitems.sort(key=lambda x: x.getLabel()) 
        # Wait, listitems are objects.
        # Worker returns list of listitems.
        
        add_items(addon_handle, all_listitems)
        
        set_content(addon_handle, 'movies') # Mixed content... separate view types?
        # Kodi doesn't support mixed content type well for view modes. 'movies' or 'tvshows' or 'files'.
        # 'movies' usually works okay for mixed video lists.
        
        set_category(addon_handle, f"Tag: {tag_name}")
        end_directory(addon_handle)
        set_view_mode('view.movies') # Use movies view
        
    except Exception as e:
        logger("build_tag_list", f"Error: {e}")
        import traceback
        logger("build_tag_list", f"Traceback: {traceback.format_exc()}")
        xbmcgui.Dialog().notification(ADDON.getAddonInfo('name'), f"Error loading tag items: {e}", xbmcgui.NOTIFICATION_ERROR)
        xbmcplugin.endOfDirectory(addon_handle, succeeded=False)
