# -*- coding: utf-8 -*-
import sys
import json
import time
from datetime import datetime
import xbmc
import xbmcgui
import xbmcplugin
import xbmcaddon
from modules import kodi_utils
from apis.orac_api import _get_data_via_ipc

logger = kodi_utils.logger
make_listitem = kodi_utils.make_listitem
build_url = kodi_utils.build_url
add_item = kodi_utils.add_item
add_items = kodi_utils.add_items
set_content = kodi_utils.set_content
set_category = kodi_utils.set_category
end_directory = kodi_utils.end_directory
set_view_mode = kodi_utils.set_view_mode
get_icon = kodi_utils.get_icon
notification = kodi_utils.notification
kodi_refresh = kodi_utils.kodi_refresh
select_dialog = kodi_utils.select_dialog
confirm_dialog = kodi_utils.confirm_dialog
show_text = kodi_utils.show_text

ADDON_ID = 'plugin.video.liberator'
ADDON = xbmcaddon.Addon(ADDON_ID)
fanart_default = kodi_utils.get_addon_fanart()
poster_empty = kodi_utils.empty_poster
anime_icon = get_icon('anime') or get_icon('tv')
run_plugin = 'RunPlugin(%s)'
container_update = 'Container.Update(%s)'


def _format_timestamp(ts):
    if not ts:
        return "Never"
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%Y-%m-%d %H:%M:%S')
    except Exception:
        return str(ts)


def build_anime_list(params, addon_handle=None):
    """
    Fetches and renders an AniList anime list from Orac's `/anime/list` endpoint.
    """
    handle = addon_handle if addon_handle is not None else int(sys.argv[1])
    list_type = params.get('list_type', 'trending')
    page = int(params.get('page', '1') or 1)
    per_page = int(params.get('per_page', '40') or 40)
    season = params.get('season')
    season_year = params.get('season_year')
    search_query = params.get('search')
    genre = params.get('genre')
    category_name = params.get('name') or params.get('category_name') or 'Anime'

    ipc_params = {
        'list_type': list_type,
        'page': str(page),
        'per_page': str(per_page),
    }
    if season:
        ipc_params['season'] = season
    if season_year:
        ipc_params['season_year'] = str(season_year)
    if search_query:
        ipc_params['search'] = search_query
    if genre:
        ipc_params['genre'] = genre

    try:
        response = _get_data_via_ipc('get_anime_list', params=ipc_params)
        if not response or not response.get('success'):
            err_msg = (response or {}).get('error') or 'No anime results returned from Orac.'
            notification(err_msg, 3500)
            end_directory(handle, cacheToDisc=False)
            return

        results = response.get('results') or []
        page_info = response.get('page_info') or {}
        has_next_page = bool(page_info.get('has_next_page'))

        if not results:
            notification(f'No anime found in {category_name}', 3000)
            end_directory(handle, cacheToDisc=False)
            return

        item_list = []
        for item in results:
            anilist_id = item.get('anilist_id')
            if not anilist_id:
                continue

            tmdb_id = item.get('tmdb_id')
            tvdb_id = item.get('tvdb_id')
            imdb_id = item.get('imdb_id') or ''
            mal_id = item.get('mal_id')
            fmt = (item.get('format') or 'TV').upper()
            is_movie = (fmt == 'MOVIE' or item.get('media_type') == 'movie')

            title = item.get('title') or item.get('english_title') or item.get('romaji_title') or f'Anime #{anilist_id}'
            romaji_title = item.get('romaji_title') or ''
            english_title = item.get('english_title') or ''
            native_title = item.get('native_title') or ''
            year = item.get('year') or item.get('season_year') or 0
            episodes_count = item.get('episodes')
            user_progress = item.get('user_progress')
            rating = float(item.get('rating') or 0.0)
            genres = item.get('genres') or []
            overview = item.get('overview') or ''
            poster = item.get('poster_path') or poster_empty
            fanart = item.get('fanart_path') or poster or fanart_default

            # Build informative label & plot showing Romaji title, format, and TMDB bridge status
            badge_parts = [fmt]
            if episodes_count:
                if user_progress is not None:
                    badge_parts.append(f'{user_progress}/{episodes_count} eps')
                else:
                    badge_parts.append(f'{episodes_count} eps')
            if tmdb_id:
                badge_parts.append(f'TMDB:{tmdb_id}')
            badge_str = ' | '.join(badge_parts)

            display_label = f'{title} [COLOR FF90EE90][{badge_str}][/COLOR]'

            plot_header = []
            if romaji_title and romaji_title.lower() != title.lower():
                plot_header.append(f'[B]Romaji:[/B] {romaji_title}')
            if native_title:
                plot_header.append(f'[B]Native:[/B] {native_title}')
            id_summary = f'AniList: {anilist_id}'
            if mal_id:
                id_summary += f' | MAL: {mal_id}'
            if tmdb_id:
                id_summary += f' | TMDB: {tmdb_id}'
            plot_header.append(f'[COLOR FFADD8E6]{id_summary}[/COLOR]')
            full_plot = '\n'.join(plot_header) + ('\n\n' + overview if overview else '')

            if is_movie:
                url_params = {
                    'mode': 'playback.media',
                    'media_type': 'movie',
                    'anilist_id': str(anilist_id),
                    'abs_ep': '1',
                    'custom_title': english_title or title,
                }
                if tmdb_id:
                    url_params['tmdb_id'] = str(tmdb_id)
                if year:
                    url_params['custom_year'] = str(year)
                is_folder = False
            else:
                url_params = {
                    'mode': 'orac.anime.episodes',
                    'anilist_id': str(anilist_id),
                    'title': title,
                }
                if tmdb_id:
                    url_params['tmdb_id'] = str(tmdb_id)
                is_folder = True

            url = build_url(url_params)
            listitem = make_listitem()
            listitem.setLabel(display_label)
            listitem.setArt({
                'poster': poster,
                'fanart': fanart,
                'icon': poster,
                'thumb': poster,
                'banner': fanart,
            })

            if is_movie:
                listitem.setProperty('IsPlayable', 'true')

            info_tag = listitem.getVideoInfoTag()
            info_tag.setMediaType('movie' if is_movie else 'tvshow')
            info_tag.setTitle(title)
            if romaji_title:
                info_tag.setOriginalTitle(romaji_title)
            info_tag.setPlot(full_plot)
            if year:
                try:
                    info_tag.setYear(int(year))
                except Exception:
                    pass
            if rating:
                try:
                    info_tag.setRating(float(rating))
                except Exception:
                    pass
            if genres and isinstance(genres, list):
                try:
                    info_tag.setGenres([str(g) for g in genres])
                except Exception:
                    pass
            unique_ids = {'anilist': str(anilist_id)}
            if tmdb_id:
                unique_ids['tmdb'] = str(tmdb_id)
            if imdb_id:
                unique_ids['imdb'] = str(imdb_id)
            if tvdb_id:
                unique_ids['tvdb'] = str(tvdb_id)
            try:
                info_tag.setUniqueIDs(unique_ids)
            except Exception:
                pass

            # Context Menu items
            cm = []
            cm.append((
                '[B]Coordinate & Alias Info[/B]',
                run_plugin % build_url({
                    'mode': 'orac.anime.mapping_info',
                    'anilist_id': str(anilist_id),
                    'episode': '1',
                    'title': title,
                })
            ))
            cm.append((
                '[B]Related / Sequels & Prequels[/B]',
                container_update % build_url({
                    'mode': 'orac.anime.relations',
                    'anilist_id': str(anilist_id),
                    'title': title,
                })
            ))
            if is_movie:
                cm.append((
                    '[B]Mark Movie Watched (Anime Bridge)[/B]',
                    run_plugin % build_url({
                        'mode': 'orac.anime.mark_watched',
                        'anilist_id': str(anilist_id),
                        'episode': '1',
                        'percent_watched': '100',
                        'title': title,
                    })
                ))
            if tmdb_id:
                cm.append((
                    '[B]Lists Manager[/B]',
                    run_plugin % build_url({
                        'mode': 'orac.lists_manager_choice',
                        'tmdb_id': str(tmdb_id),
                        'media_type': 'movie' if is_movie else 'tvshow',
                    })
                ))
            listitem.addContextMenuItems(cm)
            item_list.append((url, listitem, is_folder))

        if has_next_page:
            next_params = dict(params)
            next_params['mode'] = 'orac.anime.list'
            next_params['page'] = str(page + 1)
            next_url = build_url(next_params)
            next_item = make_listitem()
            next_item.setLabel(f'[B]Next Page ({page + 1}) >>[/B]')
            next_icon = get_icon('nextpage') or anime_icon
            next_item.setArt({'icon': next_icon, 'poster': next_icon, 'thumb': next_icon, 'fanart': fanart_default})
            item_list.append((next_url, next_item, True))

        add_items(handle, item_list)
        set_content(handle, 'movies' if list_type == 'movies' else 'tvshows')
        set_category(handle, category_name)
        end_directory(handle, cacheToDisc=False)
        set_view_mode('view.movies' if list_type == 'movies' else 'view.tvshows', 'movies' if list_type == 'movies' else 'tvshows')

    except Exception as e:
        import traceback
        logger("OracAnime", f"Error in build_anime_list: {e}\n{traceback.format_exc()}")
        notification(f"Error loading Anime list: {e}", 3500)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def build_anime_episodes(params, addon_handle=None):
    """
    Fetches detailed metadata and episode list for an `anilist_id` via `/anime/info`
    and renders each episode with its resolved Western SxxExx coordinate badge.
    """
    handle = addon_handle if addon_handle is not None else int(sys.argv[1])
    anilist_id = params.get('anilist_id')
    if not anilist_id:
        notification("Missing AniList ID", 3000)
        end_directory(handle, cacheToDisc=False)
        return

    try:
        details = _get_data_via_ipc('get_anime_info', params={'anilist_id': str(anilist_id)})
        if not details or not details.get('success'):
            err = (details or {}).get('error') or f"Failed to load AniList #{anilist_id}"
            notification(err, 3500)
            end_directory(handle, cacheToDisc=False)
            return

        show_title = details.get('title') or details.get('english_title') or details.get('romaji_title') or f'Anime #{anilist_id}'
        romaji_title = details.get('romaji_title') or ''
        english_title = details.get('english_title') or ''
        show_tmdb_id = details.get('tmdb_id') or params.get('tmdb_id')
        show_poster = details.get('poster_path') or poster_empty
        show_fanart = details.get('fanart_path') or show_poster or fanart_default
        show_overview = details.get('overview') or ''
        show_year = details.get('year') or details.get('season_year') or 0
        episode_list = details.get('episode_list') or []

        # If an upcoming or unindexed show has 0 episodes in episode_list, provide at least Episode 1 for testing
        if not episode_list:
            episode_list = [{
                'absolute_episode': 1,
                'episode': 1,
                'title': 'Episode 1',
                'thumbnail_path': show_fanart,
                'watched': False,
                'tmdb_id': show_tmdb_id,
                'western_season': 1,
                'western_episode': 1,
                'mapping_source': 'fallback_1to1',
            }]

        item_list = []
        for ep in episode_list:
            abs_ep = int(ep.get('absolute_episode') or ep.get('episode') or 1)
            ep_title = ep.get('title') or f'Episode {abs_ep}'
            ep_thumb = ep.get('thumbnail_path') or show_fanart
            watched = bool(ep.get('watched'))

            ep_tmdb_id = ep.get('tmdb_id') or show_tmdb_id
            w_season = ep.get('western_season')
            w_episode = ep.get('western_episode')
            mapping_src = ep.get('mapping_source') or 'fallback_1to1'

            if w_season is not None and w_episode is not None:
                coord_badge = f'S{int(w_season):02d}E{int(w_episode):02d}'
            else:
                coord_badge = 'MOVIE'

            label = f'{abs_ep:02d}. {ep_title} [COLOR FF90EE90][{coord_badge}][/COLOR]'

            play_params = {
                'mode': 'playback.media',
                'media_type': 'episode',
                'anilist_id': str(anilist_id),
                'abs_ep': str(abs_ep),
                'season': str(w_season if w_season is not None else 1),
                'episode': str(w_episode if w_episode is not None else abs_ep),
                'custom_title': english_title or show_title,
            }
            if ep_tmdb_id:
                play_params['tmdb_id'] = str(ep_tmdb_id)
            if show_year:
                play_params['custom_year'] = str(show_year)

            url = build_url(play_params)
            listitem = make_listitem()
            listitem.setLabel(label)
            listitem.setProperty('IsPlayable', 'true')
            listitem.setArt({
                'poster': show_poster,
                'fanart': show_fanart,
                'thumb': ep_thumb,
                'icon': ep_thumb,
                'banner': show_fanart,
            })

            plot_lines = [
                f'[B]Anime:[/B] {show_title}',
                f'[B]Romaji:[/B] {romaji_title}' if romaji_title else '',
                f'[COLOR FFADD8E6]AniList #{anilist_id} Ep {abs_ep} -> TMDB #{ep_tmdb_id or "N/A"} {coord_badge} ({mapping_src})[/COLOR]',
                '',
                show_overview,
            ]
            plot_str = '\n'.join([line for line in plot_lines if line is not None])

            info_tag = listitem.getVideoInfoTag()
            info_tag.setMediaType('episode')
            info_tag.setTvShowTitle(show_title)
            info_tag.setTitle(ep_title)
            info_tag.setSeason(int(w_season if w_season is not None else 1))
            info_tag.setEpisode(int(w_episode if w_episode is not None else abs_ep))
            info_tag.setPlot(plot_str)
            if watched:
                info_tag.setPlaycount(1)

            cm = [
                (
                    '[B]Inspect Coordinate & Scraper Queries[/B]',
                    run_plugin % build_url({
                        'mode': 'orac.anime.mapping_info',
                        'anilist_id': str(anilist_id),
                        'episode': str(abs_ep),
                        'title': f'{show_title} - Ep {abs_ep}',
                    })
                ),
                (
                    '[B]Mark Episode Watched (Anime Bridge)[/B]',
                    run_plugin % build_url({
                        'mode': 'orac.anime.mark_watched',
                        'anilist_id': str(anilist_id),
                        'episode': str(abs_ep),
                        'percent_watched': '100',
                        'title': f'{show_title} Ep {abs_ep}',
                    })
                ),
                (
                    '[B]Mark Episode Unwatched (Anime Bridge)[/B]',
                    run_plugin % build_url({
                        'mode': 'orac.anime.mark_watched',
                        'anilist_id': str(anilist_id),
                        'episode': str(abs_ep),
                        'percent_watched': '0',
                        'title': f'{show_title} Ep {abs_ep}',
                    })
                ),
            ]
            listitem.addContextMenuItems(cm)
            item_list.append((url, listitem, False))

        add_items(handle, item_list)
        set_content(handle, 'episodes')
        set_category(handle, show_title)
        end_directory(handle, cacheToDisc=False)
        set_view_mode('view.episodes_single', 'episodes')

    except Exception as e:
        import traceback
        logger("OracAnime", f"Error in build_anime_episodes: {e}\n{traceback.format_exc()}")
        notification(f"Error loading episodes: {e}", 3500)
        xbmcplugin.endOfDirectory(handle, succeeded=False)


def build_anime_relations(params, addon_handle=None):
    """Displays related anime entries (Sequels, Prequels, Side Stories, Movies) for an `anilist_id`."""
    handle = addon_handle if addon_handle is not None else int(sys.argv[1])
    anilist_id = params.get('anilist_id')
    base_title = params.get('title') or f'Anime #{anilist_id}'

    details = _get_data_via_ipc('get_anime_info', params={'anilist_id': str(anilist_id)})
    if not details or not details.get('success'):
        notification("No relation details found", 3000)
        end_directory(handle, cacheToDisc=False)
        return

    relations = details.get('relations') or []
    if not relations:
        notification(f"No related anime found for {base_title}", 3000)
        end_directory(handle, cacheToDisc=False)
        return

    item_list = []
    for rel in relations:
        rel_id = rel.get('anilist_id')
        if not rel_id:
            continue
        rel_type = rel.get('relation_type') or 'RELATED'
        rel_title = rel.get('title') or rel.get('romaji_title') or f'Anime #{rel_id}'
        rel_fmt = (rel.get('format') or 'TV').upper()
        rel_poster = rel.get('poster_path') or details.get('poster_path') or poster_empty
        is_movie = rel_fmt == 'MOVIE'

        label = f'[COLOR FFADD8E6][{rel_type}][/COLOR] {rel_title} ({rel_fmt})'
        if is_movie:
            url = build_url({
                'mode': 'playback.media',
                'media_type': 'movie',
                'anilist_id': str(rel_id),
                'abs_ep': '1',
                'custom_title': rel_title,
            })
            is_folder = False
        else:
            url = build_url({
                'mode': 'orac.anime.episodes',
                'anilist_id': str(rel_id),
                'title': rel_title,
            })
            is_folder = True

        li = make_listitem()
        li.setLabel(label)
        if is_movie:
            li.setProperty('IsPlayable', 'true')
        li.setArt({'poster': rel_poster, 'icon': rel_poster, 'thumb': rel_poster, 'fanart': fanart_default})
        info_tag = li.getVideoInfoTag()
        info_tag.setMediaType('movie' if is_movie else 'tvshow')
        info_tag.setTitle(rel_title)
        item_list.append((url, li, is_folder))

    add_items(handle, item_list)
    set_content(handle, 'tvshows')
    set_category(handle, f'Related: {base_title}')
    end_directory(handle, cacheToDisc=False)
    set_view_mode('view.tvshows', 'tvshows')


def build_anime_seasonal_menu(params, addon_handle=None):
    """Displays a menu of current and recent Anime Seasons (Winter, Spring, Summer, Fall)."""
    handle = addon_handle if addon_handle is not None else int(sys.argv[1])
    now = datetime.now()
    cur_year = now.year

    entries = [
        ({'mode': 'orac.anime.list', 'list_type': 'seasonal', 'name': 'Current Season Anime'}, '[B]Current Season[/B]'),
    ]
    seasons_order = ['WINTER', 'SPRING', 'SUMMER', 'FALL']
    for yr in (cur_year, cur_year - 1):
        for s_name in reversed(seasons_order):
            label = f'{s_name.title()} {yr}'
            entries.append((
                {
                    'mode': 'orac.anime.list',
                    'list_type': 'seasonal',
                    'season': s_name,
                    'season_year': str(yr),
                    'name': f'Anime: {label}',
                },
                label,
            ))

    item_list = []
    for url_params, label in entries:
        url = build_url(url_params)
        li = make_listitem()
        li.setLabel(label)
        li.setArt({'icon': anime_icon, 'poster': anime_icon, 'thumb': anime_icon, 'fanart': fanart_default})
        item_list.append((url, li, True))

    add_items(handle, item_list)
    set_content(handle, 'files')
    set_category(handle, 'Seasonal Anime')
    end_directory(handle, cacheToDisc=False)
    set_view_mode('view.main', '')


def build_anime_my_lists_menu(params, addon_handle=None):
    """Displays the user's AniList categories (Watching, Planning, Completed, Paused, Dropped)."""
    handle = addon_handle if addon_handle is not None else int(sys.argv[1])
    categories = [
        ('user_watching', 'Currently Watching'),
        ('user_planning', 'Plan to Watch'),
        ('user_completed', 'Completed'),
        ('user_paused', 'Paused / On Hold'),
        ('user_dropped', 'Dropped'),
    ]
    item_list = []
    for list_type, label in categories:
        url = build_url({
            'mode': 'orac.anime.list',
            'list_type': list_type,
            'name': f'AniList: {label}',
        })
        li = make_listitem()
        li.setLabel(label)
        li.setArt({'icon': anime_icon, 'poster': anime_icon, 'thumb': anime_icon, 'fanart': fanart_default})
        item_list.append((url, li, True))

    add_items(handle, item_list)
    set_content(handle, 'files')
    set_category(handle, 'My AniList')
    end_directory(handle, cacheToDisc=False)
    set_view_mode('view.main', '')


def anime_search_dialog(params):
    """Prompts for an Anime search query (English or Romaji) and opens the search results folder."""
    query = kodi_utils.kodi_dialog().input('Search Anime (Romaji or English)')
    if not query:
        return
    url = build_url({
        'mode': 'orac.anime.list',
        'list_type': 'search',
        'search': query,
        'name': f'Anime Search: {query}',
    })
    xbmc.executebuiltin(container_update % url)


def mark_anime_watched_action(params):
    """Calls Orac's `/anime/watched` endpoint via IPC to scrobble an anime episode/movie."""
    anilist_id = params.get('anilist_id')
    episode = params.get('episode', '1')
    percent_watched = params.get('percent_watched', '100')
    title = params.get('title') or f'AniList #{anilist_id}'

    res = _get_data_via_ipc('mark_anime_watched', params={
        'anilist_id': str(anilist_id),
        'episode': str(episode),
        'percent_watched': str(percent_watched),
    })
    if res and res.get('success'):
        western = res.get('western_coordinates') or {}
        w_tmdb = western.get('tmdb_id')
        w_season = western.get('season')
        w_ep = western.get('episode')
        coord_str = f'TMDB #{w_tmdb} S{int(w_season):02d}E{int(w_ep):02d}' if (w_tmdb and w_season is not None and w_ep is not None) else f'TMDB #{w_tmdb or "N/A"}'
        action_word = 'Watched' if float(percent_watched) >= 90 else 'Unwatched'
        notification(f'{action_word}: {title} -> {coord_str}', 4000)
        kodi_refresh()
    else:
        err = (res or {}).get('error') or 'Failed to update anime watched status'
        notification(err, 3500)


def show_anime_mapping_info(params):
    """
    Calls both `/anime/resolve` and `/anime/aliases` for `(anilist_id, episode)` and displays
    a detailed diagnostic text window for easy testing of Layer 1 & Layer 2 mappings.
    """
    anilist_id = params.get('anilist_id')
    episode = params.get('episode', '1')
    title = params.get('title') or f'AniList #{anilist_id}'

    resolve_res = _get_data_via_ipc('resolve_anime_coordinates', params={
        'anilist_id': str(anilist_id),
        'episode': str(episode),
    }) or {}
    aliases_res = _get_data_via_ipc('get_anime_aliases', params={
        'anilist_id': str(anilist_id),
        'episode': str(episode),
    }) or {}

    ids = aliases_res.get('ids') or {}
    lines = [
        f'[B][COLOR FF90EE90]=== Layer 1: Global Identity & Cross-References ===[/COLOR][/B]',
        f'• AniList ID: {anilist_id}',
        f'• MyAnimeList (MAL) ID: {ids.get("mal_id") or resolve_res.get("mal_id") or "None"}',
        f'• AniDB ID: {ids.get("anidb_id") or "None"}',
        f'• Kitsu ID: {ids.get("kitsu_id") or "None"}',
        f'• TMDB ID: {resolve_res.get("tmdb_id") or ids.get("tmdb_id") or "None"}',
        f'• TVDB ID: {resolve_res.get("tvdb_id") or ids.get("tvdb_id") or "None"}',
        f'• IMDb ID: {resolve_res.get("imdb_id") or ids.get("imdb_id") or "None"}',
        f'• Format / Type: {aliases_res.get("anime_type") or resolve_res.get("media_type") or "Unknown"}',
        f'• Release Year: {aliases_res.get("season_year") or "Unknown"}',
        '',
        f'[B][COLOR FFADD8E6]=== Layer 2: Episode Coordinate Translation (Ep {episode}) ===[/COLOR][/B]',
        f'• Source Coordinate: anilist:{anilist_id} (Absolute Episode {episode})',
        f'• Resolved Media Type: {resolve_res.get("media_type")}',
        f'• Resolved TMDB ID: {resolve_res.get("tmdb_id")}',
        f'• Resolved Western Season: {resolve_res.get("season")}',
        f'• Resolved Western Episode: {resolve_res.get("episode")}',
        f'• Mapping Source: {resolve_res.get("mapping_source")}',
        f'• 1:1 Fallback Used: {resolve_res.get("fallback_used")}',
        '',
        f'[B][COLOR FFFFFFB3]=== Extracted Title Aliases ===[/COLOR][/B]',
        f'• Romaji Titles: {", ".join(aliases_res.get("romaji") or ["None"])}',
        f'• English Titles: {", ".join(aliases_res.get("english") or ["None"])}',
        f'• Native (Kanji/Kana): {", ".join(aliases_res.get("native") or ["None"])}',
        f'• Synonyms ({len(aliases_res.get("synonyms") or [])}): {", ".join((aliases_res.get("synonyms") or [])[:10])}',
        '',
        f'[B][COLOR FFCCB0FF]=== Generated Scraper Search Queries (Ep {episode}) ===[/COLOR][/B]',
    ]
    for q in (aliases_res.get('search_queries') or []):
        lines.append(f'  - {q}')

    show_text(f'Anime Bridge Inspector: {title}', '\n'.join(lines))


def show_anime_bridge_status(params):
    """
    Fetches `/anime/status` from Orac and displays database row counts and sync watermarks,
    offering an option to trigger `/anime/sync_mappings`.
    """
    status = _get_data_via_ipc('get_anime_status')
    if not status or not status.get('success'):
        notification('Failed to fetch Anime Bridge status from Orac', 3500)
        return

    ident_cnt = status.get('identities_count', 0)
    alias_cnt = status.get('aliases_count', 0)
    rule_cnt = status.get('episode_mapping_rules_count', 0)
    ov_cnt = status.get('custom_overrides_count', 0)
    manami_ts = _format_timestamp(status.get('manami_last_synced'))
    manami_ver = status.get('manami_upstream_date') or 'N/A'
    anibridge_ts = _format_timestamp(status.get('anibridge_last_synced'))
    anibridge_ver = status.get('anibridge_schema_version') or 'N/A'
    al_user = status.get('anilist_user') or ('Connected' if status.get('anilist_authenticated') else 'Not Linked')
    mal_auth = 'Connected' if status.get('mal_authenticated') else 'Not Linked'

    msg = (
        f"[B]Layer 1 (Manami Offline DB):[/B] {ident_cnt:,} identities | {alias_cnt:,} aliases\n"
        f"Last Synced: {manami_ts} (Upstream: {manami_ver})\n\n"
        f"[B]Layer 2 (AniBridge Mappings):[/B] {rule_cnt:,} rules | {ov_cnt:,} custom overrides\n"
        f"Last Synced: {anibridge_ts} (Schema: {anibridge_ver})\n\n"
        f"[B]Scrobblers:[/B] AniList: {al_user} | MyAnimeList: {mal_auth}\n\n"
        f"Would you like to trigger a background re-sync of the Anime datasets now?"
    )
    if confirm_dialog(heading='Orac Anime Dual-Indexing Bridge Status', text=msg, ok_label='Sync Now', cancel_label='Close'):
        sync_res = _get_data_via_ipc('sync_anime_mappings')
        if sync_res and sync_res.get('success'):
            notification('Anime dataset sync started in background on Orac', 3500)
        else:
            notification('Failed to start Anime dataset sync', 3500)
