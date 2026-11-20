# -*- coding: utf-8 -*-
import json
from collections import OrderedDict
from core.kodi import (
    NEXTPAGE_ICON,
    add_items,
    build_url,
    container_refresh,
    container_update,
    dialog_select,
    end_directory,
    external,
    home,
    logger,
    make_dir_item,
    notification,
    paginate_list,
    set_category,
    set_content,
    set_sort_method,
    set_view_mode,
)
from core.settings import page_limit, paginate, trakt_user, widget_hide_next_page, widget_hide_watched
from orac.client import OracClientError, get_orac_client
from orac.infotagger import build_episode_item, build_movie_item, build_tvshow_item

RUN_PLUGIN = 'RunPlugin(%s)'

_SOURCE_COLORS = {
    'trakt':      'FFADD8E6',
    'mdblist':    'FF90EE90',
    'tmdb':       'FFFFFFB3',
    'simkl':      'FFCCB0FF',
    'punchplay':  'FFFFC04D',
    'imdb':       'FFFFB6C1',
    'orac_local': 'FF00FFCC',
    'local':      'FF00FFCC',
}
_COLOR_CYCLE = ['FFADD8E6', 'FF90EE90', 'FFFFFFB3', 'FFCCB0FF', 'FFFFB6C1']
_SOURCE_ICONS = {
    'trakt': 'trakt',
    'tmdb':  'tmdb',
    'imdb':  'imdb',
}
_GENERIC_USERS = {'trakt', 'tmdb', 'simkl', 'punchplay', 'external index', 'external_index'}


def _source_color(source, cycle_idx):
    if source in _SOURCE_COLORS:
        return _SOURCE_COLORS[source]
    color = _COLOR_CYCLE[cycle_idx[0] % len(_COLOR_CYCLE)]
    cycle_idx[0] += 1
    return color


def _handle_orac_error(handle, exc):
    logger('Lists', f'Orac error: {exc}')
    notification(str(exc))
    end_directory(handle, cache_to_disc=False)


def get_lists(handle, params):
    list_type = params.get('list_type', 'my_lists')
    item_type = params.get('item_type')
    source_filter = (params.get('source_filter') or '').lower()
    category_name = params.get('category_name', 'Lists')

    try:
        client = get_orac_client()
        req = {'name': list_type, 'list_type': list_type, 'exclude_empty': 'true'}
        if item_type:
            req['item_type'] = item_type
        lists_data = client.get_lists(req) or []
    except OracClientError as exc:
        _handle_orac_error(handle, exc)
        return

    grouped = OrderedDict()
    for entry in lists_data:
        source = (entry.get('source') or 'unknown').lower()
        if source_filter and source != source_filter:
            continue
        grouped.setdefault(source, []).append(entry)

    kodi_items = []
    cycle_idx = [0]
    for source, entries in grouped.items():
        color = _source_color(source, cycle_idx)
        icon = _SOURCE_ICONS.get(source, 'lists')
        group_items = []

        for entry in entries:
            name = entry.get('name') or entry.get('title') or entry.get('slug') or 'Unnamed List'
            slug = entry.get('slug') or name
            user = entry.get('user') or ''
            owner = entry.get('owner') or user
            add_to_library = bool(entry.get('add_to_library', False))

            if user.lower() in _GENERIC_USERS and not add_to_library:
                continue

            item_count = entry.get('item_count')
            entry_type = entry.get('item_type') or item_type or 'null'
            entry_list_type = entry.get('list_type') or list_type
            display_name = ' '.join(w.capitalize() for w in name.split())
            if item_count is not None and owner:
                label = f'[COLOR {color}]{display_name} [I]({owner}) (x{item_count})[/I][/COLOR]'
            else:
                label = f'[COLOR {color}]{display_name}[/COLOR]'

            url_params = {
                'mode': 'lists.build_list',
                'list_type': entry_list_type,
                'list_name': name,
                'item_type': entry_type,
                'user': owner,
                'slug': slug,
            }
            cm = [
                ('[B]Add to Shortcut Folder[/B]', RUN_PLUGIN % build_url({
                    'mode': 'shortcuts.add_to_folder',
                    'name': name,
                    'icon': icon,
                    'url_params': json.dumps(url_params),
                })),
            ]
            if slug:
                cm.append(('[B]Force Resync[/B]', RUN_PLUGIN % build_url({'mode': 'lists.force_sync'})))

            group_items.append((url_params, label, cm))

        if not group_items:
            continue

        if not source_filter:
            kodi_items.append(make_dir_item(
                {
                    'mode': 'lists.get_lists',
                    'list_type': list_type,
                    'item_type': item_type,
                    'source_filter': source,
                    'category_name': f'{source.upper()} Lists',
                },
                f'[COLOR {color}][B]-- {source.upper()} --[/B][/COLOR]',
                icon=icon,
                is_folder=True,
            ))
        for url_params, label, cm in group_items:
            kodi_items.append(make_dir_item(url_params, label, icon=icon, is_folder=True, cm_items=cm))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, category_name)
    set_sort_method(handle, 'none')
    end_directory(handle)
    set_view_mode('main', 'files')


def build_list(handle, params):
    list_type = params.get('list_type', 'my_lists')
    list_name = params.get('list_name', 'List')
    item_type = params.get('item_type', 'null')
    user = params.get('user', '')
    slug = params.get('slug', '')
    page_no = int(params.get('new_page', '1'))
    paginate_start = int(params.get('paginate_start', '0'))

    is_external = external()
    is_home = home()
    hide_watched = is_home and widget_hide_watched()

    try:
        client = get_orac_client()
        items_data = client.get_list_overview({
            'name': slug or list_name,
            'item_type': item_type,
            'user': user,
        }) or []
    except OracClientError as exc:
        _handle_orac_error(handle, exc)
        return

    total_pages = 1
    if paginate(is_home):
        limit = page_limit(is_home)
        items_data, total_pages = paginate_list(items_data, page_no, limit, paginate_start)

    kodi_items = []
    counts = {'movies': 0, 'tvshows': 0, 'episodes': 0}

    for raw in items_data:
        mtype = raw.get('media_type') or raw.get('type') or item_type
        built = None
        if mtype == 'movie':
            built = build_movie_item(raw, is_external=is_external, hide_watched=hide_watched)
            if built:
                counts['movies'] += 1
        elif mtype in ('show', 'tvshow'):
            built = build_tvshow_item(raw, is_external=is_external, hide_watched=hide_watched)
            if built:
                counts['tvshows'] += 1
        elif mtype == 'episode':
            built = build_episode_item(raw, include_show_prefix=True)
            if built:
                counts['episodes'] += 1

        if built:
            kodi_items.append(built)

    if total_pages > page_no and not (is_home and widget_hide_next_page()):
        next_page = str(page_no + 1)
        kodi_items.append(make_dir_item(
            {
                'mode': 'lists.build_list',
                'list_type': list_type,
                'list_name': list_name,
                'item_type': item_type,
                'user': user,
                'slug': slug,
                'paginate_start': paginate_start,
                'new_page': next_page,
            },
            f'Next Page ({next_page}) >>',
            icon=NEXTPAGE_ICON,
            is_folder=True,
        ))

    add_items(handle, kodi_items)

    content = max(counts, key=counts.get) if any(counts.values()) else 'movies'
    set_content(handle, content)
    set_category(handle, list_name)
    end_directory(handle, cache_to_disc=not is_external)
    if not is_external:
        set_view_mode(f'view.{content}', content, is_external)


def _norm_user(user):
    return (user or '').lower().replace(' ', '_')


def _filter_lists_by_section(lists_data, section):
    if section == 'my_lists':
        return [
            item for item in lists_data
            if (_norm_user(item.get('user')) not in ('trakt', 'tmdb', 'simkl', 'punchplay', 'orac_local')
                and item.get('source') != 'local')
            or _norm_user(item.get('user')) == 'external_index'
        ]
    if section == 'orac_local':
        return [
            item for item in lists_data
            if _norm_user(item.get('user')) == 'orac_local' or item.get('source') == 'local'
        ]
    if section in ('trakt', 'tmdb', 'simkl', 'punchplay'):
        return [item for item in lists_data if _norm_user(item.get('user')) == section]
    return lists_data


def manager_categories(handle, params):
    kodi_items = [make_dir_item(
        {'mode': 'lists.manager_window', 'section': 'all', 'category_name': 'All Lists'},
        '[COLOR dodgerblue][B]Lists Manager (Interactive Dialog)[/B][/COLOR]',
        icon='trakt',
        is_folder=False,
    )]
    categories = [
        ('My Lists', 'my_lists'),
        ('Orac Local', 'orac_local'),
        ('Trakt Lists', 'trakt'),
        ('TMDB Lists', 'tmdb'),
        ('Simkl Lists', 'simkl'),
        ('PunchPlay Lists', 'punchplay'),
    ]
    for label, section in categories:
        cm = [(
            '[B]Open in Lists Manager Dialog[/B]',
            RUN_PLUGIN % build_url({'mode': 'lists.manager_window', 'section': section, 'category_name': label}),
        )]
        kodi_items.append(make_dir_item(
            {'mode': 'lists.manager_filtered', 'section': section, 'category_name': label},
            label,
            icon='trakt',
            is_folder=True,
            cm_items=cm,
        ))
    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, 'Lists Manager')
    set_sort_method(handle, 'none')
    end_directory(handle)
    set_view_mode('main', 'files')


def manager_filtered(handle, params):
    section = params.get('section', 'my_lists')
    category_name = params.get('category_name', 'Lists')
    try:
        client = get_orac_client()
        lists_data = client.get_lists({'name': 'my_lists', 'item_type': 'all', 'exclude_empty': 'false'}) or []
    except OracClientError as exc:
        _handle_orac_error(handle, exc)
        return

    lists_data = _filter_lists_by_section(lists_data, section)
    current_user = trakt_user()
    kodi_items = []

    for entry in lists_data:
        name = entry.get('name') or entry.get('title') or entry.get('slug') or 'Unnamed List'
        slug = entry.get('slug') or name
        user = entry.get('user') or ''
        owner = entry.get('owner') or user
        source = (entry.get('source') or '').lower()
        item_type = entry.get('item_type', 'movie')
        in_lib = bool(entry.get('add_to_library', False))
        color = _SOURCE_COLORS.get(source, 'FFADD8E6')
        display_name = ' '.join(w.capitalize() for w in name.split())
        item_count = entry.get('item_count', 0)
        status_tag = '[COLOR lime][In Library][/COLOR]' if in_lib else '[COLOR orange][Not in Library][/COLOR]'
        label = f'[COLOR {color}]{display_name}[/COLOR] {status_tag} [I]({owner}) (x{item_count})[/I]'

        update_val = 'Remove' if in_lib else 'Add'
        toggle_label = 'Remove from Library' if in_lib else 'Add to Library'
        cm = [(
            f'[B]{toggle_label}[/B]',
            RUN_PLUGIN % build_url({
                'mode': 'lists.toggle_library',
                'update': update_val,
                'list_name': name,
                'user': user,
                'slug': slug,
                'item_type': item_type,
            }),
        )]
        if source == 'trakt' and user not in ('trakt', current_user):
            cm.append((
                '[B]Unlike List[/B]',
                RUN_PLUGIN % build_url({
                    'mode': 'lists.unlike',
                    'list_name': name,
                    'user': user,
                    'slug': slug,
                }),
            ))
        kodi_items.append(make_dir_item(
            {
                'mode': 'lists.build_list',
                'list_type': 'my_lists',
                'list_name': name,
                'item_type': item_type,
                'user': owner,
                'slug': slug,
            },
            label,
            icon=_SOURCE_ICONS.get(source, 'trakt'),
            is_folder=True,
            cm_items=cm,
        ))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, category_name)
    set_sort_method(handle, 'none')
    end_directory(handle)
    set_view_mode('main', 'files')


def manager_window(handle, params):
    from windows.lists_manager import ListsManager

    section = params.get('section', 'all')
    category_name = params.get('category_name', 'All Lists')
    try:
        client = get_orac_client()
        lists_data = client.get_lists({'name': 'my_lists', 'item_type': 'all', 'exclude_empty': 'false'}) or []
    except OracClientError as exc:
        notification(f'Failed to load lists: {exc}')
        return

    filtered = _filter_lists_by_section(lists_data, section)
    if not filtered:
        notification(f'No lists found in {category_name}')
        return

    selected = ListsManager('lists_manager.xml', lists=filtered, category_name=category_name).run()
    if not selected:
        return
    url = build_url({
        'mode': 'lists.build_list',
        'list_type': 'my_lists',
        'list_name': selected.get('name', 'List'),
        'item_type': selected.get('item_type', 'null'),
        'user': selected.get('owner') or selected.get('user', ''),
        'slug': selected.get('slug') or selected.get('name', ''),
    })
    container_update(url)


def toggle_library(handle, params):
    try:
        client = get_orac_client()
        res = client.update_list_library_status({
            'name': 'update_library_status',
            'list_name': params.get('list_name', ''),
            'user': params.get('user', ''),
            'slug': params.get('slug', ''),
            'item_type': params.get('item_type', 'movie'),
            'update': params.get('update', 'Add'),
        }) or {}
        if res.get('status') == 'success':
            notification('Library updated')
            container_refresh()
        else:
            notification(f'Failed to update library: {res.get("message", "Unknown error")}')
    except OracClientError as exc:
        notification(f'Failed to update library: {exc}')


def unlike_list(handle, params):
    list_name = params.get('list_name', '')
    try:
        res = get_orac_client().unlike_trakt_list({
            'name': 'unlike_trakt_list',
            'list_name': list_name,
            'user': params.get('user', ''),
            'slug': params.get('slug', ''),
        }) or {}
        if res.get('status') == 'success':
            notification(f"Unliked '{list_name}'")
            container_refresh()
        else:
            notification(f"Failed to unlike '{list_name}'")
    except OracClientError as exc:
        notification(f'Failed to unlike list: {exc}')


def manager_choice(handle, params):
    tmdb_id = params.get('tmdb_id')
    media_type = params.get('media_type', 'movie')
    if not tmdb_id:
        return

    action_idx = dialog_select('Orac Lists Manager', ['Add To Orac List...', 'Remove From Orac List...'])
    if action_idx < 0:
        return
    is_add = action_idx == 0

    try:
        client = get_orac_client()
        req = {'item_type': media_type, 'tmdb_id': tmdb_id}
        options = (client.add_list_options(req) if is_add else client.remove_list_options(req)) or []
        if not options:
            notification('No lists available.')
            return
        labels = [
            f"[B]({opt.get('source', 'trakt')})[/B] {opt.get('name', opt.get('slug', 'List')).upper()}"
            for opt in options
        ]
        idx = dialog_select('Select Orac List', labels)
        if idx < 0:
            return
        chosen = options[idx]
        payload = {
            'tmdb_id': tmdb_id,
            'user': chosen.get('user', ''),
            'slug': chosen.get('slug', ''),
            'list_name': chosen.get('name', ''),
            'item_type': media_type,
            'source': chosen.get('source', 'trakt'),
        }
        res = (client.add_to_list(payload) if is_add else client.remove_from_list(payload)) or {}
        if res.get('status') == 'success':
            verb = 'Added to' if is_add else 'Removed from'
            notification(f"{verb} '{chosen.get('name', 'list')}'")
        else:
            notification(f"Failed: {res.get('message', 'Unknown error')}")
    except OracClientError as exc:
        notification(f'Orac error: {exc}')


def force_sync(handle, params):
    try:
        client = get_orac_client()
        client.force_sync()
        notification('Orac sync triggered.')
    except OracClientError as exc:
        notification(f'Force sync failed: {exc}')
