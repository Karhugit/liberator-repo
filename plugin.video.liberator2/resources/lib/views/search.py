# -*- coding: utf-8 -*-
from core.kodi import (
    add_items,
    container_update,
    dialog_input,
    end_directory,
    external,
    logger,
    notification,
    set_category,
    set_content,
    set_view_mode,
    build_url,
)
from orac.client import OracClientError, get_orac_client
from orac.infotagger import build_movie_item, build_tvshow_item


def query(handle, params):
    media_type = params.get('media_type', 'movie')
    if media_type == 'people':
        from windows.people import search_people
        search_people(handle, params)
        return
    keyword = params.get('query') or dialog_input(f'Search {media_type.title()}')
    if not keyword:
        return
    url = build_url({'mode': 'search.results', 'media_type': media_type, 'query': keyword})
    container_update(url)


def results(handle, params):
    media_type = params.get('media_type', 'movie')
    keyword = params.get('query', '').strip()
    if not keyword:
        end_directory(handle, cache_to_disc=False)
        return

    item_type = 'tv_show' if media_type == 'tvshow' else media_type
    try:
        items_data = get_orac_client().search_tmdb({'item_type': item_type, 'name': keyword}) or []
    except OracClientError as exc:
        logger('Search', f'Search failed: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    if not items_data:
        notification('No results found')
        end_directory(handle, cache_to_disc=False)
        return

    is_ext = external()
    kodi_items = []
    for raw in items_data:
        built = build_tvshow_item(raw, is_external=is_ext) if media_type == 'tvshow' else build_movie_item(raw, is_external=is_ext)
        if built:
            kodi_items.append(built)

    add_items(handle, kodi_items)
    content = 'tvshows' if media_type == 'tvshow' else 'movies'
    set_content(handle, content)
    set_category(handle, f'Search: {keyword}')
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode(f'view.{content}', content, is_ext)
