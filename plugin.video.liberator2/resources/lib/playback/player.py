# -*- coding: utf-8 -*-
import json
import math
import time
import xbmc
import xbmcplugin
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    clear_property,
    hide_busy_dialog,
    logger,
    make_listitem,
    set_property,
)

PLAYBACK_META_PROP = 'liberator2.playback_meta'


def _build_playback_listitem(stream_url, meta):
    media_type = meta.get('media_type', 'movie')
    title = meta.get('title') or 'Liberator 2'

    li = make_listitem(title)
    li.setPath(stream_url)
    li.setArt({
        'poster': meta.get('poster') or EMPTY_POSTER,
        'fanart': meta.get('fanart') or FANART_PATH,
        'thumb': meta.get('ep_thumb') or meta.get('poster') or EMPTY_POSTER,
        'clearlogo': meta.get('clearlogo') or '',
    })

    info_tag = li.getVideoInfoTag()
    info_tag.setMediaType('episode' if media_type == 'episode' else 'movie')
    info_tag.setTitle(meta.get('ep_name') or title)
    info_tag.setPlot(meta.get('overview') or '')
    if meta.get('year'):
        try:
            info_tag.setYear(int(meta['year']))
        except (ValueError, TypeError):
            pass
    if media_type == 'episode':
        info_tag.setTvShowTitle(title)
        info_tag.setSeason(int(meta.get('season', 1)))
        info_tag.setEpisode(int(meta.get('episode', 1)))
    return li


def _stop_previous_attempt(player, max_wait_ms=2500, force_stop=False):
    """Issues a non-blocking stop before retrying a fallback source so CVideoPlayer never blocks the GUI thread."""
    try:
        if not force_stop and not player.isPlaying():
            return
        logger('Player', 'Stopping previous stream attempt before fallback')
        xbmc.executebuiltin('PlayerControl(Stop)')
        monitor = xbmc.Monitor()
        waited = 0
        while player.isPlaying() and waited < max_wait_ms:
            if monitor.abortRequested():
                break
            xbmc.sleep(100)
            waited += 100
        if not player.isPlaying():
            xbmc.sleep(150)
    except Exception as exc:
        logger('Player', f'Error stopping previous attempt: {exc}')


def start_playback(handle, stream_url, meta, force_direct_play=False):
    """Hands the resolved stream URL to Kodi and publishes metadata for the background service."""
    media_type = meta.get('media_type', 'movie')
    li = _build_playback_listitem(stream_url, meta)

    set_property(PLAYBACK_META_PROP, json.dumps(meta))
    logger('Player', f'Starting playback: {media_type} tmdb={meta.get("tmdb_id")} handle={handle}')

    if not force_direct_play and handle >= 0:
        xbmcplugin.setResolvedUrl(handle, True, li)
    else:
        xbmc.Player().play(stream_url, li)


def play_and_verify(
    handle,
    stream_url,
    meta,
    splash=None,
    handle_used=False,
    force_direct_play=False,
    timeout_seconds=22.0,
):
    """
    Starts playback for stream_url and polls until video actually starts or fails/times out.
    Returns (status, handle_used) where status is 'started', 'timeout', 'failed', 'skipped', or 'cancelled'.
    """
    media_type = meta.get('media_type', 'movie')
    li = _build_playback_listitem(stream_url, meta)
    set_property(PLAYBACK_META_PROP, json.dumps(meta))

    player = xbmc.Player()
    monitor = xbmc.Monitor()

    # Kodi only honours setResolvedUrl() once per plugin handle; fallback retries must use Player.play().
    if handle_used:
        _stop_previous_attempt(player)
        logger('Player', f'Retrying fallback via Player.play(): {media_type} tmdb={meta.get("tmdb_id")}')
        player.play(stream_url, li)
    elif not force_direct_play and handle >= 0:
        logger('Player', f'Starting playback via setResolvedUrl: {media_type} tmdb={meta.get("tmdb_id")} handle={handle}')
        xbmcplugin.setResolvedUrl(handle, True, li)
        handle_used = True
    else:
        logger('Player', f'Starting direct playback via Player.play(): {media_type} tmdb={meta.get("tmdb_id")}')
        player.play(stream_url, li)

    start_ts = time.time()
    timeout_seconds = max(1.0, float(timeout_seconds or 15.0))
    while (time.time() - start_ts) < timeout_seconds:
        hide_busy_dialog()
        if monitor.abortRequested() or (splash and splash.is_canceled):
            if splash:
                splash.update_resolver(status_text='Cancelling...')
            _stop_previous_attempt(player, force_stop=True)
            clear_property(PLAYBACK_META_PROP)
            return 'cancelled', handle_used
        if splash and splash.skip_requested:
            if splash:
                splash.update_resolver(status_text='Skipping to next source...')
            _stop_previous_attempt(player, force_stop=True)
            clear_property(PLAYBACK_META_PROP)
            return 'skipped', handle_used
        if xbmc.getCondVisibility('Window.IsTopMost(okdialog)'):
            logger('Player', 'Dismissing okdialog error popup after stream failure')
            xbmc.executebuiltin('SendClick(okdialog, 11)')
            if splash:
                splash.update_resolver(status_text='Stream failed — trying next source...')
            _stop_previous_attempt(player, force_stop=True)
            clear_property(PLAYBACK_META_PROP)
            return 'failed', handle_used
        if player.isPlayingVideo():
            try:
                total_time = player.getTotalTime()
                if total_time and total_time > 0:
                    logger('Player', f'Playback verified (total_time={total_time:.1f}s)')
                    return 'started', handle_used
            except Exception as exc:
                logger('Player', f'Error checking player total_time: {exc}')

        if splash:
            elapsed = time.time() - start_ts
            remaining = max(0, int(math.ceil(timeout_seconds - elapsed)))
            pct = int(min(100, (elapsed / timeout_seconds) * 100))
            splash.update_resolver(percent=pct, remaining_seconds=remaining)
        xbmc.sleep(50)

    logger('Player', f'Stream start timed out after {timeout_seconds:.1f}s')
    if splash:
        splash.update_resolver(percent=100, status_text='Timed out — trying next source...')
    xbmc.sleep(50)
    _stop_previous_attempt(player, force_stop=True)
    clear_property(PLAYBACK_META_PROP)
    return 'timeout', handle_used
