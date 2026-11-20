# -*- coding: utf-8 -*-
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    build_url,
    make_listitem,
)
from core.settings import media_open_action

RUN_PLUGIN = 'RunPlugin(%s)'
CONTAINER_UPDATE = 'Container.Update(%s)'


def _safe_int(val, default=0):
    try:
        return int(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _apply_resume_and_watched(li, info_tag, meta):
    percent_watched = _safe_float(
        meta.get('percent_watched') if meta.get('percent_watched') is not None
        else (meta.get('progress') if meta.get('progress') is not None else meta.get('resume_point'))
    )
    watched = bool(meta.get('watched')) or meta.get('watched_status') == 2 or percent_watched >= 90
    info_tag.setPlaycount(1 if watched else 0)

    duration = _safe_int(meta.get('duration') or meta.get('runtime'))
    total_seconds = (duration * 60) if (0 < duration < 600) else duration

    if 0 < percent_watched < 90 and not watched:
        li.setProperty('watchedprogress', str(int(percent_watched)))
        if total_seconds > 0:
            resume_sec = (percent_watched / 100.0) * total_seconds
            info_tag.setResumePoint(resume_sec, float(total_seconds))
    else:
        li.setProperty('watchedprogress', '0')
    return watched


def _apply_common_tag(info_tag, meta, media_type, title=None):
    info_tag.setMediaType(media_type)
    info_tag.setTitle(title or meta.get('episode_title') or meta.get('title') or '')
    info_tag.setOriginalTitle(meta.get('original_title') or '')
    info_tag.setYear(_safe_int(meta.get('year') or meta.get('show_year')))
    info_tag.setPlot(meta.get('episode_overview') or meta.get('overview') or meta.get('show_overview') or '')
    info_tag.setTagLine(meta.get('tagline') or '')
    info_tag.setTrailer(meta.get('trailer') or '')
    rating = meta.get('episode_rating') if meta.get('episode_rating') is not None else meta.get('rating')
    info_tag.setRating(_safe_float(rating))
    info_tag.setVotes(_safe_int(meta.get('votes')))
    info_tag.setMpaa(meta.get('certification') or '')

    genres = meta.get('genres') or []
    if isinstance(genres, str):
        genres = [g.strip() for g in genres.split(',') if g.strip()]
    if genres:
        info_tag.setGenres(genres)

    studio = meta.get('studio') or meta.get('network') or ''
    if isinstance(studio, str) and studio:
        info_tag.setStudios([s.strip() for s in studio.split(',') if s.strip()])
    elif isinstance(studio, list) and studio:
        info_tag.setStudios([str(s) for s in studio if s])

    premiered = meta.get('premiered') or meta.get('air_date') or meta.get('first_aired') or ''
    if premiered:
        info_tag.setFirstAired(str(premiered)[:10])

    duration = _safe_int(meta.get('duration') or meta.get('runtime'))
    if duration > 0:
        # Orac typically returns minutes if < 600, seconds otherwise
        info_tag.setDuration(duration * 60 if duration < 600 else duration)

    unique_ids = {}
    if meta.get('tmdb_id'):
        unique_ids['tmdb'] = str(meta['tmdb_id'])
    if meta.get('imdb_id'):
        unique_ids['imdb'] = str(meta['imdb_id'])
    if meta.get('tvdb_id'):
        unique_ids['tvdb'] = str(meta['tvdb_id'])
    if unique_ids:
        info_tag.setUniqueIDs(unique_ids, 'tmdb' if 'tmdb' in unique_ids else next(iter(unique_ids)))


def build_movie_item(meta, is_external=False, hide_watched=False):
    tmdb_id = meta.get('tmdb_id') or meta.get('id')
    title = meta.get('title') or ''
    year = _safe_int(meta.get('year'))
    watched = bool(meta.get('watched'))
    if hide_watched and watched:
        return None

    poster = meta.get('poster_path') or EMPTY_POSTER
    fanart = meta.get('fanart_path') or FANART_PATH
    clearlogo = meta.get('clearlogo_path') or ''
    landscape = meta.get('landscape_path') or fanart

    play_params = {
        'mode': 'playback.play',
        'media_type': 'movie',
        'tmdb_id': tmdb_id,
        'title': title,
        'year': year,
    }
    extras_params = {
        'mode': 'windows.extras',
        'media_type': 'movie',
        'tmdb_id': tmdb_id,
    }

    open_extras = media_open_action('movie') == 1
    primary_url = build_url(extras_params if open_extras else play_params)
    is_folder = False

    li = make_listitem(title)
    li.setArt({
        'poster': poster,
        'fanart': fanart,
        'icon': landscape or poster,
        'thumb': poster,
        'clearlogo': clearlogo,
        'landscape': landscape,
        'movie.poster': poster,
        'movie.fanart': fanart,
        'movie.clearlogo': clearlogo,
        'movie.landscape': landscape,
    })

    info_tag = li.getVideoInfoTag()
    _apply_common_tag(info_tag, meta, 'movie', title=title)
    _apply_resume_and_watched(li, info_tag, meta)
    li.setProperty('IsPlayable', 'false' if open_extras else 'true')

    cm = []
    if open_extras:
        cm.append(('[B]Play[/B]', RUN_PLUGIN % build_url(play_params)))
    else:
        cm.append(('[B]Extras[/B]', RUN_PLUGIN % build_url(extras_params)))
    cm.append(('[B]Select Source[/B]', RUN_PLUGIN % build_url({**play_params, 'force_select': 'true'})))
    if tmdb_id:
        cm.append(('[B]Play Trailer[/B]', RUN_PLUGIN % build_url({
            'mode': 'playback.trailer', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'trailer_url': meta.get('trailer', '')
        })))
    cm.append(('[B]Orac Lists Manager[/B]', RUN_PLUGIN % build_url({
        'mode': 'lists.manager_choice', 'media_type': 'movie', 'tmdb_id': tmdb_id, 'icon': poster
    })))
    cm.append(('[B]Add Tag[/B]', RUN_PLUGIN % build_url({
        'mode': 'tags.add', 'media_type': 'movie', 'tmdb_id': tmdb_id
    })))
    cm.append(('[B]Remove Tag[/B]', RUN_PLUGIN % build_url({
        'mode': 'tags.remove', 'media_type': 'movie', 'tmdb_id': tmdb_id
    })))
    watch_action = 'mark_as_unwatched' if watched else 'mark_as_watched'
    watch_label = 'Mark Unwatched' if watched else 'Mark Watched'
    cm.append((f'[B]{watch_label}[/B]', RUN_PLUGIN % build_url({
        'mode': 'watched.movie', 'action': watch_action, 'tmdb_id': tmdb_id
    })))
    li.addContextMenuItems(cm)

    return primary_url, li, is_folder


def build_tvshow_item(meta, is_external=False, hide_watched=False):
    tmdb_id = meta.get('tmdb_id') or meta.get('id')
    title = meta.get('title') or ''
    total_episodes = _safe_int(meta.get('total_episodes') or meta.get('aired_episodes'))
    watched_episodes = _safe_int(meta.get('watched_episodes'))
    unwatched = max(0, total_episodes - watched_episodes)
    is_watched = total_episodes > 0 and unwatched == 0
    if hide_watched and is_watched:
        return None

    poster = meta.get('poster_path') or EMPTY_POSTER
    fanart = meta.get('fanart_path') or FANART_PATH
    clearlogo = meta.get('clearlogo_path') or ''
    landscape = meta.get('landscape_path') or fanart

    browse_params = {
        'mode': 'tv.seasons',
        'tmdb_id': tmdb_id,
        'title': title,
    }
    extras_params = {
        'mode': 'windows.extras',
        'media_type': 'tvshow',
        'tmdb_id': tmdb_id,
    }

    open_extras = media_open_action('tvshow') == 1
    primary_url = build_url(extras_params if open_extras else browse_params)
    is_folder = not open_extras

    li = make_listitem(title)
    li.setArt({
        'poster': poster,
        'fanart': fanart,
        'icon': landscape or poster,
        'thumb': poster,
        'clearlogo': clearlogo,
        'landscape': landscape,
        'tvshow.poster': poster,
        'tvshow.fanart': fanart,
        'tvshow.clearlogo': clearlogo,
        'tvshow.landscape': landscape,
    })
    li.setProperty('TotalEpisodes', str(total_episodes))
    li.setProperty('WatchedEpisodes', str(watched_episodes))
    li.setProperty('UnWatchedEpisodes', str(unwatched))

    info_tag = li.getVideoInfoTag()
    _apply_common_tag(info_tag, meta, 'tvshow', title=title)
    info_tag.setTvShowTitle(title)
    info_tag.setPlaycount(1 if is_watched else 0)

    cm = []
    if open_extras:
        cm.append(('[B]Browse[/B]', CONTAINER_UPDATE % build_url(browse_params)))
    else:
        cm.append(('[B]Extras[/B]', RUN_PLUGIN % build_url(extras_params)))
    if tmdb_id:
        cm.append(('[B]Play Trailer[/B]', RUN_PLUGIN % build_url({
            'mode': 'playback.trailer', 'media_type': 'tvshow', 'tmdb_id': tmdb_id, 'trailer_url': meta.get('trailer', '')
        })))
    cm.append(('[B]Orac Lists Manager[/B]', RUN_PLUGIN % build_url({
        'mode': 'lists.manager_choice', 'media_type': 'tvshow', 'tmdb_id': tmdb_id, 'icon': poster
    })))
    cm.append(('[B]Add Tag[/B]', RUN_PLUGIN % build_url({
        'mode': 'tags.add', 'media_type': 'tvshow', 'tmdb_id': tmdb_id
    })))
    cm.append(('[B]Remove Tag[/B]', RUN_PLUGIN % build_url({
        'mode': 'tags.remove', 'media_type': 'tvshow', 'tmdb_id': tmdb_id
    })))
    watch_action = 'mark_as_unwatched' if is_watched else 'mark_as_watched'
    watch_label = 'Mark Unwatched' if is_watched else 'Mark Watched'
    cm.append((f'[B]{watch_label}[/B]', RUN_PLUGIN % build_url({
        'mode': 'watched.tvshow', 'action': watch_action, 'tmdb_id': tmdb_id
    })))
    cm.append(('[B]Drop Show[/B]', RUN_PLUGIN % build_url({
        'mode': 'watched.drop_tvshow', 'tmdb_id': tmdb_id, 'title': title
    })))
    li.addContextMenuItems(cm)

    return primary_url, li, is_folder


def build_season_item(meta, show_meta):
    tmdb_id = show_meta.get('show_tmdb_id') or meta.get('tmdb_id')
    show_title = show_meta.get('show_title', '')
    season_num = _safe_int(meta.get('season'), 1)
    title = meta.get('title') or (f'Specials' if season_num == 0 else f'Season {season_num}')

    poster = meta.get('poster_path') or show_meta.get('show_poster') or EMPTY_POSTER
    fanart = meta.get('fanart_path') or show_meta.get('show_fanart') or FANART_PATH
    clearlogo = show_meta.get('show_clearlogo', '')
    landscape = show_meta.get('show_landscape', fanart)

    episodes = meta.get('episodes') or []
    total_eps = _safe_int(meta.get('episode_count') or len(episodes))
    watched_eps = _safe_int(meta.get('watched_episodes'))
    if watched_eps == 0 and episodes:
        watched_eps = sum(1 for ep in episodes if ep.get('watched'))
    unwatched = max(0, total_eps - watched_eps)
    is_watched = total_eps > 0 and unwatched == 0

    url = build_url({
        'mode': 'tv.episodes',
        'tmdb_id': tmdb_id,
        'season': season_num,
        'title': show_title,
    })

    li = make_listitem(title)
    li.setArt({
        'poster': poster,
        'season.poster': poster,
        'tvshow.poster': show_meta.get('show_poster') or poster,
        'tvshow.clearlogo': clearlogo,
        'fanart': fanart,
        'landscape': landscape,
        'thumb': poster,
        'icon': poster,
    })
    li.setProperty('TotalEpisodes', str(total_eps))
    li.setProperty('WatchedEpisodes', str(watched_eps))
    li.setProperty('UnWatchedEpisodes', str(unwatched))

    info_tag = li.getVideoInfoTag()
    _apply_common_tag(info_tag, meta, 'season', title=title)
    info_tag.setTvShowTitle(show_title)
    info_tag.setSeason(season_num)
    info_tag.setPlaycount(1 if is_watched else 0)

    watch_action = 'mark_as_unwatched' if is_watched else 'mark_as_watched'
    watch_label = 'Mark Unwatched' if is_watched else 'Mark Watched'
    li.addContextMenuItems([
        (f'[B]{watch_label}[/B]', RUN_PLUGIN % build_url({
            'mode': 'watched.season', 'action': watch_action, 'tmdb_id': tmdb_id, 'season': season_num
        }))
    ])
    return url, li, True


def build_episode_item(meta, show_meta=None, include_show_prefix=False):
    show_meta = show_meta or {}
    tmdb_id = meta.get('show_tmdb_id') or show_meta.get('show_tmdb_id') or meta.get('tmdb_id')
    show_title = meta.get('show_title') or show_meta.get('show_title') or ''
    raw_season = meta.get('season') if meta.get('season') is not None else meta.get('season_number')
    raw_episode = meta.get('episode_number') if meta.get('episode_number') is not None else meta.get('episode')
    season_num = _safe_int(raw_season, 1)
    episode_num = _safe_int(raw_episode, 1)
    ep_title = meta.get('episode_title') or meta.get('title') or f'Episode {episode_num}'

    if include_show_prefix and show_title:
        label = f'{show_title} - {season_num}x{episode_num:02d} - {ep_title}'
    else:
        label = f'{season_num}x{episode_num:02d}. {ep_title}'

    watched = bool(meta.get('watched'))
    show_poster = meta.get('show_poster_path') or show_meta.get('show_poster') or EMPTY_POSTER
    show_fanart = meta.get('show_fanart_path') or show_meta.get('show_fanart') or FANART_PATH
    show_clearlogo = meta.get('show_clearlogo_path') or show_meta.get('show_clearlogo') or ''
    show_landscape = meta.get('show_landscape_path') or show_meta.get('show_landscape') or show_fanart
    thumb = meta.get('episode_thumbnail_path') or show_landscape

    play_params = {
        'mode': 'playback.play',
        'media_type': 'episode',
        'tmdb_id': tmdb_id,
        'season': season_num,
        'episode': episode_num,
        'title': show_title or ep_title,
    }
    url = build_url(play_params)

    li = make_listitem(label)
    li.setArt({
        'poster': show_poster,
        'fanart': show_fanart,
        'icon': thumb,
        'thumb': thumb,
        'clearlogo': show_clearlogo,
        'landscape': show_landscape,
        'tvshow.poster': show_poster,
        'tvshow.fanart': show_fanart,
        'tvshow.clearlogo': show_clearlogo,
        'tvshow.landscape': show_landscape,
    })
    li.setProperty('IsPlayable', 'true')

    info_tag = li.getVideoInfoTag()
    _apply_common_tag(info_tag, meta, 'episode', title=ep_title)
    info_tag.setTvShowTitle(show_title)
    info_tag.setSeason(season_num)
    info_tag.setEpisode(episode_num)
    watched = _apply_resume_and_watched(li, info_tag, meta)

    watch_action = 'mark_as_unwatched' if watched else 'mark_as_watched'
    watch_label = 'Mark Unwatched' if watched else 'Mark Watched'
    cm = [
        ('[B]Select Source[/B]', RUN_PLUGIN % build_url({**play_params, 'force_select': 'true'})),
        (f'[B]{watch_label}[/B]', RUN_PLUGIN % build_url({
            'mode': 'watched.episode', 'action': watch_action,
            'tmdb_id': tmdb_id, 'season': season_num, 'episode': episode_num
        })),
    ]
    if include_show_prefix and tmdb_id:
        cm.append(('[B]Browse Show[/B]', CONTAINER_UPDATE % build_url({
            'mode': 'tv.seasons', 'tmdb_id': tmdb_id, 'title': show_title
        })))
    li.addContextMenuItems(cm)
    return url, li, False
