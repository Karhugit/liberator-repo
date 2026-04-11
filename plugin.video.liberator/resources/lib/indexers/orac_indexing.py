# -*- coding: utf-8 -*-
from modules import kodi_utils
from windows.base_window import open_window

logger = kodi_utils.logger

class OracIndexing:
    def __init__(self, params={}):
        self.params = params

    def create_new_index(self):
        """
        Opens a dialog for the user to create a new index by selecting various TMDb parameters.
        This will be similar to the existing 'discover' feature.
        """
        logger("OracIndexing", "create_new_index called with params: %s" % self.params)
        # The media_type is now passed directly in the params from the navigator menu.
        media_type = self.params.get('media_type')
        if not media_type: return
        
        # Now open the index creation window, passing the media_type
        # This window would be a new XML file you create, similar to discover.xml
        open_window(('windows.orac_indexer', 'OracIndexer'), 'orac_indexer.xml', media_type=media_type)