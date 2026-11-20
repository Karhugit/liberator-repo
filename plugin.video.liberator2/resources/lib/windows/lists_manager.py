# -*- coding: utf-8 -*-
from collections import OrderedDict
import json
from core.kodi import dialog_select, logger, notification
from core.settings import trakt_user
from orac.client import OracClientError, get_orac_client
from windows.base import BaseDialog

SOURCE_COLORS = {
    'trakt':      'FFADD8E6',
    'mdblist':    'FF90EE90',
    'tmdb':       'FFFFFFB3',
    'simkl':      'FFCCB0FF',
    'punchplay':  'FFFFC04D',
    'imdb':       'FFFFB6C1',
    'orac_local': 'FF00FFCC',
    'local':      'FF00FFCC',
}
COLOR_CYCLE = ('FFADD8E6', 'FF90EE90', 'FFFFFFB3', 'FFCCB0FF', 'FFFFB6C1')


def _source_color(source, cycle_idx):
    if source in SOURCE_COLORS:
        return SOURCE_COLORS[source]
    color = COLOR_CYCLE[cycle_idx[0] % len(COLOR_CYCLE)]
    cycle_idx[0] += 1
    return color


class ListsManager(BaseDialog):
    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename)
        self.window_id = 2000
        self.lists = kwargs.get('lists', [])
        self.category_name = kwargs.get('category_name', 'Lists')
        self.selected_list = None

    def onInit(self):
        self.setProperty('category_name', self.category_name)
        self._populate()
        self.set_focus_id(self.window_id)

    def _populate(self):
        grouped = OrderedDict()
        for entry in self.lists:
            src = (entry.get('source') or 'unknown').lower()
            grouped.setdefault(src, []).append(entry)

        items = []
        cycle_idx = [0]
        for src, entries in grouped.items():
            color = _source_color(src, cycle_idx)
            header = self.make_listitem()
            header.setLabel(f'[COLOR {color}][B]{src.upper()}[/B][/COLOR]')
            header.setProperties({
                'source': src.upper(),
                'source_color': color,
                'is_header': 'true',
                'item_data': '',
            })
            items.append(header)

            for entry in entries:
                name = entry.get('name') or 'Unknown'
                owner = entry.get('owner') or entry.get('user') or ''
                in_lib = bool(entry.get('add_to_library', False))
                status = 'In Library' if in_lib else 'Not in Library'
                status_color = 'FF00FF00' if in_lib else 'FFFF8C00'

                li = self.make_listitem()
                li.setLabel(name)
                li.setProperties({
                    'owner': owner,
                    'source': src.upper(),
                    'source_color': color,
                    'item_count': str(entry.get('item_count', 0)),
                    'status': status,
                    'status_color': status_color,
                    'is_header': 'false',
                    'item_data': json.dumps(entry),
                })
                items.append(li)

        self.add_items(self.window_id, items)

    def run(self):
        self.doModal()
        self.clearProperties()
        return self.selected_list

    def onClick(self, control_id):
        if control_id != self.window_id:
            return
        li = self.get_listitem(self.window_id)
        if not li or li.getProperty('is_header') == 'true':
            return
        raw = li.getProperty('item_data')
        if not raw:
            return
        self.selected_list = json.loads(raw)
        self.close()

    def onAction(self, action):
        if action in self.closing_actions:
            self.selected_list = None
            self.close()
        elif action in self.context_actions:
            self._handle_context()

    def _handle_context(self):
        li = self.get_listitem(self.window_id)
        if not li or li.getProperty('is_header') == 'true':
            return
        raw = li.getProperty('item_data')
        if not raw:
            return
        entry = json.loads(raw)

        in_lib = bool(entry.get('add_to_library', False))
        toggle_label = 'Remove from Library' if in_lib else 'Add to Library'
        options = [toggle_label]

        user = entry.get('user', '')
        source = (entry.get('source') or '').lower()
        if source == 'trakt' and user not in ('trakt', trakt_user()):
            options.append('Unlike List')

        idx = dialog_select(entry.get('name', 'List Options'), options)
        if idx < 0:
            return
        choice = options[idx]

        if choice in ('Add to Library', 'Remove from Library'):
            update_action = 'Add' if choice == 'Add to Library' else 'Remove'
            self._toggle_library(li, entry, update_action)
        elif choice == 'Unlike List':
            self._unlike_list(entry)

    def _toggle_library(self, li, entry, update_action):
        try:
            res = get_orac_client().update_list_library_status({
                'name': 'update_library_status',
                'list_name': entry.get('name', ''),
                'user': entry.get('user', ''),
                'slug': entry.get('slug', ''),
                'item_type': entry.get('item_type', 'movie'),
                'update': update_action,
            }) or {}
            if res.get('status') == 'success':
                in_lib = update_action == 'Add'
                entry['add_to_library'] = in_lib
                li.setProperties({
                    'status': 'In Library' if in_lib else 'Not in Library',
                    'status_color': 'FF00FF00' if in_lib else 'FFFF8C00',
                    'item_data': json.dumps(entry),
                })
                notification(f"{'Added to' if in_lib else 'Removed from'} library")
            else:
                notification(f"Update failed: {res.get('message', 'Unknown error')}")
        except OracClientError as exc:
            logger('ListsManager', f'Toggle library failed: {exc}')
            notification(str(exc))

    def _unlike_list(self, entry):
        try:
            res = get_orac_client().unlike_trakt_list({
                'name': 'unlike_trakt_list',
                'list_name': entry.get('name', ''),
                'user': entry.get('user', ''),
                'slug': entry.get('slug', ''),
            }) or {}
            if res.get('status') == 'success':
                notification(f"Unliked '{entry.get('name', '')}'")
                self.close()
            else:
                notification('Failed to unlike list')
        except OracClientError as exc:
            notification(str(exc))
