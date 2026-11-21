# -*- coding: utf-8 -*-
from core.kodi import (
    ADDON_PATH,
    add_dir,
    add_items,
    build_url,
    current_view_id,
    end_directory,
    make_dir_item,
    notification,
    open_settings,
    save_view_mode,
    set_category,
    set_content,
    set_sort_method,
    set_view_mode,
)
from core.shortcuts import get_menu_items

RUN_PLUGIN = 'RunPlugin(%s)'


class Navigator:
    def __init__(self, handle, params):
        self.handle = handle
        self.params = params
        self._items = []

    def _add(self, params, label, icon='folder', is_folder=True, cm_items=None):
        self._items.append(make_dir_item(params, label, icon=icon, is_folder=is_folder, cm_items=cm_items))

    def _finish(self, category='Liberator 2', content='files'):
        add_items(self.handle, self._items)
        set_content(self.handle, content)
        set_category(self.handle, category)
        set_sort_method(self.handle, 'none')
        end_directory(self.handle)
        set_view_mode('main', content)

    def main(self):
        items = get_menu_items('RootList')
        for idx, item in enumerate(items):
            url_params = {'mode': item.get('mode', 'navigator.main')}
            if item.get('params') and isinstance(item['params'], dict):
                url_params.update(item['params'])
            cm = [
                ('[B]Move[/B]', RUN_PLUGIN % build_url({
                    'mode': 'menu_editor.move', 'active_list': 'RootList', 'position': str(idx)
                })),
                ('[B]Rename[/B]', RUN_PLUGIN % build_url({
                    'mode': 'menu_editor.rename', 'active_list': 'RootList', 'position': str(idx)
                })),
                ('[B]Remove[/B]', RUN_PLUGIN % build_url({
                    'mode': 'menu_editor.remove', 'active_list': 'RootList', 'position': str(idx)
                })),
                ('[B]Restore Default Menu[/B]', RUN_PLUGIN % build_url({
                    'mode': 'menu_editor.restore', 'active_list': 'RootList'
                })),
            ]
            self._add(
                url_params,
                item.get('name', 'Menu Item'),
                icon=item.get('icon', 'folder'),
                is_folder=bool(item.get('is_folder', True)),
                cm_items=cm,
            )
        self._finish('Liberator 2')

    def movies(self):
        self._add(
            {'mode': 'lists.get_lists', 'list_type': 'my_lists', 'item_type': 'movie', 'category_name': 'My Movie Lists'},
            'My Lists', icon='trakt'
        )
        self._add(
            {'mode': 'lists.get_lists', 'list_type': 'generic_lists', 'item_type': 'movie', 'category_name': 'Generic Movie Lists'},
            'Generic Lists', icon='trakt'
        )
        self._add({'mode': 'recommendations.movies', 'category_name': 'Movie Recommendations'}, 'Recommendations', icon='trending')
        self._add({'mode': 'indexer.internal', 'item_type': 'movie'}, 'Movie Indexes', icon='lists')
        self._add({'mode': 'indexer.external', 'media_type': 'movie'}, 'Discover / External Indexes', icon='discover')
        self._add({'mode': 'movies.collections'}, 'Collections', icon='box_office')
        self._finish('Movies')

    def tvshows(self):
        self._add(
            {'mode': 'lists.get_lists', 'list_type': 'my_lists', 'item_type': 'tvshow', 'category_name': 'My TV Lists'},
            'My Lists', icon='trakt'
        )
        self._add(
            {'mode': 'lists.get_lists', 'list_type': 'generic_lists', 'item_type': 'tvshow', 'category_name': 'Generic TV Lists'},
            'Generic Lists', icon='trakt'
        )
        self._add({'mode': 'tv.next_episodes', 'category_name': 'Next Episodes'}, 'Next Episodes', icon='next_episodes')
        self._add({'mode': 'indexer.internal', 'item_type': 'tvshow'}, 'TV Show Indexes', icon='lists')
        self._add({'mode': 'indexer.internal', 'item_type': 'episode'}, 'Episode Indexes', icon='lists')
        self._add({'mode': 'indexer.external', 'media_type': 'tvshow'}, 'Discover / External Indexes', icon='discover')
        self._finish('TV Shows')

    def my_library(self):
        self._add({'mode': 'navigator.movies'}, 'Movies', icon='movies')
        self._add({'mode': 'navigator.tvshows'}, 'TV Shows', icon='tv')
        self._add({'mode': 'tags.menu'}, 'Tag Manager', icon='settings')
        self._add({'mode': 'lists.force_sync', 'isFolder': 'false'}, 'Force Orac Resync', icon='settings', is_folder=False)
        self._finish('My Library')

    def anime(self):
        self._add({'mode': 'anime.list', 'list_type': 'trending', 'name': 'Trending Anime'}, 'Trending Anime', icon='anime')
        self._add({'mode': 'anime.list', 'list_type': 'popular', 'name': 'Popular Anime'}, 'Popular Anime', icon='anime')
        self._add({'mode': 'anime.list', 'list_type': 'airing', 'name': 'Currently Airing'}, 'Currently Airing', icon='anime')
        self._add({'mode': 'anime.seasonal', 'name': 'Seasonal Anime'}, 'Seasonal Anime', icon='anime')
        self._add({'mode': 'anime.list', 'list_type': 'top_rated', 'name': 'Top Rated Anime'}, 'Top Rated Anime', icon='anime')
        self._add({'mode': 'anime.list', 'list_type': 'upcoming', 'name': 'Upcoming Anime'}, 'Upcoming Anime', icon='anime')
        self._add({'mode': 'anime.list', 'list_type': 'movies', 'name': 'Anime Movies'}, 'Anime Movies', icon='movies')
        self._add({'mode': 'anime.my_lists', 'name': 'My AniList'}, 'My AniList', icon='trakt')
        self._add({'mode': 'anime.search', 'name': 'Search Anime'}, 'Search Anime', icon='search', is_folder=False)
        self._add({'mode': 'anime.status', 'name': 'Anime Bridge Status'}, 'Anime Bridge Status & Sync', icon='settings', is_folder=False)
        self._finish('Anime')

    def search(self):
        self._add({'mode': 'search.query', 'media_type': 'movie'}, 'Search Movies', icon='search', is_folder=False)
        self._add({'mode': 'search.query', 'media_type': 'tvshow'}, 'Search TV Shows', icon='search', is_folder=False)
        self._add({'mode': 'search.query', 'media_type': 'people'}, 'Search People', icon='genre_family', is_folder=False)
        self._finish('Search')

    def premium(self):
        self._add({'mode': 'cloud.pm_files'}, 'Cloud Storage', icon='premiumize')
        self._add({'mode': 'cloud.pm_transfers'}, 'Transfers', icon='premiumize')
        self._add({'mode': 'cloud.pm_account'}, 'Account Info', icon='premiumize', is_folder=False)
        self._finish('Premiumize Cloud')

    def tools(self):
        self._add({'mode': 'navigator.open_settings'}, 'Addon Settings', icon='settings', is_folder=False)
        self._add({'mode': 'navigator.view_modes'}, 'Set View Modes', icon='settings')
        self._add({'mode': 'navigator.test_orac'}, 'Test Orac Connection', icon='settings', is_folder=False)
        self._add({'mode': 'lists.force_sync'}, 'Force Orac Resync', icon='settings', is_folder=False)
        self._add({'mode': 'navigator.changelog'}, 'View Changelog', icon='lists', is_folder=False)
        self._finish('Tools & Settings')


def open_addon_settings(handle, params):
    open_settings()


def test_orac_connection(handle, params):
    from orac.client import OracClientError, OracNotConfiguredError, get_orac_client

    try:
        client = get_orac_client()
        client.get_lists({'list_type': 'my_lists'})
        notification(f'Connected to Orac at {client.base_url}')
    except OracNotConfiguredError:
        notification('Orac server address is not set in settings.')
        open_settings()
    except OracClientError as exc:
        notification(f'Orac connection failed: {exc}')


VIEW_MODE_OPTIONS = (
    ('Main Menus', 'main', 'files'),
    ('Movies', 'view.movies', 'movies'),
    ('TV Shows', 'view.tvshows', 'tvshows'),
    ('Seasons', 'view.seasons', 'seasons'),
    ('Episodes', 'view.episodes', 'episodes'),
)


def view_modes(handle, params):
    view_key = params.get('view_key')
    if not view_key:
        for label, key, content in VIEW_MODE_OPTIONS:
            add_dir(
                handle,
                {'mode': 'navigator.view_modes', 'view_key': key, 'content': content, 'name': label},
                f'Set {label} View',
                icon='settings',
                is_folder=True,
            )
        set_content(handle, 'files')
        set_category(handle, 'Set View Modes')
        set_sort_method(handle, 'none')
        end_directory(handle)
        return

    content = params.get('content', 'files')
    label = params.get('name', view_key)
    add_dir(
        handle,
        {'mode': 'navigator.save_view', 'view_key': view_key, 'name': label},
        f'[B]Switch to desired view, then click here to Save ({label})[/B]',
        icon='settings',
        is_folder=False,
    )
    set_content(handle, content)
    set_category(handle, f'Set {label} View')
    set_sort_method(handle, 'none')
    end_directory(handle, cache_to_disc=False)


def save_view(handle, params):
    view_key = params.get('view_key')
    label = params.get('name', view_key)
    if not view_key:
        return
    vid = current_view_id()
    if vid:
        save_view_mode(view_key, vid)
        notification(f'Saved {label} view mode ({vid})')
    else:
        notification('Could not detect current view ID')


def view_changelog(handle, params):
    import os
    import xbmcgui

    path = os.path.join(ADDON_PATH, 'resources', 'text', 'changelog.txt')
    try:
        with open(path, 'r', encoding='utf-8') as fh:
            text = fh.read()
    except OSError:
        notification('Changelog not found.')
        return
    xbmcgui.Dialog().textviewer('Liberator 2 Changelog', text)
