# -*- coding: utf-8 -*-
import datetime
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    NEXTPAGE_ICON,
    add_dir,
    add_item,
    add_items,
    build_url,
    container_update,
    dialog_input,
    dialog_ok,
    dialog_confirm,
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
from orac.infotagger import RUN_PLUGIN


def anime_list(handle, params):
    list_type = params.get('list_type', 'trending')
    page = int(params.get('page', '1') or 1)
    per_page = int(params.get('per_page', '40') or 40)
    category_name = params.get('name') or 'Anime'

    req = {'list_type': list_type, 'page': str(page), 'per_page': str(per_page)}
    for key in ('season', 'season_year', 'search', 'genre'):
        if params.get(key):
            req[key] = params[key]

    try:
        resp = get_orac_client().get_anime_list(req) or {}
    except OracClientError as exc:
        logger('Anime', f'Error fetching anime list: {exc}')
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    if not resp.get('success'):
        notification(resp.get('error') or 'No anime results returned')
        end_directory(handle, cache_to_disc=False)
        return

    results = resp.get('results') or []
    has_next = bool((resp.get('page_info') or {}).get('has_next_page'))
    is_ext = external()

    kodi_items = []
    for item in results:
        anilist_id = item.get('anilist_id')
        if not anilist_id:
            continue
        tmdb_id = item.get('tmdb_id')
        fmt = (item.get('format') or 'TV').upper()
        is_movie = fmt == 'MOVIE' or item.get('media_type') == 'movie'
        title = item.get('title') or item.get('english_title') or item.get('romaji_title') or f'Anime #{anilist_id}'
        poster = item.get('poster_path') or EMPTY_POSTER
        fanart = item.get('fanart_path') or FANART_PATH

        if is_movie and tmdb_id:
            url = build_url({
                'mode': 'playback.play',
                'media_type': 'movie',
                'tmdb_id': tmdb_id,
                'anilist_id': anilist_id,
                'title': title,
            })
            is_folder = False
        else:
            url = build_url({
                'mode': 'anime.episodes',
                'anilist_id': anilist_id,
                'tmdb_id': tmdb_id or '',
                'title': title,
            })
            is_folder = True

        li = make_listitem(title)
        li.setArt({'poster': poster, 'fanart': fanart, 'thumb': poster, 'icon': poster})
        if not is_folder:
            li.setProperty('IsPlayable', 'true')
        tag = li.getVideoInfoTag()
        tag.setMediaType('movie' if is_movie else 'tvshow')
        tag.setTitle(title)
        tag.setPlot(item.get('overview') or '')
        try:
            tag.setRating(float(item.get('rating') or 0.0))
        except (ValueError, TypeError):
            pass
        try:
            tag.setYear(int(item.get('year') or item.get('season_year') or 0))
        except (ValueError, TypeError):
            pass
        if item.get('genres'):
            tag.setGenres([str(g) for g in item['genres']])
        kodi_items.append((url, li, is_folder))

    add_items(handle, kodi_items)

    if has_next:
        next_params = dict(params)
        next_params['page'] = str(page + 1)
        add_dir(handle, next_params, f'Next Page ({page + 1}) >>', icon=NEXTPAGE_ICON, is_folder=True)

    set_content(handle, 'tvshows')
    set_category(handle, category_name)
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode('view.tvshows', 'tvshows', is_ext)


def anime_episodes(handle, params):
    anilist_id = params.get('anilist_id')
    if not anilist_id:
        end_directory(handle, cache_to_disc=False)
        return

    try:
        resp = get_orac_client().get_anime_info({'anilist_id': anilist_id}) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    info = resp.get('anime') or resp
    show_title = info.get('title') or params.get('title') or 'Anime'
    tmdb_id = info.get('tmdb_id') or params.get('tmdb_id')
    poster = info.get('poster_path') or EMPTY_POSTER
    fanart = info.get('fanart_path') or FANART_PATH
    episodes = resp.get('episodes') or info.get('episodes') or []

    kodi_items = []
    for ep in episodes:
        abs_ep = ep.get('absolute_episode') or ep.get('episode') or 1
        s_num = ep.get('season') or 1
        e_num = ep.get('tmdb_episode') or ep.get('episode') or abs_ep
        ep_title = ep.get('title') or f'Episode {abs_ep}'
        label = f'{abs_ep:02d}. {ep_title}'
        thumb = ep.get('thumbnail') or ep.get('episode_thumbnail_path') or fanart

        url = build_url({
            'mode': 'playback.play',
            'media_type': 'episode',
            'tmdb_id': tmdb_id or '',
            'season': s_num,
            'episode': e_num,
            'anilist_id': anilist_id,
            'absolute_episode': abs_ep,
            'title': show_title,
        })
        li = make_listitem(label)
        li.setArt({'poster': poster, 'fanart': fanart, 'thumb': thumb, 'icon': thumb})
        li.setProperty('IsPlayable', 'true')
        tag = li.getVideoInfoTag()
        tag.setMediaType('episode')
        tag.setTvShowTitle(show_title)
        tag.setTitle(ep_title)
        tag.setSeason(int(s_num))
        tag.setEpisode(int(e_num))
        tag.setPlot(ep.get('overview') or '')
        kodi_items.append((url, li, False))

    is_ext = external()
    add_items(handle, kodi_items)
    set_content(handle, 'episodes')
    set_category(handle, show_title)
    end_directory(handle, cache_to_disc=not is_ext)
    set_view_mode('view.episodes', 'episodes', is_ext)


def seasonal_menu(handle, params):
    year = datetime.date.today().year
    seasons = ('WINTER', 'SPRING', 'SUMMER', 'FALL')
    for y in (year, year - 1):
        for s in seasons:
            add_dir(
                handle,
                {'mode': 'anime.list', 'list_type': 'seasonal', 'season': s, 'season_year': str(y), 'name': f'{s.title()} {y}'},
                f'{s.title()} {y}',
                icon='anime',
            )
    set_content(handle, 'files')
    set_category(handle, 'Seasonal Anime')
    end_directory(handle)


def my_lists(handle, params):
    lists_cfg = [
        ('Currently Watching', 'user_watching'),
        ('Plan to Watch', 'user_planning'),
        ('Completed', 'user_completed'),
        ('Paused', 'user_paused'),
        ('Dropped', 'user_dropped'),
    ]
    for label, lt in lists_cfg:
        add_dir(handle, {'mode': 'anime.list', 'list_type': lt, 'name': label}, label, icon='trakt')
    set_content(handle, 'files')
    set_category(handle, 'My AniList')
    end_directory(handle)


def search(handle, params):
    q = dialog_input('Search Anime').strip()
    if not q:
        return
    container_update(build_url({'mode': 'anime.list', 'list_type': 'search', 'search': q, 'name': f'Anime: {q}'}))


def status(handle, params):
    try:
        client = get_orac_client()
        data = client.get_anime_status() or {}
        msg = (
            f"Mappings: {data.get('mappings_count', 'N/A')}\n"
            f"AniList Auth: {data.get('anilist_authenticated', False)}\n"
            f"Last Sync: {data.get('last_sync', 'N/A')}"
        )
        if dialog_confirm('Anime Bridge Status', f'{msg}\n\nTrigger mapping sync now?'):
            client.sync_anime_mappings()
            notification('Anime mapping sync started on Orac')
    except OracClientError as exc:
        dialog_ok('Anime Bridge Status', f'Error: {exc}')
