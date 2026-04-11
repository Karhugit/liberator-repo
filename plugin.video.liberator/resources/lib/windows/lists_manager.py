# -*- coding: utf-8 -*-
import json
from windows.base_window import BaseDialog
from modules import kodi_utils
from caches.settings_cache import get_setting

logger = kodi_utils.logger
build_url = kodi_utils.build_url
addon_fanart = kodi_utils.addon_fanart()

class ListsManager(BaseDialog):
    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, *args)
        self.window_id = 2000
        self.lists = kwargs.get('lists', [])
        self.category_name = kwargs.get('category_name', 'Lists')
        self.item_type = kwargs.get('item_type', 'movie')
        self.selected_list = None

    def onInit(self):
        self.setProperty('category_name', self.category_name)
        self.make_items()
        self.setFocusId(self.window_id)

    def make_items(self):
        items = []
        trakt_user = get_setting('liberator.trakt.user')

        # Group lists by source
        from collections import OrderedDict
        grouped = OrderedDict()
        for item in self.lists:
            source = item.get('source', 'unknown').lower()
            grouped.setdefault(source, []).append(item)

        for source, source_lists in grouped.items():
            # Section header (non-selectable)
            header = self.make_listitem()
            header.setLabel('[B]%s[/B]' % source.upper())
            header.setProperty('is_header', 'true')
            header.setProperty('item_data', '')
            items.append(header)

            for item in source_lists:
                try:
                    listitem = self.make_listitem()
                    name = item.get('name', 'Unknown')
                    user = item.get('user', '')
                    owner = item.get('owner', user)
                    count = str(item.get('item_count', 0))
                    add_to_library = item.get('add_to_library', False)
                    slug = item.get('slug', '')

                    status = "In Library" if add_to_library else "Not in Library"
                    status_color = "FF00FF00" if add_to_library else "FFCCCCCC"

                    listitem.setLabel(name)
                    listitem.setProperty('owner', owner)
                    listitem.setProperty('source', source.upper())
                    listitem.setProperty('item_count', count)
                    listitem.setProperty('status', status)
                    listitem.setProperty('status_color', status_color)
                    listitem.setProperty('is_header', 'false')

                    # Store full item data for retrieval
                    listitem.setProperty('item_data', json.dumps(item))

                    # Context Menu
                    cm = []
                    if add_to_library:
                        cm.append(('Remove from Library', 'Remove'))
                    else:
                        cm.append(('Add to Library', 'Add'))

                    if source == 'trakt' and user != 'trakt' and user != trakt_user:
                        cm.append(('Unlike List', 'Unlike'))

                    listitem.addContextMenuItems(cm)
                    items.append(listitem)
                except Exception as e:
                    logger("ListsManager", f"Error processing item: {e}")

        self.add_items(self.window_id, items)

    def run(self):
        self.doModal()
        return self.selected_list

    def onClick(self, controlId):
        if controlId == self.window_id:
            item = self.get_listitem(self.window_id)
            if item:
                if item.getProperty('is_header') == 'true':
                    return  # Ignore clicks on section headers
                item_data = item.getProperty('item_data')
                if not item_data:
                    return
                self.selected_list = json.loads(item_data)
                self.close()

    def onAction(self, action):
        if action in self.closing_actions:
            self.selected_list = None
            self.close()
        
        # Handle Context Menu Actions (if not handled natively by the skin/Kodi, 
        # usually addContextMenuItems handles the display, but the action execution 
        # might need interception if not using RunPlugin)
        # However, BaseDialog logic might require us to define how context menu actions are mapped.
        elif action in self.context_actions:
            self.onContext()

    def context_menu(self, item):
        # We can override this if we want a custom context menu dialog, 
        # but since we added items via addContextMenuItems, Kodi handles it.
        # But wait, BaseDialog usually needs to handle the return from CM?
        # Looking at sources.py, it builds a manual select_dialog for context menu.
        # Let's stick to simple addContextMenuItems for now, where actions are strings passed to RunPlugin?
        # Wait, inside a modal dialog, RunPlugin might not work as expected or might close the dialog?
        # Let's check `sources.py` again. 
        # It uses `self.context_actions` and calls `self.context_menu(source)`.
        pass

    def onContext(self):
        try:
            full_listitem = self.get_listitem(self.window_id)
            if not full_listitem: return
            if full_listitem.getProperty('is_header') == 'true': return  # Skip headers
            
            item_data = json.loads(full_listitem.getProperty('item_data'))
            
            options = []
            
            # Library Logic
            add_to_library = item_data.get('add_to_library', False)
            if add_to_library:
                options.append("Remove from Library")
            else:
                 options.append("Add to Library")

             # Unlike (if Trakt Liked List)
            user = item_data.get('user', '')
            source = item_data.get('source', '')
            trakt_user = get_setting('liberator.trakt.user')
            if source == 'trakt' and (user != 'trakt' and user != trakt_user):
                 options.append("Unlike List")
            
            if not options: return

            choice = kodi_utils.select_dialog(options, heading=item_data.get('name'))
            if choice is None: return
            
            action = choice
            
            if action == "Add to Library":
                self.update_library(item_data, 'Add')
            elif action == "Remove from Library":
                self.update_library(item_data, 'Remove')
            elif action == "Unlike List":
                self.unlike_list(item_data)

        except Exception as e:
            logger("ListsManager", f"Context Menu Error: {e}")

    def update_library(self, item, update_action):
        from indexers.orac_lists import add_orac_list_to_library
        # params needed by add_orac_list_to_library
        params = {
            'list_name': item.get('name'),
            'item_type': self.item_type, 
            'url': 'dummy', # Not strictly needed for logic but function might expect it
            'update': update_action,
            'user': item.get('user'),
            'slug': item.get('slug')
        }
        
        # We call the function directly (imported)
        result = add_orac_list_to_library(params, None)
        
        if result and result.get('status') == 'success':
            # Update local list item status to reflect change immediately
            # Or simplified: Close and Re-open? 
            # Ideally update property of current listitem
            selected_pos = self.get_position(self.window_id)
            # Toggle value in our local list copy
            item['add_to_library'] = (update_action == 'Add')
            
            # Re-draw list? Or update single item?
            # Easiest is to close and let caller refresh, or update item properties.
            self.refresh_list_item(selected_pos, item)

    def unlike_list(self, item):
        from indexers.orac_lists import unlike_orac_list
        params = {
            'list_name': item.get('name'),
            'user': item.get('user'),
            'slug': item.get('slug')
        }
        result = unlike_orac_list(params, None)
        if result and result.get('status') == 'success':
             # Remove item from list
             # self.removeItem(self.window_id, self.get_position(self.window_id)) # Not available in standard API easily?
             # Just close to refresh
             self.close()

    def refresh_list_item(self, index, item):
        # Re-create the listitem at this index
        # Kodi Python API doesn't allow easy "UpdateItem" at index for all properties?
        # Let's just update the listitem in place if we can get it
        listitem = self.get_listitem(self.window_id) # This gets selected item
        
        status = "In Library" if item['add_to_library'] else "Not in Library"
        status_color = "FF00FF00" if item['add_to_library'] else "FFCCCCCC"
        
        listitem.setProperty('status', status)
        listitem.setProperty('status_color', status_color)
        listitem.setProperty('item_data', json.dumps(item))
