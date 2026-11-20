# -*- coding: utf-8 -*-
import json
from core.kodi import (
    add_dir,
    add_items,
    end_directory,
    external,
    get_property,
    logger,
    notification,
    set_category,
    set_content,
    set_property,
    set_view_mode,
)
from orac.client import OracClientError, get_orac_client
from orac.infotagger import build_movie_item

RECS_CACHE_PROP = 'liberator2.recommendations.cache'


def _fetch_recommendations():
    cached = get_property(RECS_CACHE_PROP)
    if cached:
        try:
            return json.loads(cached)
        except ValueError:
            pass
    data = get_orac_client().get_movie_recommendations()
    if data:
        set_property(RECS_CACHE_PROP, json.dumps(data))
    return data


def movies(handle, params):
    try:
        data = _fetch_recommendations()
    except OracClientError as exc:
        logger('Recommendations', f'Error fetching recommendations: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    if not data:
        notification('No recommendations found')
        end_directory(handle, cache_to_disc=False)
        return

    add_dir(handle, {'mode': 'recommendations.shelf', 'action': 'top_picks', 'name': 'Top Picks'}, 'Top Picks', icon='trending')
    for idx, shelf_obj in enumerate(data.get('genre_shelves', [])):
        title = shelf_obj.get('title', f'Genre {idx + 1}')
        add_dir(
            handle,
            {'mode': 'recommendations.shelf', 'action': 'genre_shelf', 'index': str(idx), 'name': title},
            title,
            icon='genres',
        )

    set_content(handle, 'files')
    set_category(handle, 'Recommendations')
    end_directory(handle)
    set_view_mode('main', 'files')


def shelf(handle, params):
    action = params.get('action', 'top_picks')
    index = int(params.get('index', '-1'))
    name = params.get('name', 'Recommendations')

    try:
        data = _fetch_recommendations() or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    if action == 'top_picks':
        items_data = data.get('top_picks', [])
    elif action == 'genre_shelf' and index >= 0:
        shelves = data.get('genre_shelves', [])
        items_data = shelves[index].get('items', []) if index < len(shelves) else []
    else:
        items_data = []

    is_ext = external()
    kodi_items = [i for i in (build_movie_item(m, is_external=is_ext) for m in items_data) if i]
    add_items(handle, kodi_items)
    set_content(handle, 'movies')
    set_category(handle, name)
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode('view.movies', 'movies', is_ext)
