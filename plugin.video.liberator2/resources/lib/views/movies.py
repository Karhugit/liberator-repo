# -*- coding: utf-8 -*-
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    add_items,
    build_url,
    end_directory,
    external,
    logger,
    make_listitem,
    notification,
    set_category,
    set_content,
    set_view_mode,
)
from orac.client import OracClientError, get_orac_client
from orac.infotagger import build_movie_item


def collections(handle, params):
    collection_id = params.get('collection_id')
    try:
        data = get_orac_client().get_collections() or {}
    except OracClientError as exc:
        logger('Movies', f'Collections error: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    is_ext = external()
    col_list = data.get('collections', []) if isinstance(data, dict) else data

    if not collection_id:
        col_items = []
        for col in col_list:
            col_id = str(col.get('id', ''))
            col_name = col.get('name') or col.get('title') or 'Collection'
            movies = col.get('movies') or col.get('parts') or []
            label = f'{col_name} [I](x{len(movies)})[/I]'
            poster = col.get('poster_path') or EMPTY_POSTER
            fanart = col.get('backdrop_path') or FANART_PATH

            li = make_listitem(label)
            li.setArt({'poster': poster, 'thumb': poster, 'icon': poster, 'fanart': fanart})
            url = build_url({'mode': 'movies.collections', 'collection_id': col_id, 'name': col_name})
            col_items.append((url, li, True))

        add_items(handle, col_items)
        set_content(handle, 'files')
        set_category(handle, 'Collections')
        end_directory(handle)
        set_view_mode('main', 'files', is_ext)
        return

    selected_col = next((c for c in col_list if str(c.get('id', '')) == str(collection_id)), None)
    items_list = (selected_col.get('movies') or selected_col.get('parts') or []) if selected_col else []
    kodi_items = [i for i in (build_movie_item(m, is_external=is_ext) for m in items_list) if i]
    add_items(handle, kodi_items)
    set_content(handle, 'movies')
    set_category(handle, params.get('name', 'Collection'))
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode('view.movies', 'movies', is_ext)
