# -*- coding: utf-8 -*-
import copy
import json
import os
from core.kodi import (
    ADDON_DATA,
    add_dir,
    build_url,
    container_refresh,
    dialog_confirm,
    dialog_input,
    dialog_select,
    end_directory,
    load_json_file,
    notification,
    save_json_file,
    set_category,
    set_content,
    set_sort_method,
    set_view_mode,
)

MENUS_FILE = os.path.join(ADDON_DATA, 'menus.json')
SHORTCUTS_FILE = os.path.join(ADDON_DATA, 'shortcuts.json')
RUN_PLUGIN = 'RunPlugin(%s)'

DEFAULT_ROOT_MENU = [
    {'name': 'My Library', 'mode': 'navigator.my_library', 'icon': 'lists', 'is_folder': True},
    {'name': 'Movies', 'mode': 'navigator.movies', 'icon': 'movies', 'is_folder': True},
    {'name': 'TV Shows', 'mode': 'navigator.tvshows', 'icon': 'tv', 'is_folder': True},
    {'name': 'Anime', 'mode': 'navigator.anime', 'icon': 'anime', 'is_folder': True},
    {'name': 'Lists Manager', 'mode': 'lists.manager_categories', 'icon': 'trakt', 'is_folder': True},
    {'name': 'Shortcut Folders', 'mode': 'shortcuts.folders', 'icon': 'folder', 'is_folder': True},
    {'name': 'Search', 'mode': 'navigator.search', 'icon': 'search', 'is_folder': True},
    {'name': 'My Services', 'mode': 'navigator.premium', 'icon': 'folder', 'is_folder': True},
    {'name': 'Tools & Settings', 'mode': 'navigator.tools', 'icon': 'settings', 'is_folder': True},
]


def _load_menus():
    return load_json_file(MENUS_FILE, {})


def _save_menus(data):
    save_json_file(MENUS_FILE, data)


def get_menu_items(list_name='RootList'):
    menus = _load_menus()
    items = menus.get(list_name)
    if items and isinstance(items, list):
        return copy.deepcopy(items)
    if list_name == 'RootList':
        return copy.deepcopy(DEFAULT_ROOT_MENU)
    return []


def _save_menu_items(list_name, items):
    menus = _load_menus()
    menus[list_name] = items
    _save_menus(menus)


def menu_move(handle, params):
    list_name = params.get('active_list', 'RootList')
    pos = int(params.get('position', '0'))
    items = get_menu_items(list_name)
    if len(items) <= 1 or not (0 <= pos < len(items)):
        return
    moving = items[pos]
    targets = [f'Position {i + 1}: {entry.get("name", "")}' for i, entry in enumerate(items)]
    new_pos = dialog_select(f'Move "{moving.get("name", "")}" To', targets)
    if new_pos < 0 or new_pos == pos:
        return
    items.insert(new_pos, items.pop(pos))
    _save_menu_items(list_name, items)
    container_refresh()


def menu_remove(handle, params):
    list_name = params.get('active_list', 'RootList')
    pos = int(params.get('position', '0'))
    items = get_menu_items(list_name)
    if len(items) <= 1 or not (0 <= pos < len(items)):
        notification('Cannot remove the last menu item')
        return
    item_name = items[pos].get('name', 'Item')
    if not dialog_confirm('Remove Menu Item', f'Remove [B]{item_name}[/B] from main menu?'):
        return
    items.pop(pos)
    _save_menu_items(list_name, items)
    container_refresh()


def menu_rename(handle, params):
    list_name = params.get('active_list', 'RootList')
    pos = int(params.get('position', '0'))
    items = get_menu_items(list_name)
    if not (0 <= pos < len(items)):
        return
    old_name = items[pos].get('name', '')
    new_name = dialog_input('Rename Menu Item', old_name).strip()
    if not new_name or new_name == old_name:
        return
    items[pos]['name'] = new_name
    _save_menu_items(list_name, items)
    container_refresh()


def menu_restore(handle, params):
    list_name = params.get('active_list', 'RootList')
    if not dialog_confirm('Restore Default Menu', 'Restore the main menu back to defaults?'):
        return
    menus = _load_menus()
    menus.pop(list_name, None)
    _save_menus(menus)
    notification('Menu restored to default')
    container_refresh()


# --- Shortcut Folders ---

def _load_shortcuts():
    data = load_json_file(SHORTCUTS_FILE, {})
    return data if isinstance(data, dict) else {}


def _save_shortcuts(data):
    save_json_file(SHORTCUTS_FILE, data)


def folders(handle, params):
    add_dir(
        handle,
        {'mode': 'shortcuts.folder_create'},
        '[B]+ Create New Shortcut Folder[/B]',
        icon='new',
        is_folder=False,
    )
    data = _load_shortcuts()
    for folder_name, items in data.items():
        count = len(items) if isinstance(items, list) else 0
        cm = [
            ('[B]Rename Folder[/B]', RUN_PLUGIN % build_url({'mode': 'shortcuts.folder_rename', 'folder': folder_name})),
            ('[B]Clear Folder[/B]', RUN_PLUGIN % build_url({'mode': 'shortcuts.folder_clear', 'folder': folder_name})),
            ('[B]Delete Folder[/B]', RUN_PLUGIN % build_url({'mode': 'shortcuts.folder_delete', 'folder': folder_name})),
        ]
        add_dir(
            handle,
            {'mode': 'shortcuts.folder_contents', 'folder': folder_name},
            f'{folder_name} [I](x{count})[/I]',
            icon='folder',
            is_folder=True,
            cm_items=cm,
        )
    set_content(handle, 'files')
    set_category(handle, 'Shortcut Folders')
    set_sort_method(handle, 'none')
    end_directory(handle)
    set_view_mode('main', 'files')


def folder_contents(handle, params):
    folder_name = params.get('folder', '')
    data = _load_shortcuts()
    items = data.get(folder_name, [])
    for idx, entry in enumerate(items):
        url_params = dict(entry.get('url_params') or {})
        name = entry.get('name', 'Shortcut')
        icon = entry.get('icon', 'folder')
        is_folder = bool(entry.get('is_folder', True))
        cm = [
            ('[B]Move[/B]', RUN_PLUGIN % build_url({'mode': 'shortcuts.item_move', 'folder': folder_name, 'position': str(idx)})),
            ('[B]Rename[/B]', RUN_PLUGIN % build_url({'mode': 'shortcuts.item_rename', 'folder': folder_name, 'position': str(idx)})),
            ('[B]Remove[/B]', RUN_PLUGIN % build_url({'mode': 'shortcuts.item_remove', 'folder': folder_name, 'position': str(idx)})),
        ]
        add_dir(handle, url_params, name, icon=icon, is_folder=is_folder, cm_items=cm)
    set_content(handle, 'files')
    set_category(handle, folder_name or 'Shortcut Folder')
    set_sort_method(handle, 'none')
    end_directory(handle)
    set_view_mode('main', 'files')


def folder_create(handle, params):
    name = dialog_input('New Shortcut Folder Name').strip()
    if not name:
        return
    data = _load_shortcuts()
    if name in data:
        notification('Shortcut folder already exists')
        return
    data[name] = []
    _save_shortcuts(data)
    notification(f'Created folder: {name}')
    container_refresh()


def folder_rename(handle, params):
    old_name = params.get('folder', '')
    if not old_name:
        return
    new_name = dialog_input('Rename Shortcut Folder', old_name).strip()
    if not new_name or new_name == old_name:
        return
    data = _load_shortcuts()
    if old_name not in data:
        return
    if new_name in data:
        notification('A folder with that name already exists')
        return
    new_data = {}
    for k, v in data.items():
        new_data[new_name if k == old_name else k] = v
    _save_shortcuts(new_data)
    container_refresh()


def folder_delete(handle, params):
    folder_name = params.get('folder', '')
    if not folder_name or not dialog_confirm('Delete Folder', f'Delete shortcut folder [B]{folder_name}[/B]?'):
        return
    data = _load_shortcuts()
    data.pop(folder_name, None)
    _save_shortcuts(data)
    container_refresh()


def folder_clear(handle, params):
    folder_name = params.get('folder', '')
    if not folder_name or not dialog_confirm('Clear Folder', f'Clear all items from [B]{folder_name}[/B]?'):
        return
    data = _load_shortcuts()
    if folder_name in data:
        data[folder_name] = []
        _save_shortcuts(data)
        container_refresh()


def add_to_folder(handle, params):
    name = params.get('name', 'Shortcut')
    icon = params.get('icon', 'folder')
    is_folder = params.get('is_folder', 'true') == 'true'
    try:
        url_params = json.loads(params.get('url_params', '{}'))
    except ValueError:
        notification('Invalid shortcut parameters')
        return
    if not url_params:
        notification('Nothing to add')
        return

    data = _load_shortcuts()
    folder_names = list(data.keys())
    options = ['+ Create New Shortcut Folder'] + folder_names
    idx = dialog_select('Add to Shortcut Folder', options)
    if idx < 0:
        return
    if idx == 0:
        folder_name = dialog_input('New Shortcut Folder Name').strip()
        if not folder_name:
            return
        data.setdefault(folder_name, [])
    else:
        folder_name = folder_names[idx - 1]

    custom_name = dialog_input('Shortcut Label', name).strip() or name
    data[folder_name].append({
        'name': custom_name,
        'url_params': url_params,
        'icon': icon,
        'is_folder': is_folder,
    })
    _save_shortcuts(data)
    notification(f'Added "{custom_name}" to {folder_name}')


def item_move(handle, params):
    folder_name = params.get('folder', '')
    pos = int(params.get('position', '0'))
    data = _load_shortcuts()
    items = data.get(folder_name, [])
    if len(items) <= 1 or not (0 <= pos < len(items)):
        return
    targets = [f'Position {i + 1}: {entry.get("name", "")}' for i, entry in enumerate(items)]
    new_pos = dialog_select(f'Move "{items[pos].get("name", "")}" To', targets)
    if new_pos < 0 or new_pos == pos:
        return
    items.insert(new_pos, items.pop(pos))
    data[folder_name] = items
    _save_shortcuts(data)
    container_refresh()


def item_rename(handle, params):
    folder_name = params.get('folder', '')
    pos = int(params.get('position', '0'))
    data = _load_shortcuts()
    items = data.get(folder_name, [])
    if not (0 <= pos < len(items)):
        return
    old_name = items[pos].get('name', '')
    new_name = dialog_input('Rename Shortcut', old_name).strip()
    if not new_name or new_name == old_name:
        return
    items[pos]['name'] = new_name
    data[folder_name] = items
    _save_shortcuts(data)
    container_refresh()


def item_remove(handle, params):
    folder_name = params.get('folder', '')
    pos = int(params.get('position', '0'))
    data = _load_shortcuts()
    items = data.get(folder_name, [])
    if not (0 <= pos < len(items)):
        return
    if not dialog_confirm('Remove Shortcut', f'Remove [B]{items[pos].get("name", "Shortcut")}[/B]?'):
        return
    items.pop(pos)
    data[folder_name] = items
    _save_shortcuts(data)
    container_refresh()
