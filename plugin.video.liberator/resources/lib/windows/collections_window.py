# -*- coding: utf-8 -*-
import json
from windows.base_window import BaseDialog
from apis.orac_api import _get_data_via_ipc
from modules import kodi_utils
import xbmcgui

class CollectionsWindow(BaseDialog):
    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, *args)
        self.collections_list_id = 2000
        self.movies_list_id = 2001
        self.collections_data = []
        self.current_collection_index = -1

    def run(self):
        self.doModal()

    def onInit(self):
        self.fetch_collections()
        self.populate_collections()
        self.setFocusId(self.collections_list_id)

    def fetch_collections(self):
        try:
            response = _get_data_via_ipc('get_collections')
            if response and response.get('success'):
                self.collections_data = response.get('collections', [])
        except Exception as e:
            kodi_utils.logger("CollectionsWindow", f"Error fetching collections: {e}")

    def populate_collections(self):
        items = []
        for index, collection in enumerate(self.collections_data):
            listitem = self.make_listitem()
            listitem.setLabel(collection.get('name', 'Unknown'))
            poster = collection.get('poster_path', '')
            if poster:
                poster_url = f"https://image.tmdb.org/t/p/w500{poster}"
                listitem.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url})
            listitem.setProperty('collection_index', str(index))
            listitem.setProperty('item_count', f"{len(collection.get('movies', []))} Movies")
            items.append(listitem)
        self.add_items(self.collections_list_id, items)
        
        if items:
            self.update_movies_list(0)

    def update_movies_list(self, collection_index):
        if collection_index == self.current_collection_index:
            return
        self.current_collection_index = collection_index
        try:
            collection = self.collections_data[collection_index]
            movies = collection.get('movies', [])
            items = []
            for movie in movies:
                listitem = self.make_listitem()
                listitem.setLabel(movie.get('title', 'Unknown'))
                poster = movie.get('poster_path', '')
                if poster:
                    poster_url = f"https://image.tmdb.org/t/p/w500{poster}"
                    listitem.setArt({'icon': poster_url, 'thumb': poster_url, 'poster': poster_url})
                listitem.setProperty('tmdb_id', str(movie.get('tmdb_id', '')))
                year_val = str(movie.get('release_date') or '')
                listitem.setProperty('year', year_val[:4])
                items.append(listitem)
            self.reset_window(self.movies_list_id)
            self.add_items(self.movies_list_id, items)
        except Exception as e:
            kodi_utils.logger("CollectionsWindow", f"Error updating movies list: {e}")

    def onAction(self, action):
        if action in self.closing_actions:
            self.close()
            return
        
        # Standard Kodi GUI navigation will update focus. 
        # Check if the focused item on the left list changed.
        try:
            focus_id = self.getFocusId()
            if focus_id == self.collections_list_id:
                selected_item = self.get_listitem(self.collections_list_id)
                if selected_item:
                    index_str = selected_item.getProperty('collection_index')
                    if index_str:
                        self.update_movies_list(int(index_str))
        except:
            pass

    def onClick(self, controlId):
        if controlId == self.movies_list_id:
            selected_item = self.get_listitem(self.movies_list_id)
            if selected_item:
                tmdb_id = selected_item.getProperty('tmdb_id')
                if tmdb_id:
                    self.close()
                    # Trigger standard movie search/playback
                    params = {
                        'mode': 'playback.media',
                        'media_type': 'movie',
                        'tmdb_id': tmdb_id
                    }
                    action = f"RunPlugin({kodi_utils.build_url(params)})"
                    kodi_utils.execute_builtin(action)

def open_collections_window(params):
    from windows.base_window import open_window
    open_window(
        ('windows.collections_window', 'CollectionsWindow'),
        'collections.xml'
    )
