# -*- coding: utf-8 -*-
import json
from core.kodi import (
    add_dir,
    add_items,
    build_url,
    container_refresh,
    dialog_confirm,
    dialog_input,
    dialog_select,
    end_directory,
    external,
    logger,
    notification,
    set_category,
    set_content,
    set_view_mode,
)
from orac.client import OracClientError, get_orac_client
from orac.infotagger import build_episode_item, build_movie_item, build_tvshow_item

RUN_PLUGIN = 'RunPlugin(%s)'


def internal(handle, params):
    item_type = params.get('item_type', 'movie')
    add_dir(handle, {'mode': 'indexer.internal_create', 'item_type': item_type}, '[B]+ Create New Index[/B]', icon='new', is_folder=False)

    try:
        resp = get_orac_client().get_internal_indexes({'item_type': item_type}) or {}
    except OracClientError as exc:
        logger('Indexer', f'Internal indexes error: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    indexes = resp.get('indexes', []) if resp.get('success') else []
    for idx in indexes:
        idx_id = idx.get('id', 'Unnamed Index')
        p_dict = idx.get('parameters', {})
        is_random = p_dict.get('sort_by') == 'random' or p_dict.get('sort_by_tv') == 'random'
        cm = [(
            '[B]Delete Index[/B]',
            RUN_PLUGIN % build_url({'mode': 'indexer.internal_delete', 'index_id': idx_id, 'item_type': item_type}),
        )]
        add_dir(
            handle,
            {
                'mode': 'indexer.internal_view',
                'index_id': idx_id,
                'item_type': item_type,
                'is_random': 'true' if is_random else 'false',
            },
            idx_id,
            icon='lists',
            is_folder=True,
            cm_items=cm,
        )

    set_content(handle, 'files')
    set_category(handle, f'{item_type.title()} Indexes')
    end_directory(handle)
    set_view_mode('main', 'files')


def internal_create(handle, params):
    item_type = params.get('item_type', 'movie')
    name = dialog_input('Index Name').strip()
    if not name:
        return
    try:
        client = get_orac_client()
        genres_resp = client.get_genres({'media_type': 'tv' if item_type == 'tvshow' else 'movie'}) or {}
        genres = genres_resp if isinstance(genres_resp, list) else genres_resp.get('genres', [])
        genre_names = [g.get('name', g) if isinstance(g, dict) else str(g) for g in genres]
        selected_genre = ''
        if genre_names:
            g_idx = dialog_select('Optional Genre Filter (Cancel for All)', genre_names)
            if g_idx >= 0:
                selected_genre = genre_names[g_idx]

        sort_options = ['popularity', 'rating', 'release_date', 'random']
        s_idx = dialog_select('Sort By', sort_options)
        sort_by = sort_options[s_idx] if s_idx >= 0 else 'popularity'

        payload = {
            'id': name,
            'item_type': item_type,
            'parameters': {
                'sort_by_tv' if item_type == 'tvshow' else 'sort_by': sort_by,
            },
        }
        if selected_genre:
            payload['parameters']['genres'] = [selected_genre]

        client.add_internal_index(payload)
        notification(f'Created index: {name}')
        container_refresh()
    except OracClientError as exc:
        notification(f'Failed to create index: {exc}')


def internal_delete(handle, params):
    index_id = params.get('index_id')
    item_type = params.get('item_type', 'movie')
    if not index_id:
        return
    if not dialog_confirm('Delete Index', f'Delete index [B]{index_id}[/B]?'):
        return
    try:
        get_orac_client().delete_internal_index({'index_id': index_id, 'item_type': item_type})
        notification(f'Deleted {index_id}')
        container_refresh()
    except OracClientError as exc:
        notification(f'Delete failed: {exc}')


def internal_view(handle, params):
    index_id = params.get('index_id')
    item_type = params.get('item_type', 'movie')
    is_random = params.get('is_random') == 'true'
    if not index_id:
        end_directory(handle, cache_to_disc=False)
        return

    try:
        resp = get_orac_client().internal_index_contents({'index_id': index_id, 'item_type': item_type}) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    rows = resp.get('results', []) if resp.get('success') else []
    is_ext = external()
    kodi_items = []
    for raw in rows:
        if item_type == 'movie':
            built = build_movie_item(raw, is_external=is_ext)
        elif item_type == 'tvshow':
            built = build_tvshow_item(raw, is_external=is_ext)
        else:
            built = build_episode_item(raw, include_show_prefix=True)
        if built:
            kodi_items.append(built)

    add_items(handle, kodi_items)
    content = 'tvshows' if item_type == 'tvshow' else ('movies' if item_type == 'movie' else 'episodes')
    set_content(handle, content)
    set_category(handle, index_id)
    end_directory(handle, cache_to_disc=not (is_ext or is_random))
    set_view_mode(f'view.{content}', content, is_ext)


def external_list(handle, params):
    media_type = params.get('media_type', 'movie')
    try:
        resp = get_orac_client().get_external_indexes({'media_type': media_type}) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    indexes = resp.get('indexes', []) if isinstance(resp, dict) else resp
    for idx in indexes:
        name = idx.get('id', 'Unnamed')
        is_random = '[random]' in json.dumps(idx.get('parameters', {}))
        cm = [(
            '[B]Delete Index[/B]',
            RUN_PLUGIN % build_url({'mode': 'indexer.external_delete', 'name': name, 'media_type': media_type}),
        )]
        add_dir(
            handle,
            {
                'mode': 'indexer.external_discover',
                'media_type': media_type,
                'name': name,
                'is_random': 'true' if is_random else 'false',
            },
            name,
            icon='discover',
            is_folder=True,
            cm_items=cm,
        )

    set_content(handle, 'files')
    set_category(handle, f'Discover ({media_type.title()})')
    end_directory(handle)
    set_view_mode('main', 'files')


def external_discover(handle, params):
    media_type = params.get('media_type', 'movie')
    name = params.get('name', '')
    is_random = params.get('is_random') == 'true'
    if not name:
        end_directory(handle, cache_to_disc=False)
        return

    try:
        client = get_orac_client()
        rows = (client.discover_tvshow({'name': name}) if media_type == 'tvshow' else client.discover_movie({'name': name})) or []
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    is_ext = external()
    kodi_items = []
    for raw in rows:
        built = build_tvshow_item(raw, is_external=is_ext) if media_type == 'tvshow' else build_movie_item(raw, is_external=is_ext)
        if built:
            kodi_items.append(built)

    add_items(handle, kodi_items)
    content = 'tvshows' if media_type == 'tvshow' else 'movies'
    set_content(handle, content)
    set_category(handle, name)
    end_directory(handle, cache_to_disc=not (is_ext or is_random))
    set_view_mode(f'view.{content}', content, is_ext)


def external_delete(handle, params):
    name = params.get('name')
    media_type = params.get('media_type', 'movie')
    if not name:
        return
    try:
        get_orac_client().delete_external_index({'id': name, 'media_type': media_type})
        notification(f'Removed {name}')
        container_refresh()
    except OracClientError as exc:
        notification(f'Failed to remove index: {exc}')
