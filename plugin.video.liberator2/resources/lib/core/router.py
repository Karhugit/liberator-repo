# -*- coding: utf-8 -*-
import importlib
from urllib.parse import parse_qsl
from core.kodi import end_directory, logger, notification

ROUTES = {
    'noop': None,

    # Navigation
    'navigator.main': ('views.navigator', 'Navigator.main'),
    'navigator.movies': ('views.navigator', 'Navigator.movies'),
    'navigator.tvshows': ('views.navigator', 'Navigator.tvshows'),
    'navigator.my_library': ('views.navigator', 'Navigator.my_library'),
    'navigator.anime': ('views.navigator', 'Navigator.anime'),
    'navigator.search': ('views.navigator', 'Navigator.search'),
    'navigator.premium': ('views.navigator', 'Navigator.premium'),
    'navigator.tools': ('views.navigator', 'Navigator.tools'),
    'navigator.open_settings': ('views.navigator', 'open_addon_settings'),
    'navigator.test_orac': ('views.navigator', 'test_orac_connection'),
    'navigator.changelog': ('views.navigator', 'view_changelog'),
    'navigator.view_modes': ('views.navigator', 'view_modes'),
    'navigator.save_view': ('views.navigator', 'save_view'),

    # Menu Editor & Shortcut Folders
    'menu_editor.move': ('core.shortcuts', 'menu_move'),
    'menu_editor.remove': ('core.shortcuts', 'menu_remove'),
    'menu_editor.rename': ('core.shortcuts', 'menu_rename'),
    'menu_editor.restore': ('core.shortcuts', 'menu_restore'),
    'shortcuts.folders': ('core.shortcuts', 'folders'),
    'shortcuts.folder_contents': ('core.shortcuts', 'folder_contents'),
    'shortcuts.folder_create': ('core.shortcuts', 'folder_create'),
    'shortcuts.folder_rename': ('core.shortcuts', 'folder_rename'),
    'shortcuts.folder_delete': ('core.shortcuts', 'folder_delete'),
    'shortcuts.folder_clear': ('core.shortcuts', 'folder_clear'),
    'shortcuts.add_to_folder': ('core.shortcuts', 'add_to_folder'),
    'shortcuts.item_move': ('core.shortcuts', 'item_move'),
    'shortcuts.item_rename': ('core.shortcuts', 'item_rename'),
    'shortcuts.item_remove': ('core.shortcuts', 'item_remove'),

    # Lists & Library
    'lists.get_lists': ('views.lists', 'get_lists'),
    'lists.build_list': ('views.lists', 'build_list'),
    'lists.manager_categories': ('views.lists', 'manager_categories'),
    'lists.manager_filtered': ('views.lists', 'manager_filtered'),
    'lists.manager_window': ('views.lists', 'manager_window'),
    'lists.toggle_library': ('views.lists', 'toggle_library'),
    'lists.unlike': ('views.lists', 'unlike_list'),
    'lists.manager_choice': ('views.lists', 'manager_choice'),
    'lists.force_sync': ('views.lists', 'force_sync'),

    # Windows
    'windows.extras': ('windows.extras', 'open_extras'),
    'windows.people': ('windows.people', 'open_person'),

    # TV Shows, Seasons, Episodes
    'tv.seasons': ('views.tv', 'seasons'),
    'tv.episodes': ('views.tv', 'episodes'),
    'tv.next_episodes': ('views.tv', 'next_episodes'),

    # Playback & Watched Status
    'playback.play': ('playback.sources', 'play'),
    'playback.trailer': ('playback.sources', 'trailer'),
    'watched.movie': ('playback.watched', 'mark_movie'),
    'watched.tvshow': ('playback.watched', 'mark_tvshow'),
    'watched.season': ('playback.watched', 'mark_season'),
    'watched.episode': ('playback.watched', 'mark_episode'),
    'watched.drop_tvshow': ('playback.watched', 'drop_tvshow'),

    # Search, Tags, Recommendations, Collections
    'search.query': ('views.search', 'query'),
    'search.results': ('views.search', 'results'),
    'tags.menu': ('views.tags', 'menu'),
    'tags.list': ('views.tags', 'list_items'),
    'tags.add': ('views.tags', 'add_tag'),
    'tags.remove': ('views.tags', 'remove_tag'),
    'recommendations.movies': ('views.recommendations', 'movies'),
    'recommendations.shelf': ('views.recommendations', 'shelf'),
    'movies.collections': ('views.movies', 'collections'),

    # Indexers & Discover
    'indexer.internal': ('views.indexer', 'internal'),
    'indexer.internal_create': ('views.indexer', 'internal_create'),
    'indexer.internal_delete': ('views.indexer', 'internal_delete'),
    'indexer.internal_view': ('views.indexer', 'internal_view'),
    'indexer.external': ('views.indexer', 'external_list'),
    'indexer.external_discover': ('views.indexer', 'external_discover'),
    'indexer.external_delete': ('views.indexer', 'external_delete'),

    # Anime
    'anime.list': ('views.anime', 'anime_list'),
    'anime.episodes': ('views.anime', 'anime_episodes'),
    'anime.seasonal': ('views.anime', 'seasonal_menu'),
    'anime.my_lists': ('views.anime', 'my_lists'),
    'anime.search': ('views.anime', 'search'),
    'anime.status': ('views.anime', 'status'),

    # Premiumize Cloud (via Orac)
    'cloud.pm_files': ('views.cloud', 'pm_files'),
    'cloud.pm_play': ('views.cloud', 'pm_play'),
    'cloud.pm_delete': ('views.cloud', 'pm_delete'),
    'cloud.pm_transfers': ('views.cloud', 'pm_transfers'),
    'cloud.pm_account': ('views.cloud', 'pm_account'),
}


def dispatch(argv):
    handle = int(argv[1])
    raw_qs = argv[2][1:] if len(argv) > 2 and argv[2].startswith('?') else (argv[2] if len(argv) > 2 else '')
    params = dict(parse_qsl(raw_qs, keep_blank_values=True))
    mode = params.get('mode', 'navigator.main')
    logger('Router', f'mode={mode} params={params}')

    if mode not in ROUTES:
        logger('Router', f'Unknown route: {mode}')
        notification(f'Route not supported: {mode}')
        end_directory(handle, cache_to_disc=False)
        return

    target = ROUTES[mode]
    if target is None:
        return

    module_path, attr_path = target
    mod = importlib.import_module(module_path)
    if attr_path.startswith('Navigator.'):
        method_name = attr_path.split('.', 1)[1]
        getattr(mod.Navigator(handle, params), method_name)()
    else:
        getattr(mod, attr_path)(handle, params)
