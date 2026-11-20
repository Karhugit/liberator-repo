# -*- coding: utf-8 -*-
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    add_items,
    end_directory,
    external,
    logger,
    notification,
    set_category,
    set_content,
    set_view_mode,
)
from core.settings import (
    default_all_episodes,
    nextep_include_unaired,
    nextep_sort_descending,
    nextep_sort_key,
    show_specials,
    trakt_user,
)
from orac.client import OracClientError, get_orac_client
from orac.infotagger import build_episode_item, build_season_item


def _show_meta_dict(show_data, tmdb_id):
    return {
        'show_tmdb_id': tmdb_id,
        'show_title': show_data.get('title', ''),
        'show_poster': show_data.get('poster_path') or EMPTY_POSTER,
        'show_fanart': show_data.get('fanart_path') or FANART_PATH,
        'show_clearlogo': show_data.get('clearlogo_path', ''),
        'show_landscape': show_data.get('landscape_path', ''),
    }


def seasons(handle, params):
    tmdb_id = params.get('tmdb_id')
    if not tmdb_id:
        end_directory(handle, cache_to_disc=False)
        return

    try:
        client = get_orac_client()
        show_data = client.get_show_details({'tmdb_id': tmdb_id, 'user': trakt_user()})
    except OracClientError as exc:
        logger('TV', f'Error fetching show {tmdb_id}: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    if not show_data:
        end_directory(handle, cache_to_disc=False)
        return

    season_list = show_data.get('seasons', [])
    if not show_specials():
        season_list = [s for s in season_list if s.get('season', 1) != 0]
    season_list.sort(key=lambda s: (s.get('season', 1) == 0, s.get('season', 1)))

    all_eps_mode = default_all_episodes()
    if all_eps_mode == 2 or (all_eps_mode == 1 and len(season_list) == 1):
        _render_episodes_from_show(handle, show_data, tmdb_id, season_filter=None)
        return

    is_ext = external()
    show_meta = _show_meta_dict(show_data, tmdb_id)
    kodi_items = [build_season_item(s, show_meta) for s in season_list]
    add_items(handle, kodi_items)
    set_content(handle, 'seasons')
    set_category(handle, show_data.get('title', 'Seasons'))
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode('view.seasons', 'seasons', is_ext)


def episodes(handle, params):
    tmdb_id = params.get('tmdb_id')
    if not tmdb_id:
        end_directory(handle, cache_to_disc=False)
        return

    try:
        client = get_orac_client()
        show_data = client.get_show_details({'tmdb_id': tmdb_id, 'user': trakt_user()})
    except OracClientError as exc:
        logger('TV', f'Error fetching episodes for {tmdb_id}: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    if not show_data:
        end_directory(handle, cache_to_disc=False)
        return

    season_param = params.get('season')
    season_filter = None
    if season_param and season_param != 'all':
        try:
            season_filter = int(season_param)
        except (ValueError, TypeError):
            season_filter = None

    _render_episodes_from_show(handle, show_data, tmdb_id, season_filter=season_filter)


def _render_episodes_from_show(handle, show_data, tmdb_id, season_filter=None):
    all_seasons = show_data.get('seasons', [])
    if season_filter is not None:
        seasons_to_use = [s for s in all_seasons if s.get('season') == season_filter]
    elif not show_specials():
        seasons_to_use = [s for s in all_seasons if s.get('season') != 0]
    else:
        seasons_to_use = all_seasons

    show_meta = _show_meta_dict(show_data, tmdb_id)
    kodi_items = []
    for season_obj in seasons_to_use:
        for ep in season_obj.get('episodes', []):
            kodi_items.append(build_episode_item(ep, show_meta=show_meta, include_show_prefix=False))

    is_ext = external()
    add_items(handle, kodi_items)
    set_content(handle, 'episodes')
    set_category(handle, show_data.get('title', 'Episodes'))
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode('view.episodes', 'episodes', is_ext)


def next_episodes(handle, params):
    try:
        client = get_orac_client()
        episodes_data = client.get_next_episodes({
            'include_unaired': 'true' if nextep_include_unaired() else 'false'
        }) or []
    except OracClientError as exc:
        logger('TV', f'Error fetching next episodes: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    if not show_specials():
        episodes_data = [ep for ep in episodes_data if ep.get('season') != 0]

    sort_key = nextep_sort_key()
    reverse = nextep_sort_descending()
    if sort_key == 'last_played':
        episodes_data.sort(key=lambda ep: ep.get('last_watched_at') or '', reverse=reverse)
    elif sort_key == 'first_aired':
        episodes_data.sort(key=lambda ep: ep.get('air_date') or '', reverse=reverse)
    elif sort_key == 'name':
        episodes_data.sort(
            key=lambda ep: (ep.get('show_title') or ep.get('title') or '').lower(),
            reverse=reverse,
        )

    kodi_items = [build_episode_item(ep, include_show_prefix=True) for ep in episodes_data]
    add_items(handle, kodi_items)
    set_content(handle, 'episodes')
    set_category(handle, params.get('category_name', 'Next Episodes'))
    end_directory(handle, cache_to_disc=False)
    set_view_mode('view.episodes', 'episodes')
