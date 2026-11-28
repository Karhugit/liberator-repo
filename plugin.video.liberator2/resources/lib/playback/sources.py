# -*- coding: utf-8 -*-
from datetime import date
import math
import threading
import time
from urllib.parse import unquote, urlsplit
import requests
import xbmc
import xbmcplugin
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    clear_property,
    logger,
    make_listitem,
    notification,
    play_trailer,
)
from core.settings import autoplay_enabled, strict_dedupe, trakt_user, use_local_files
from orac.client import OracClientError, get_orac_client
from playback.player import PLAYBACK_META_PROP, play_and_verify
from windows.sources import SourcesPlayback, SourcesResults

QUALITY_RANK = {'4k': 4, '2160p': 4, '1080p': 3, '720p': 2, 'sd': 1}


def _fail_resolve(handle):
    if handle >= 0:
        xbmcplugin.setResolvedUrl(handle, False, make_listitem())


def _is_future_date(raw_date):
    date_str = str(raw_date or '').strip()[:10]
    return len(date_str) == 10 and date_str > date.today().isoformat()


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
            'air_date': ep_data.get('air_date') or ep_data.get('first_aired') or ep_data.get('premiered') or params.get('air_date') or '',
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


def _is_easynews_item(item, url=''):
    provider = str(item.get('cache_provider') or item.get('debrid') or item.get('provider') or '').lower()
    return 'easynews' in provider or 'easynews.com' in str(url or '').lower()


def _probe_easynews_stream(url, head_timeout=(3, 4), tail_timeout=(3, 3)):
    """Pre-flight head + tail-seek probe so stalled Easynews nodes never hang Kodi's VideoPlayer."""
    try:
        parsed = urlsplit(url)
        auth = None
        if parsed.username is not None:
            auth = (unquote(parsed.username), unquote(parsed.password or ''))

        with requests.Session() as sess:
            head_headers = {'Range': 'bytes=0-65535', 'User-Agent': 'Mozilla/5.0'}
            total_size = 0
            final_url = url
            with sess.get(url, headers=head_headers, stream=True, timeout=head_timeout) as resp:
                if resp.status_code not in (200, 206):
                    logger('Sources', f'Easynews head probe HTTP {resp.status_code}')
                    return False
                chunk = next(resp.iter_content(chunk_size=16384), b'')
                if not chunk:
                    logger('Sources', 'Easynews head probe returned empty EOF')
                    return False
                resp_headers = getattr(resp, 'headers', {}) or {}
                cr = resp_headers.get('Content-Range', '')
                if '/' in cr:
                    total_str = cr.rsplit('/', 1)[-1].strip()
                    if total_str.isdigit():
                        total_size = int(total_str)
                elif resp.status_code == 200:
                    try:
                        total_size = int(resp_headers.get('Content-Length') or 0)
                    except (ValueError, TypeError):
                        total_size = 0
                final_url = getattr(resp, 'url', None) or url

            # Probe tail (MKV Cues region) to catch nodes that accept headers/head then stall on seek
            if total_size > 131072:
                tail_start = total_size - 32768
                tail_end = total_size - 1
                tail_headers = {'Range': f'bytes={tail_start}-{tail_end}', 'User-Agent': 'Mozilla/5.0'}
                target_url = final_url if (auth or '@' in final_url) else url
                req_auth = auth if (auth and '@' not in target_url) else None
                try:
                    with sess.get(target_url, headers=tail_headers, auth=req_auth, stream=True, timeout=tail_timeout) as resp2:
                        if resp2.status_code not in (200, 206):
                            logger('Sources', f'Easynews tail-seek probe failed (HTTP {resp2.status_code})')
                            return False
                        chunk2 = next(resp2.iter_content(chunk_size=16384), b'')
                        if not chunk2:
                            logger('Sources', 'Easynews tail-seek probe failed (empty EOF)')
                            return False
                except Exception as exc2:
                    logger('Sources', f'Easynews tail-seek probe failed: {exc2}')
                    return False
            return True
    except requests.RequestException as exc:
        logger('Sources', f'Easynews probe failed: {exc}')
        return False
    except Exception as exc:
        logger('Sources', f'Easynews probe unexpected error: {exc}')
        return False


def _resolve_source(client, item, meta):
    url = item.get('url', '')
    if url.startswith('/'):
        return f'{client.base_url}{url}'
    if url.startswith(('http://', 'https://')) and (item.get('direct') or not item.get('hash')):
        if _is_easynews_item(item, url):
            if not _probe_easynews_stream(url):
                return None
            return url if '|' in url else f'{url}|connection-timeout=6'
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

    try:
        res = client.resolve(resolve_params) or {}
    except OracClientError as exc:
        logger('Sources', f'Resolve failed for {resolve_params.get("provider")}: {exc}')
        return None
    if res.get('success') and res.get('stream_url'):
        return res['stream_url']
    return None


def _build_playback_queue(results, chosen=None):
    cached = [r for r in results if 'Uncached' not in r.get('cache_provider', '')]
    if chosen is None:
        return cached

    chosen_idx = None
    for idx, item in enumerate(cached):
        if item == chosen:
            chosen_idx = idx
            break
    if chosen_idx is None:
        chosen_sig = (chosen.get('url', ''), chosen.get('hash', ''), chosen.get('name', ''))
        for idx, item in enumerate(cached):
            if (item.get('url', ''), item.get('hash', ''), item.get('name', '')) == chosen_sig:
                chosen_idx = idx
                break

    if chosen_idx is None:
        return [chosen] + cached

    items_prev = list(reversed(cached[:chosen_idx]))
    items_next = cached[chosen_idx + 1:]
    return [cached[chosen_idx]] + items_next + items_prev


def _format_resolve_display(idx, total, item):
    provider = (item.get('cache_provider') or item.get('debrid') or item.get('provider') or 'ORAC')
    provider = str(provider).replace('.me', '').upper()
    quality = str(item.get('quality') or 'SD').upper()
    size_label = item.get('size_label') or ''
    if not size_label and item.get('size'):
        try:
            size_label = f'{float(item["size"]):.2f} GB'
        except (ValueError, TypeError):
            size_label = ''
    extra = item.get('extraInfo') or item.get('info') or ''
    parts = [f'[B]{quality}[/B]']
    if size_label:
        parts.append(f'[B]{size_label}[/B]')
    if extra:
        parts.append(str(extra))
    name = str(item.get('display_name') or item.get('name') or 'Unknown Source').upper()
    return f'{idx:02d}/{total:02d}  [B]{provider}[/B][CR]{" | ".join(parts)}[CR]{name}'


def play(handle, params):
    media_type = params.get('media_type', 'movie')
    tmdb_id = params.get('tmdb_id')
    force_select = params.get('force_select') == 'true'
    force_direct_play = params.get('direct_play') == 'true' or handle < 0
    handle_used = False

    if not tmdb_id:
        notification('Missing TMDB ID for playback')
        _fail_resolve(handle)
        return

    if media_type == 'episode' and _is_future_date(params.get('air_date')):
        notification('Please wait for release date!')
        _fail_resolve(handle)
        return

    splash = None
    try:
        client = get_orac_client()
        meta = _build_meta(client, media_type, tmdb_id, params)

        if media_type == 'episode' and _is_future_date(meta.get('air_date')):
            notification('Please wait for release date!')
            _fail_resolve(handle)
            return

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
        monitor = xbmc.Monitor()
        while worker.is_alive():
            if splash.is_canceled or monitor.abortRequested():
                splash.close()
                splash = None
                _fail_resolve(handle)
                return
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
        is_autoplay = autoplay_enabled(media_type) and not force_select

        if is_autoplay:
            queue = _build_playback_queue(results)
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
            queue = _build_playback_queue(results, chosen=chosen)
            splash = SourcesPlayback('sources_playback.xml', meta=meta)
            splash.show()
            xbmc.sleep(50)

        if not queue:
            if splash:
                splash.close()
                splash = None
            notification('No playable sources available.')
            _fail_resolve(handle)
            return

        splash.set_resolver_mode()
        splash.reset_cancel()
        total = len(queue)
        cancelled = False

        for idx, candidate in enumerate(queue, 1):
            if splash.is_canceled or monitor.abortRequested():
                cancelled = True
                break

            splash.reset_skip()
            splash.set_busy_spinner(True)
            is_en = _is_easynews_item(candidate, candidate.get('url', ''))
            probe_msg = 'Checking Easynews stream...' if is_en else 'Resolving source...'
            splash.update_resolver(
                text=_format_resolve_display(idx, total, candidate),
                percent=0,
                status_text=probe_msg,
            )

            resolve_box = {'url': None}

            def _do_resolve(target=candidate):
                resolve_box['url'] = _resolve_source(client, target, meta)

            r_start = time.time()
            probe_window = 7.0
            r_worker = threading.Thread(target=_do_resolve, daemon=True)
            r_worker.start()
            skipped_resolve = False
            while r_worker.is_alive():
                if splash.is_canceled or monitor.abortRequested():
                    cancelled = True
                    break
                if splash.skip_requested:
                    skipped_resolve = True
                    break
                if is_en:
                    elapsed = time.time() - r_start
                    rem = max(0, int(math.ceil(probe_window - elapsed)))
                    pct = int(min(99, (elapsed / probe_window) * 100))
                    splash.update_resolver(percent=pct, status_text=f'Checking Easynews stream... {rem}s')
                xbmc.sleep(50)

            if cancelled:
                break
            stream_url = resolve_box['url']
            if skipped_resolve or not stream_url:
                logger('Sources', f'Source {idx}/{total} skipped or failed to resolve, trying next source')
                continue

            splash.set_busy_spinner(False)
            splash.update_resolver(percent=0, remaining_seconds=22)
            status, handle_used = play_and_verify(
                handle,
                stream_url,
                meta,
                splash=splash,
                handle_used=handle_used,
                force_direct_play=force_direct_play,
                timeout_seconds=22.0,
            )
            if status == 'started':
                splash.close()
                splash = None
                return
            if status == 'cancelled':
                cancelled = True
                break
            logger('Sources', f'Source {idx}/{total} failed ({status}), trying next source')

        if splash:
            splash.close()
            splash = None
        clear_property(PLAYBACK_META_PROP)
        if not handle_used:
            _fail_resolve(handle)
        if not cancelled:
            notification('Failed to play any source.')

    except OracClientError as exc:
        logger('Sources', f'Orac error during playback: {exc}')
        if splash:
            splash.close()
        notification(f'Playback error: {exc}')
        if not handle_used:
            _fail_resolve(handle)
    except Exception as exc:
        logger('Sources', f'Unexpected playback error: {exc}')
        if splash:
            splash.close()
        notification(f'Playback error: {exc}')
        if not handle_used:
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
