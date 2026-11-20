# -*- coding: utf-8 -*-
import json
import os
import sys
from urllib.parse import urlencode
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import xbmcvfs
from core.settings import use_viewtypes

ADDON_ID = 'plugin.video.liberator2'
ADDON = xbmcaddon.Addon(ADDON_ID)
ADDON_NAME = ADDON.getAddonInfo('name')
ADDON_PATH = ADDON.getAddonInfo('path')
ADDON_DATA = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
VIEWS_FILE = os.path.join(ADDON_DATA, 'views.json')
MEDIA_PATH = os.path.join(ADDON_PATH, 'resources', 'media', 'icons')
FANART_PATH = os.path.join(ADDON_PATH, 'fanart.jpg')
ICON_PATH = os.path.join(ADDON_PATH, 'icon.png')
EMPTY_POSTER = os.path.join(MEDIA_PATH, 'box_office.png')
NEXTPAGE_ICON = os.path.join(MEDIA_PATH, 'nextpage.png')

HOME_WINDOW = xbmcgui.Window(10000)


def ensure_addon_data():
    os.makedirs(ADDON_DATA, exist_ok=True)
    return ADDON_DATA


def load_json_file(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return default


def save_json_file(path, data):
    ensure_addon_data()
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, indent=2)


def logger(tag, message):
    xbmc.log(f'[{ADDON_NAME}] [{tag}] {message}', xbmc.LOGINFO)


def addon_fanart():
    return FANART_PATH


_ICON_CACHE = {}


def get_icon(name):
    if not name:
        return ICON_PATH
    cached = _ICON_CACHE.get(name)
    if cached is not None:
        return cached
    if name.startswith(('http://', 'https://', 'special://')):
        resolved = name
    else:
        candidate = os.path.join(MEDIA_PATH, f'{name}.png')
        resolved = candidate if xbmcvfs.exists(candidate) else ICON_PATH
    _ICON_CACHE[name] = resolved
    return resolved


def build_url(params):
    clean = {k: v for k, v in params.items() if v is not None}
    return f'plugin://{ADDON_ID}/?{urlencode(clean)}'


def make_listitem(label=''):
    return xbmcgui.ListItem(label=label, offscreen=True)


def add_item(handle, url, listitem, is_folder=True):
    xbmcplugin.addDirectoryItem(handle=handle, url=url, listitem=listitem, isFolder=is_folder)


def add_items(handle, items):
    xbmcplugin.addDirectoryItems(handle=handle, items=items, totalItems=len(items))


def make_dir_item(params, name, icon='folder', is_folder=True, cm_items=None):
    url = build_url(params)
    li = make_listitem(name)
    icon_img = get_icon(icon)
    li.setArt({'icon': icon_img, 'thumb': icon_img, 'poster': icon_img, 'fanart': FANART_PATH})
    if cm_items:
        li.addContextMenuItems(cm_items)
    return url, li, is_folder


def add_dir(handle, params, name, icon='folder', is_folder=True, cm_items=None):
    url, li, folder = make_dir_item(params, name, icon=icon, is_folder=is_folder, cm_items=cm_items)
    add_item(handle, url, li, is_folder=folder)


def set_content(handle, content):
    xbmcplugin.setContent(handle, content)


def set_category(handle, category):
    xbmcplugin.setPluginCategory(handle, category)


def set_sort_method(handle, method='none'):
    sort_map = {
        'none': xbmcplugin.SORT_METHOD_NONE,
        'label': xbmcplugin.SORT_METHOD_LABEL,
        'title': xbmcplugin.SORT_METHOD_VIDEO_TITLE,
        'date': xbmcplugin.SORT_METHOD_DATE,
        'episode': xbmcplugin.SORT_METHOD_EPISODE,
    }
    xbmcplugin.addSortMethod(handle, sort_map.get(method, xbmcplugin.SORT_METHOD_NONE))


def end_directory(handle, cache_to_disc=True):
    xbmcplugin.endOfDirectory(handle, succeeded=True, cacheToDisc=cache_to_disc)


def external():
    return 'plugin' not in xbmc.getInfoLabel('Container.PluginName')


def home():
    return xbmcgui.getCurrentWindowId() == 10000


def container_refresh():
    xbmc.executebuiltin('Container.Refresh')


def container_update(url):
    xbmc.executebuiltin(f'Container.Update({url})')


def open_settings():
    ADDON.openSettings()


def notification(message, duration=3000, level=xbmcgui.NOTIFICATION_INFO, heading=ADDON_NAME):
    xbmcgui.Dialog().notification(heading, message, level, duration)


def dialog_ok(heading, message):
    xbmcgui.Dialog().ok(heading, message)


def dialog_confirm(heading, message):
    return xbmcgui.Dialog().yesno(heading, message)


def dialog_select(heading, options):
    return xbmcgui.Dialog().select(heading, options)


def dialog_multiselect(heading, options):
    return xbmcgui.Dialog().multiselect(heading, options)


def dialog_input(heading, default=''):
    return xbmcgui.Dialog().input(heading, default)


def get_property(key):
    return HOME_WINDOW.getProperty(key)


def set_property(key, value):
    HOME_WINDOW.setProperty(key, str(value))


def clear_property(key):
    HOME_WINDOW.clearProperty(key)


def paginate_list(data, page_no, limit, paginate_start=0):
    if not data:
        return [], 1
    total_pages = max(1, (len(data) - paginate_start + limit - 1) // limit)
    start = paginate_start + (page_no - 1) * limit
    end = start + limit
    return data[start:end], total_pages


def execute_builtin(command):
    xbmc.executebuiltin(command)


def show_busy_dialog():
    xbmc.executebuiltin('ActivateWindow(busydialognocancel)')


def hide_busy_dialog():
    xbmc.executebuiltin('Dialog.Close(busydialognocancel)')
    xbmc.executebuiltin('Dialog.Close(busydialog)')


def addon_enabled(addon_id):
    return bool(xbmc.getCondVisibility(f'System.HasAddon({addon_id})'))


def play_trailer(trailer_url):
    if not trailer_url:
        notification('No trailer available')
        return
    url = str(trailer_url).strip()
    if not url.startswith(('http://', 'https://', 'plugin://')):
        url = f'plugin://plugin.video.youtube/play/?video_id={url}'
    elif 'youtube.com/watch?v=' in url:
        video_id = url.split('v=', 1)[1].split('&', 1)[0]
        url = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
    elif 'youtu.be/' in url:
        video_id = url.split('youtu.be/', 1)[1].split('?', 1)[0]
        url = f'plugin://plugin.video.youtube/play/?video_id={video_id}'
    if url.startswith('plugin://plugin.video.youtube') and not addon_enabled('plugin.video.youtube'):
        notification('YouTube addon is required to play trailers')
        return
    xbmc.Player().play(url)


def load_views():
    return load_json_file(VIEWS_FILE, {})


def save_view_mode(view_key, view_id):
    views = load_views()
    views[view_key] = str(view_id)
    save_json_file(VIEWS_FILE, views)


def current_view_id():
    try:
        win = xbmcgui.Window(xbmcgui.getCurrentWindowId())
        return win.getFocusId()
    except Exception:
        return 0


def set_view_mode(view_key, content='files', is_external=None):
    if not use_viewtypes():
        return
    if is_external is None:
        is_external = external()
    if is_external:
        return
    view_id = load_views().get(view_key)
    if not view_id:
        return
    try:
        if content != 'files':
            for _ in range(30):
                if xbmc.getInfoLabel('Container.Content') == content:
                    break
                xbmc.sleep(50)
            else:
                return
        else:
            xbmc.sleep(50)
        xbmc.executebuiltin(f'Container.SetViewMode({view_id})')
    except Exception:
        return
