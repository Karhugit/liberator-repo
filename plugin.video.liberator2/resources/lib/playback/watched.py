# -*- coding: utf-8 -*-
from core.kodi import container_refresh, dialog_confirm, logger, notification
from orac.client import OracClientError, get_orac_client


def _calc_percent(params):
    action = params.get('action')
    if action == 'mark_as_unwatched':
        return 0
    curr_time = params.get('curr_time')
    total_time = params.get('total_time')
    if curr_time is not None and total_time is not None and float(total_time) > 0:
        adjusted = max(0.0, float(curr_time) - 5.0)
        pct = round((adjusted / float(total_time)) * 100.0, 1)
        return 100 if pct >= 95 else pct
    return 100


def mark_movie(handle, params):
    tmdb_id = int(params['tmdb_id'])
    req = {'type': 'movie', 'tmdb_id': tmdb_id, 'percent_watched': _calc_percent(params)}
    if params.get('anilist_id'):
        req['anilist_id'] = str(params['anilist_id'])
    try:
        get_orac_client().mark_watched(req)
        if params.get('from_playback') != 'true':
            container_refresh()
    except OracClientError as exc:
        logger('Watched', f'mark_movie failed: {exc}')
        notification(f'Failed to update watched status: {exc}')


def mark_season(handle, params):
    season = int(params['season'])
    if season == 0:
        notification('Cannot mark specials season')
        return
    tmdb_id = int(params['tmdb_id'])
    pct = 0 if params.get('action') == 'mark_as_unwatched' else 100
    try:
        get_orac_client().mark_watched({
            'type': 'season', 'tmdb_id': tmdb_id, 'season': season, 'percent_watched': pct
        })
        container_refresh()
    except OracClientError as exc:
        logger('Watched', f'mark_season failed: {exc}')
        notification(f'Failed to update watched status: {exc}')


def mark_episode(handle, params):
    tmdb_id = int(params['tmdb_id'])
    season = int(params['season'])
    episode = int(params['episode'])
    req = {
        'type': 'episode',
        'tmdb_id': tmdb_id,
        'season': season,
        'episode': episode,
        'percent_watched': _calc_percent(params),
    }
    if params.get('anilist_id'):
        req['anilist_id'] = str(params['anilist_id'])
    try:
        get_orac_client().mark_watched(req)
        if params.get('from_playback') != 'true':
            container_refresh()
    except OracClientError as exc:
        logger('Watched', f'mark_episode failed: {exc}')
        notification(f'Failed to update watched status: {exc}')


def mark_tvshow(handle, params):
    tmdb_id = int(params['tmdb_id'])
    pct = 0 if params.get('action') == 'mark_as_unwatched' else 100
    try:
        get_orac_client().mark_watched({
            'type': 'tvshow', 'tmdb_id': tmdb_id, 'percent_watched': pct
        })
        container_refresh()
    except OracClientError as exc:
        logger('Watched', f'mark_tvshow failed: {exc}')
        notification(f'Failed to update watched status: {exc}')


def drop_tvshow(handle, params):
    tmdb_id = int(params['tmdb_id'])
    title = params.get('title', 'this show')
    if not dialog_confirm('Drop Show', f'Are you sure you want to drop [B]{title}[/B]?'):
        return
    try:
        get_orac_client().drop_tvshow({'type': 'tvshow', 'tmdb_id': tmdb_id})
        notification(f'Dropped {title}')
        container_refresh()
    except OracClientError as exc:
        logger('Watched', f'drop_tvshow failed: {exc}')
        notification(f'Failed to drop show: {exc}')
