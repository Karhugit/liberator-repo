# -*- coding: utf-8 -*-
from core.kodi import (
    add_items,
    container_refresh,
    dialog_input,
    dialog_select,
    end_directory,
    external,
    logger,
    make_dir_item,
    notification,
    set_category,
    set_content,
    set_sort_method,
    set_view_mode,
)
from orac.client import OracClientError, get_orac_client
from orac.infotagger import build_movie_item, build_tvshow_item


def menu(handle, params):
    try:
        resp = get_orac_client().get_all_tags(details=True) or {}
    except OracClientError as exc:
        logger('Tags', f'Failed to fetch tags: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    tags = resp.get('tags', []) if resp.get('success') else []
    if not tags:
        notification('No tags found')
        end_directory(handle)
        return

    tag_items = []
    for tag in tags:
        tag_name = tag.get('tag_name', '')
        if not tag_name:
            continue
        movies = tag.get('movie_count', 0)
        shows = tag.get('show_count', 0)
        parts = []
        if movies:
            parts.append(f"{movies} Movie{'s' if movies != 1 else ''}")
        if shows:
            parts.append(f"{shows} Show{'s' if shows != 1 else ''}")
        counts = ', '.join(parts) or 'Empty'
        label = f'{tag_name.capitalize()} [I][COLOR gray]({counts})[/COLOR][/I]'
        tag_items.append(make_dir_item({'mode': 'tags.list', 'tag_name': tag_name}, label, icon='lists', is_folder=True))

    add_items(handle, tag_items)
    set_content(handle, 'files')
    set_category(handle, 'Tag Manager')
    set_sort_method(handle, 'label')
    end_directory(handle)
    set_view_mode('main', 'files')


def list_items(handle, params):
    tag_name = params.get('tag_name', '')
    if not tag_name:
        end_directory(handle, cache_to_disc=False)
        return

    try:
        resp = get_orac_client().get_tag_items(tag_name) or {}
    except OracClientError as exc:
        logger('Tags', f'Failed to fetch items for {tag_name}: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    items = resp.get('items', []) if resp.get('success') else []
    is_ext = external()
    kodi_items = []
    movies_count = 0
    shows_count = 0

    for raw in items:
        mtype = raw.get('media_type') or raw.get('type')
        if mtype == 'movie':
            built = build_movie_item(raw, is_external=is_ext)
            if built:
                kodi_items.append(built)
                movies_count += 1
        elif mtype in ('show', 'tvshow'):
            built = build_tvshow_item(raw, is_external=is_ext)
            if built:
                kodi_items.append(built)
                shows_count += 1

    add_items(handle, kodi_items)
    content = 'tvshows' if shows_count > movies_count else 'movies'
    set_content(handle, content)
    set_category(handle, f'Tag: {tag_name.capitalize()}')
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode(f'view.{content}', content, is_ext)


def add_tag(handle, params):
    media_type = params.get('media_type', 'movie')
    tmdb_id = params.get('tmdb_id')
    if not tmdb_id:
        return

    try:
        client = get_orac_client()
        all_tags_resp = client.get_all_tags(details=False) or {}
        existing = [t.get('tag_name') or t for t in all_tags_resp.get('tags', []) if t]
        options = ['+ Create New Tag'] + existing
        idx = dialog_select('Add Tag', options)
        if idx < 0:
            return
        if idx == 0:
            tag_name = dialog_input('Enter New Tag Name').strip()
        else:
            tag_name = options[idx]
        if not tag_name:
            return
        client.add_tag(media_type, tmdb_id, tag_name)
        notification(f'Added tag: {tag_name}')
        container_refresh()
    except OracClientError as exc:
        notification(f'Failed to add tag: {exc}')


def remove_tag(handle, params):
    media_type = params.get('media_type', 'movie')
    tmdb_id = params.get('tmdb_id')
    if not tmdb_id:
        return

    try:
        client = get_orac_client()
        resp = client.get_tags_for_item(media_type, tmdb_id) or {}
        tags = resp.get('tags', []) if isinstance(resp, dict) else resp
        if not tags:
            notification('No tags on this item')
            return
        idx = dialog_select('Remove Tag', tags)
        if idx < 0:
            return
        tag_name = tags[idx]
        client.remove_tag(media_type, tmdb_id, tag_name)
        notification(f'Removed tag: {tag_name}')
        container_refresh()
    except OracClientError as exc:
        notification(f'Failed to remove tag: {exc}')
