import sys
from apis.orac_api import _get_data_via_ipc
from modules import kodi_utils
from indexers.orac_tvshows import orac_tvshows
from indexers.orac_movies import orac_movies

logger = kodi_utils.logger
add_items, set_content, end_directory, set_category, set_view_mode = kodi_utils.add_items, kodi_utils.set_content, kodi_utils.end_directory, kodi_utils.set_category, kodi_utils.set_view_mode
notification, external = kodi_utils.notification, kodi_utils.external
build_url, kodi_dialog, execute_builtin, select_dialog = kodi_utils.build_url, kodi_utils.kodi_dialog, kodi_utils.execute_builtin, kodi_utils.select_dialog

class OracSearch:
    """
    Handles searching TMDb via the Orac service and displaying the results.
    """
    def __init__(self, params):
        self.params = params
        self.handle = int(sys.argv[1])
        self.is_external = external()
        self.key_id = self.params.get('key_id')
        self.media_type = self.params.get('media_type', '')
        self.name = self.params.get('name', 'Search Results for %s' % self.key_id)

    def search(self):
        logger("Liberator", "Orac Search called")
        logger("Liberator", f"Params: {self.params}")

        if not self.media_type or not self.key_id:
            return

        ipc_params = {'item_type': self.media_type, 'name': self.key_id}
        result = _get_data_via_ipc('search_tmdb', ipc_params)

        if not result:
            notification('No Results Found', 2500)
            end_directory(self.handle)
            return

        if self.media_type == 'tv_show':
            item_list = {'list': list(enumerate(result)), 'id_type': 'trakt_dict', 'custom_order': 'true'}
            list_items = orac_tvshows(item_list).worker(short=True)
            content_type = 'tvshows'
            view = 'view.tvshows'
        else:  # movie
            item_list = {'list': list(enumerate(result)), 'id_type': 'trakt_dict', 'custom_order': 'true'}
            list_items = orac_movies(item_list).worker()
            content_type = 'movies'
            view = 'view.movies'

        logger("Liberator", f"Found {len(list_items)} items for media_type: {self.media_type}")
        add_items(self.handle, list_items)
        set_content(self.handle, content_type)
        set_category(self.handle, self.name)
        end_directory(self.handle, cacheToDisc=False if self.is_external else True)
        if not self.is_external:
            set_view_mode(view, content_type, self.is_external)

def orac_search_tmdb(params):
    OracSearch(params).search()
    return False # Signal to the router that the directory has been handled.