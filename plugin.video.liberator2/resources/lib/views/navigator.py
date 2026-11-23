# -*- coding: utf-8 -*-
from core.kodi import (
    ADDON_PATH,
    add_dir,
    add_items,
    build_url,
    container_refresh,
    current_view_id,
    dialog_select,
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
from core.settings import (
    EPISODE_TITLE_FORMATS,
    episode_display_format,
    episode_title_format_label,
    set_setting,
    single_ep_display_format,
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
        from orac.client import OracClientError, get_orac_client

        services = []
        try:
            resp = get_orac_client().get_debrid_services() or {}
            services = resp.get('services') or []
        except OracClientError:
            # Backward-compatible fallback if Orac Server hasn't been restarted with /api/debrid/services
            services = [{
                'id': 'premiumize',
                'name': 'Premiumize.me',
                'icon': 'premiumize',
                'has_cloud': True,
                'has_history': True,
                'has_account': True,
            }]

        if not services:
            self._add(
                {'mode': 'noop'},
                'No services authorised on Orac Server (configure in Orac web dashboard)',
                icon='settings',
                is_folder=False,
            )
            self._finish('My Services')
            return

        for svc in services:
            svc_id = svc.get('id', '')
            svc_name = svc.get('name', svc_id.title())
            svc_icon = svc.get('icon', svc_id or 'folder')
            self._add(
                {
                    'mode': 'navigator.service_menu',
                    'service': svc_id,
                    'name': svc_name,
                    'icon': svc_icon,
                    'has_cloud': str(bool(svc.get('has_cloud', False))).lower(),
                    'has_history': str(bool(svc.get('has_history', False))).lower(),
                    'has_account': str(bool(svc.get('has_account', True))).lower(),
                },
                svc_name,
                icon=svc_icon,
            )
        self._finish('My Services')

    def service_menu(self):
        svc = (self.params.get('service') or '').lower()
        name = self.params.get('name') or svc.title()
        icon = self.params.get('icon') or svc or 'folder'
        has_cloud = self.params.get('has_cloud', 'true') == 'true'
        has_history = self.params.get('has_history', 'false') == 'true'
        has_account = self.params.get('has_account', 'true') == 'true'

        if svc == 'premiumize':
            self._add({'mode': 'cloud.pm_files', 'name': f'{name} Cloud Storage'}, 'Cloud Storage', icon=icon)
            self._add({'mode': 'cloud.pm_transfers', 'name': f'{name} History'}, 'History', icon=icon)
            self._add({'mode': 'cloud.account_info', 'service': svc, 'name': name}, 'Account Info', icon=icon, is_folder=False)
        else:
            if has_cloud:
                self._add({'mode': 'cloud.files', 'service': svc, 'name': f'{name} Cloud Storage', 'icon': icon}, 'Cloud Storage', icon=icon)
            if has_history:
                self._add({'mode': 'cloud.downloads', 'service': svc, 'name': f'{name} History', 'icon': icon}, 'History', icon=icon)
            if has_account:
                self._add({'mode': 'cloud.account_info', 'service': svc, 'name': name}, 'Account Info', icon=icon, is_folder=False)
        self._finish(name)

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
    if view_key == 'view.episodes':
        ep_fmt_items = (
            (
                'episode_display',
                'Episode Title Format (Season Lists)',
                episode_title_format_label(episode_display_format()),
            ),
            (
                'single_ep_display',
                'Single Episode Title Format (Next Episodes)',
                episode_title_format_label(single_ep_display_format(False)),
            ),
            (
                'single_ep_display_widget',
                'Single Episode Title Format (Widgets)',
                episode_title_format_label(single_ep_display_format(True)),
            ),
        )
        for setting_id, title_label, current_val in ep_fmt_items:
            add_dir(
                handle,
                {
                    'mode': 'navigator.set_ep_title_format',
                    'setting_id': setting_id,
                    'name': title_label,
                },
                f'{title_label}: [B]{current_val}[/B]',
                icon='tv',
                is_folder=False,
            )
    set_content(handle, content)
    set_category(handle, f'Set {label} View')
    set_sort_method(handle, 'none')
    end_directory(handle, cache_to_disc=False)


def set_ep_title_format(handle, params):
    setting_id = params.get('setting_id')
    heading = params.get('name') or 'Episode Title Format'
    if setting_id not in ('episode_display', 'single_ep_display', 'single_ep_display_widget'):
        return
    options = [f'{label}   [COLOR grey]({example})[/COLOR]' for _fid, label, example in EPISODE_TITLE_FORMATS]
    choice = dialog_select(heading, options)
    if choice < 0:
        return
    fid, label, _example = EPISODE_TITLE_FORMATS[choice]
    set_setting(setting_id, fid)
    notification(f'{heading}: {label}')
    container_refresh()


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
