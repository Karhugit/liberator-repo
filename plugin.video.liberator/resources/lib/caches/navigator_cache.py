# -*- coding: utf-8 -*-
from caches.base_cache import connect_database
from modules.kodi_utils import get_property, set_property, clear_property
# from modules.kodi_utils import logger

GET_LIST = 'SELECT list_contents FROM navigator WHERE list_name = ? AND list_type = ?'
SET_LIST = 'INSERT OR REPLACE INTO navigator VALUES (?, ?, ?)'
DELETE_LIST = 'DELETE FROM navigator WHERE list_name=? and list_type=?'
GET_FOLDERS = 'SELECT list_name, list_contents FROM navigator WHERE list_type = ?'
GET_FOLDER_CONTENTS = 'SELECT list_contents FROM navigator WHERE list_name = ? AND list_type = ?'
prop_dict = {'default': 'liberator_%s_default', 'edited': 'liberator_%s_edited', 'shortcut_folder': 'liberator_%s_shortcut_folder'}
tvshow_random_converts = {'navigator.genres': 'tmdb_tv_genres', 'navigator.providers': 'tmdb_tv_providers', 'navigator.networks': 'tmdb_tv_networks',
'navigator.languages': 'tmdb_tv_languages', 'navigator.years': 'tmdb_tv_year', 'navigator.decades': 'tmdb_tv_decade'}
anime_random_converts = {'navigator.genres': 'tmdb_anime_genres', 'navigator.providers': 'tmdb_anime_providers', 'navigator.years': 'tmdb_anime_year',
'navigator.decades': 'tmdb_anime_decade'}

root_list = [
{'name': 'My Library', 'mode': 'navigator.my_library', 'iconImage': 'lists'},
{'name': 'External Indexes', 'mode': 'navigator.index', 'iconImage': 'lists'},
{'name': 'Search', 'mode': 'navigator.search', 'iconImage': 'search'},
{'name': 'Lists Manager', 'mode': 'orac.list.list_manager', 'iconImage': 'lists'},
{'name': 'My Services', 'mode': 'navigator.premium', 'iconImage': 'premium'},
{'name': 'Favorites', 'mode': 'navigator.favorites', 'iconImage': 'favorites'},
{'name': 'Downloads', 'mode': 'navigator.downloads', 'iconImage': 'downloads'},
{'name': 'Tools', 'mode': 'navigator.tools', 'iconImage': 'settings2'}
            ]

index_list = [
    {'name': 'Create New Index', 'mode': 'orac.index_create_new', 'iconImage': 'lists', 'isFolder': 'false'},
    {'name': 'My Indexes', 'mode': 'index_manage_existing', 'iconImage': 'settings2'},
    {'name': 'Import Index', 'mode': 'index_import', 'iconImage': 'trending', 'isFolder': 'false'},  # Future feature
    {'name': 'Export Index', 'mode': 'index_export', 'iconImage': 'downloads', 'isFolder': 'false'},  # Future feature
]

main_menus = {'RootList': root_list, 'IndexList': index_list}

class NavigatorCache:
    def get_main_lists(self, list_name):
        if list_name == 'RootList':
            return root_list, None
        if list_name == 'IndexList':
            return index_list, None
        default_contents = self.get_memory_cache(list_name, 'default')
        if not default_contents:
            default_contents = self.get_list(list_name, 'default')
            if default_contents == None:
                self.rebuild_database()
                return self.get_main_lists(list_name)
            try: edited_contents = self.get_list(list_name, 'edited')
            except: edited_contents = None
        else: edited_contents = self.get_memory_cache(list_name, 'edited')
        return default_contents, edited_contents

    def get_list(self, list_name, list_type):
        contents = None
        try:
            dbcon = connect_database('navigator_db')
            contents = eval(dbcon.execute(GET_LIST, (list_name, list_type)).fetchone()[0])
        except: pass
        return contents

    def set_list(self, list_name, list_type, list_contents):
        dbcon = connect_database('navigator_db')
        dbcon.execute(SET_LIST, (list_name, list_type, repr(list_contents)))
        self.set_memory_cache(list_name, list_type, list_contents)

    def delete_list(self, list_name, list_type):
        dbcon = connect_database('navigator_db')
        dbcon.execute(DELETE_LIST, (list_name, list_type))
        self.delete_memory_cache(list_name, list_type)
        dbcon.execute('VACUUM')
    
    def get_memory_cache(self, list_name, list_type):
        try: return eval(get_property(self._get_list_prop(list_type) % list_name))
        except: return None
    
    def set_memory_cache(self, list_name, list_type, list_contents):
        set_property(self._get_list_prop(list_type) % list_name, repr(list_contents))

    def delete_memory_cache(self, list_name, list_type):
        clear_property(self._get_list_prop(list_type) % list_name)

    def get_shortcut_folders(self):
        try:
            dbcon = connect_database('navigator_db')
            folders = dbcon.execute(GET_FOLDERS, ('shortcut_folder',)).fetchall()
            folders = sorted([(str(i[0]), eval(i[1])) for i in folders], key=lambda s: s[0].lower())
        except: folders = []
        return folders

    def get_shortcut_folder_contents(self, list_name):
        try:
            dbcon = connect_database('navigator_db')
            contents = eval(dbcon.execute(GET_FOLDER_CONTENTS, (list_name, 'shortcut_folder')).fetchone()[0])
        except: contents = []
        return contents

    def currently_used_list(self, list_name):
        default_contents, edited_contents = self.get_main_lists(list_name)
        list_items = edited_contents or default_contents
        return list_items

    def rebuild_database(self):
        dbcon = connect_database('navigator_db')
        for list_name, list_contents in main_menus.items(): self.set_list(list_name, 'default', list_contents)

    def _get_list_prop(self, list_type):
        return prop_dict[list_type]
    
navigator_cache = NavigatorCache()
