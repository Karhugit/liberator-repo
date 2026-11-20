# -*- coding: utf-8 -*-
import json
import xbmc
import xbmcplugin
from core.kodi import EMPTY_POSTER, FANART_PATH, logger, make_listitem, set_property

PLAYBACK_META_PROP = 'liberator2.playback_meta'


def start_playback(handle, stream_url, meta, force_direct_play=False):
    """Hands the resolved stream URL to Kodi and publishes metadata for the background service."""
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

    set_property(PLAYBACK_META_PROP, json.dumps(meta))
    logger('Player', f'Starting playback: {media_type} tmdb={meta.get("tmdb_id")} handle={handle}')

    if not force_direct_play and handle >= 0:
        xbmcplugin.setResolvedUrl(handle, True, li)
    else:
        xbmc.Player().play(stream_url, li)
