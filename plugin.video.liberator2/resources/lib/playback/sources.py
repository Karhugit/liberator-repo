# -*- coding: utf-8 -*-
import threading
import time
import xbmc
import xbmcplugin
from core.kodi import EMPTY_POSTER, FANART_PATH, logger, make_listitem, notification, play_trailer
from core.settings import autoplay_enabled, strict_dedupe, trakt_user, use_local_files
from orac.client import OracClientError, get_orac_client
from playback.player import start_playback
from windows.sources import SourcesPlayback, SourcesResults

QUALITY_RANK = {'4k': 4, '2160p': 4, '1080p': 3, '720p': 2, 'sd': 1}


def _fail_resolve(handle):
    if handle >= 0:
        xbmcplugin.setResolvedUrl(handle, False, make_listitem())


def _build_meta(client, media_type, tmdb_id, params):
    season = params.get('season')
    episode = params.get('episode')
    meta = {
        'media_type': media_type,
        'tmdb_id': tmdb_id,
        'title': params.get('title', ''),
        'year': params.get('year', ''),
        'poster': EMPTY_POSTER,
        'fanart': FANART_PATH,
        'clearlogo': '',
        'overview': '',
    }
    if params.get('anilist_id'):
        meta['anilist_id'] = str(params['anilist_id'])
    if params.get('absolute_episode') or params.get('abs_ep'):
        meta['absolute_episode'] = str(params.get('absolute_episode') or params.get('abs_ep'))

    if media_type == 'movie':
        data = client.get_movie_details({'tmdb_id': tmdb_id, 'user': trakt_user()}) or {}
        meta.update({
            'title': data.get('title') or meta['title'],
            'year': data.get('year') or meta['year'],
            'imdb_id': data.get('imdb_id', ''),
            'tvdb_id': data.get('tvdb_id', 0),
            'poster': data.get('poster_path') or EMPTY_POSTER,
            'fanart': data.get('fanart_path') or FANART_PATH,
            'clearlogo': data.get('clearlogo_path', ''),
            'overview': data.get('overview', ''),
            'genres': data.get('genres', []),
            'resume_point': data.get('percent_watched') or data.get('resume_point') or data.get('progress') or 0,
        })
    else:
        data = client.get_show_details({'tmdb_id': tmdb_id, 'user': trakt_user()}) or {}
        s_num = int(season) if season is not None else 1
        e_num = int(episode) if episode is not None else 1
        ep_data = {}
        next_ep = None
        flat_eps = []
        for s_obj in data.get('seasons', []):
            for ep in s_obj.get('episodes', []):
                flat_eps.append((
                    int(ep.get('season') if ep.get('season') is not None else ep.get('season_number', s_obj.get('season', 1))),
                    int(ep.get('episode_number') if ep.get('episode_number') is not None else ep.get('episode', 1)),
                    ep,
                ))
        flat_eps.sort(key=lambda x: (x[0], x[1]))
        for idx, (sn, en, ep) in enumerate(flat_eps):
            if sn == s_num and en == e_num:
                ep_data = ep
                if idx + 1 < len(flat_eps):
                    ns, ne, nep = flat_eps[idx + 1]
                    next_ep = {
                        'tmdb_id': tmdb_id,
                        'title': data.get('title') or meta['title'],
                        'season': ns,
                        'episode': ne,
                        'ep_name': nep.get('episode_title') or nep.get('title') or f'Episode {ne}',
                        'ep_thumb': nep.get('episode_thumbnail_path', ''),
                        'fanart': data.get('fanart_path') or FANART_PATH,
                        'clearlogo': data.get('clearlogo_path', ''),
                    }
                break

        meta.update({
            'title': data.get('title') or meta['title'],
            'year': data.get('year') or meta['year'],
            'imdb_id': data.get('imdb_id', ''),
            'tvdb_id': data.get('tvdb_id', 0),
            'total_seasons': data.get('total_seasons') or len(data.get('seasons', [])) or 1,
            'season': s_num,
            'episode': e_num,
            'ep_name': ep_data.get('episode_title') or ep_data.get('title') or f'Episode {e_num}',
            'ep_thumb': ep_data.get('episode_thumbnail_path', ''),
            'air_date': ep_data.get('air_date') or ep_data.get('premiered') or '',
            'poster': data.get('poster_path') or EMPTY_POSTER,
            'fanart': data.get('fanart_path') or FANART_PATH,
            'clearlogo': data.get('clearlogo_path', ''),
            'overview': ep_data.get('episode_overview') or ep_data.get('overview') or data.get('overview', ''),
            'genres': data.get('genres', []),
            'resume_point': ep_data.get('percent_watched') or ep_data.get('resume_point') or ep_data.get('progress') or 0,
            'next_episode': next_ep,
        })
    return meta


def _build_scrape_params(meta):
    params = {
        'media_type': meta['media_type'],
        'item_type': meta['media_type'],
        'title': meta['title'],
        'year': str(meta.get('year') or ''),
        'tmdb_id': meta['tmdb_id'],
        'imdb_id': meta.get('imdb_id', ''),
        'tvdb_id': meta.get('tvdb_id', 0),
        'strict_dedupe': str(strict_dedupe()).lower(),
        'use_local': str(use_local_files()).lower(),
        'orac_scraping': 'true',
    }
    if meta['media_type'] == 'episode':
        params.update({
            'tvshowtitle': meta['title'],
            'season': str(meta['season']),
            'episode': str(meta['episode']),
            'ep_name': meta.get('ep_name', ''),
            'air_date': meta.get('air_date', ''),
            'premiered': meta.get('air_date', ''),
            'total_seasons': meta.get('total_seasons', 1),
        })
    if meta.get('anilist_id'):
        params['anilist_id'] = str(meta['anilist_id'])
    if meta.get('absolute_episode'):
        params['absolute_episode'] = str(meta['absolute_episode'])
        params['abs_ep'] = str(meta['absolute_episode'])
    return params


def _sort_sources(raw_results):
    def sort_key(item):
        is_local = 0 if (item.get('is_local') or item.get('provider') == 'orac_local') else 1
        uncached = 1 if 'Uncached' in item.get('cache_provider', '') else 0
        q_rank = QUALITY_RANK.get((item.get('quality') or 'sd').lower(), 1)
        try:
            size = float(item.get('size', 0) or 0)
        except (ValueError, TypeError):
            size = 0.0
        return (is_local, uncached, -q_rank, -size)

    return sorted(raw_results, key=sort_key)


def _resolve_source(client, item, meta):
    url = item.get('url', '')
    if url.startswith('/'):
        return f'{client.base_url}{url}'
    if url.startswith(('http://', 'https://')) and not item.get('hash'):
        return url

    resolve_params = {
        'provider': item.get('cache_provider') or item.get('debrid') or item.get('provider') or 'orac',
        'magnet': url,
        'hash': item.get('hash', ''),
        'title': meta.get('title', ''),
    }
    if meta['media_type'] == 'episode':
        resolve_params['season'] = str(meta['season'])
        resolve_params['episode'] = str(meta['episode'])

    res = client.resolve(resolve_params) or {}
    if res.get('success') and res.get('stream_url'):
        return res['stream_url']
    return None


def play(handle, params):
    media_type = params.get('media_type', 'movie')
    tmdb_id = params.get('tmdb_id')
    force_select = params.get('force_select') == 'true'
    force_direct_play = params.get('direct_play') == 'true' or handle < 0

    if not tmdb_id:
        notification('Missing TMDB ID for playback')
        _fail_resolve(handle)
        return

    splash = None
    try:
        client = get_orac_client()
        meta = _build_meta(client, media_type, tmdb_id, params)

        splash = SourcesPlayback('sources_playback.xml', meta=meta)
        splash.show()
        xbmc.sleep(100)
        splash.set_text('Searching Orac for sources...')

        scrape_box = {'resp': None, 'err': None}

        def _do_scrape():
            try:
                scrape_box['resp'] = client.scrape(_build_scrape_params(meta)) or {}
            except Exception as exc:
                scrape_box['err'] = exc

        start_ts = time.time()
        worker = threading.Thread(target=_do_scrape, daemon=True)
        worker.start()
        while worker.is_alive():
            xbmc.sleep(100)
        duration = time.time() - start_ts

        if scrape_box['err']:
            raise scrape_box['err']
        scrape_resp = scrape_box['resp'] or {}

        raw_results = scrape_resp.get('results', []) if scrape_resp.get('success') else []
        if not raw_results:
            splash.close()
            splash = None
            notification('No sources found.')
            _fail_resolve(handle)
            return

        results = _sort_sources(raw_results)
        stream_url = None

        if autoplay_enabled(media_type) and not force_select:
            cached = [r for r in results if 'Uncached' not in r.get('cache_provider', '')]
            for idx, candidate in enumerate(cached[:5], 1):
                splash.set_text(f'Resolving source {idx}/{min(len(cached), 5)}...')
                stream_url = _resolve_source(client, candidate, meta)
                if stream_url:
                    break
        else:
            splash.close()
            splash = None
            action, chosen = SourcesResults(
                'sources_results.xml',
                results=results,
                meta=meta,
                scrape_duration=duration,
            ).run()
            if action != 'play' or not chosen:
                _fail_resolve(handle)
                return
            splash = SourcesPlayback('sources_playback.xml', meta=meta)
            splash.show()
            xbmc.sleep(50)
            splash.set_text('Resolving selected source...')
            stream_url = _resolve_source(client, chosen, meta)

        if splash:
            splash.close()
            splash = None

        if not stream_url:
            notification('Failed to resolve stream.')
            _fail_resolve(handle)
            return

        start_playback(handle, stream_url, meta, force_direct_play=force_direct_play)

    except OracClientError as exc:
        logger('Sources', f'Orac error during playback: {exc}')
        if splash:
            splash.close()
        notification(f'Playback error: {exc}')
        _fail_resolve(handle)
    except Exception as exc:
        logger('Sources', f'Unexpected playback error: {exc}')
        if splash:
            splash.close()
        notification(f'Playback error: {exc}')
        _fail_resolve(handle)


def trailer(handle, params):
    trailer_url = params.get('trailer_url') or ''
    if not trailer_url and params.get('tmdb_id'):
        media_type = params.get('media_type', 'movie')
        try:
            client = get_orac_client()
            if media_type == 'movie':
                data = client.get_movie_details({'tmdb_id': params['tmdb_id'], 'user': trakt_user()}) or {}
            else:
                data = client.get_show_details({'tmdb_id': params['tmdb_id'], 'user': trakt_user()}) or {}
            trailer_url = data.get('trailer') or ''
            if not trailer_url:
                trailers = data.get('all_trailers') or []
                if trailers and isinstance(trailers[0], dict):
                    trailer_url = trailers[0].get('key', '')
        except OracClientError as exc:
            logger('Sources', f'Trailer lookup failed: {exc}')
    play_trailer(trailer_url)
