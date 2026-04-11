# -*- coding: utf-8 -*-
"""
Internal Index Dialog for Liberator - simplified indexer for local library filters.
V1: Genre filtering only (with_genres / without_genres).
"""
import json
import re
from datetime import datetime
from windows.base_window import BaseDialog
from modules import kodi_utils, meta_lists
from apis.orac_api import _get_data_via_ipc

kodi_dialog, select_dialog, get_icon = kodi_utils.kodi_dialog, kodi_utils.select_dialog, kodi_utils.get_icon
sleep, container_refresh, confirm_dialog = kodi_utils.sleep, kodi_utils.container_refresh, kodi_utils.confirm_dialog
movie_genres, tvshow_genres = meta_lists.movie_genres, meta_lists.tvshow_genres

# Expanded filters for V2/V3
discover_items = {
    'with_lists': {
        'label': 'Lists', 'key': 'with_lists', 'display_key': 'with_lists_display',
        'filter_key': 'with_lists', 'icon': 'lists', 'type': 'list'
    },
    'with_genres': {
        'label': 'With Genres', 'key': 'with_genres', 'display_key': 'with_genres_display',
        'filter_key': 'with_genres', 'icon': 'genres', 'type': 'genre'
    },
    'without_genres': {
        'label': 'Without Genres', 'key': 'without_genres', 'display_key': 'without_genres_display',
        'filter_key': 'without_genres', 'icon': 'genres', 'type': 'genre'
    },
    'with_tags': {
        'label': 'With Tags', 'key': 'with_tags', 'display_key': 'with_tags_display',
        'filter_key': 'with_tags', 'icon': 'lists', 'type': 'tag'
    },
    'min_year': {
        'label': 'Min Year', 'key': 'min_year', 'display_key': 'min_year_display',
        'filter_key': 'min_year', 'icon': 'calendar', 'type': 'input', 'media_type': 'movie'
    },
    'max_year': {
        'label': 'Max Year', 'key': 'max_year', 'display_key': 'max_year_display',
        'filter_key': 'max_year', 'icon': 'calendar', 'type': 'input', 'media_type': 'movie'
    },
    'min_first_aired_year': {
        'label': 'Min First Aired Year', 'key': 'min_first_aired_year', 'display_key': 'min_first_aired_year_display',
        'filter_key': 'min_first_aired_year', 'icon': 'calendar', 'type': 'input', 'media_type': 'tvshow'
    },
    'max_first_aired_year': {
        'label': 'Max First Aired Year', 'key': 'max_first_aired_year', 'display_key': 'max_first_aired_year_display',
        'filter_key': 'max_first_aired_year', 'icon': 'calendar', 'type': 'input', 'media_type': 'tvshow'
    },
    'min_runtime': {
        'label': 'Min Runtime (mins)', 'key': 'min_runtime', 'display_key': 'min_runtime_display',
        'filter_key': 'min_runtime', 'icon': 'runtime', 'type': 'input', 'media_type': 'movie'
    },
    'max_runtime': {
        'label': 'Max Runtime (mins)', 'key': 'max_runtime', 'display_key': 'max_runtime_display',
        'filter_key': 'max_runtime', 'icon': 'runtime', 'type': 'input', 'media_type': 'movie'
    },
    'min_rating': {
        'label': 'Min Rating', 'key': 'min_rating', 'display_key': 'min_rating_display',
        'filter_key': 'min_rating', 'icon': 'rating', 'type': 'input'
    },
    'min_votes': {
        'label': 'Min Votes', 'key': 'min_votes', 'display_key': 'min_votes_display',
        'filter_key': 'min_votes', 'icon': 'rating', 'type': 'input', 'media_type': 'tvshow'
    },
    'country': {
        'label': 'Country', 'key': 'country', 'display_key': 'country_display',
        'filter_key': 'country', 'icon': 'language', 'type': 'input'
    },
    'language': {
        'label': 'Language', 'key': 'language', 'display_key': 'language_display',
        'filter_key': 'language', 'icon': 'language', 'type': 'select_language'
    },
    'certification': {
        'label': 'Certification', 'key': 'certification', 'display_key': 'certification_display',
        'filter_key': 'certification', 'icon': 'cert', 'type': 'input'
    },
    'network': {
        'label': 'Network', 'key': 'network', 'display_key': 'network_display',
        'filter_key': 'network', 'icon': 'networks', 'type': 'input', 'media_type': 'tvshow'
    },
    'release_date_gte': {
        'label': 'Release Date >=', 'key': 'release_date_gte', 'display_key': 'release_date_gte_display',
        'filter_key': 'release_date.gte', 'icon': 'calendar', 'type': 'date', 'media_type': 'movie'
    },
    'release_date_lte': {
        'label': 'Release Date <=', 'key': 'release_date_lte', 'display_key': 'release_date_lte_display',
        'filter_key': 'release_date.lte', 'icon': 'calendar', 'type': 'date', 'media_type': 'movie'
    },
    'status': {
        'label': 'Status', 'key': 'status', 'display_key': 'status_display',
        'filter_key': 'status', 'icon': 'status', 'type': 'select', 'media_type': 'tvshow',
        'options': [
            {'name': 'All', 'value': ''}, 
            {'name': 'Returning Series', 'value': 'returning series'}, 
            {'name': 'Ended', 'value': 'ended'},
            {'name': 'In Production', 'value': 'in production'},
            {'name': 'Canceled', 'value': 'canceled'},
            {'name': 'Pilot', 'value': 'pilot'}
        ]
    },
    'dropped': {
        'label': 'Dropped', 'key': 'dropped', 'display_key': 'dropped_display',
        'filter_key': 'dropped', 'icon': 'trash', 'type': 'select', 'media_type': 'tvshow',
        'options': [{'name': 'All', 'value': ''}, {'name': 'Dropped', 'value': '1'}, {'name': 'Not Dropped', 'value': '0'}]
    },
    'min_user_rating': {
        'label': 'Min User Rating', 'key': 'min_user_rating', 'display_key': 'min_user_rating_display',
        'filter_key': 'min_user_rating', 'icon': 'rating', 'type': 'input'
    },
    'watched_status': {
        'label': 'Watched Status', 'key': 'watched_status', 'display_key': 'watched_status_display',
        'filter_key': 'watched_status', 'icon': 'watched', 'type': 'select', 
        'options': [
            {'name': 'All', 'value': ''}, 
            {'name': 'Unwatched', 'value': '0'}, 
            {'name': 'In Progress', 'value': '1'}, 
            {'name': 'Watched', 'value': '2'}
        ]
    },
    'air_date_gte': {
        'label': 'Air Date >=', 'key': 'air_date_gte', 'display_key': 'air_date_gte_display',
        'filter_key': 'air_date_gte', 'icon': 'calendar', 'type': 'date', 'media_type': 'episode'
    },
    'air_date_lte': {
        'label': 'Air Date <=', 'key': 'air_date_lte', 'display_key': 'air_date_lte_display',
        'filter_key': 'air_date_lte', 'icon': 'calendar', 'type': 'date', 'media_type': 'episode'
    },
    'first_air_date_gte': {
        'label': 'Show First Air Date >=', 'key': 'first_air_date_gte', 'display_key': 'first_air_date_gte_display',
        'filter_key': 'first_air_date_gte', 'icon': 'calendar', 'type': 'date', 'media_type': 'episode'
    },
    'first_air_date_lte': {
        'label': 'Show First Air Date <=', 'key': 'first_air_date_lte', 'display_key': 'first_air_date_lte_display',
        'filter_key': 'first_air_date_lte', 'icon': 'calendar', 'type': 'date', 'media_type': 'episode'
    },
    'episode_rating_gte': {
        'label': 'Min Episode Rating', 'key': 'episode_rating_gte', 'display_key': 'episode_rating_gte_display',
        'filter_key': 'episode_rating_gte', 'icon': 'rating', 'type': 'input', 'media_type': 'episode'
    },
    'episode_rating_lte': {
        'label': 'Max Episode Rating', 'key': 'episode_rating_lte', 'display_key': 'episode_rating_lte_display',
        'filter_key': 'episode_rating_lte', 'icon': 'rating', 'type': 'input', 'media_type': 'episode'
    },
    'episode_votes_gte': {
        'label': 'Min Episode Votes', 'key': 'episode_votes_gte', 'display_key': 'episode_votes_gte_display',
        'filter_key': 'episode_votes_gte', 'icon': 'most_voted', 'type': 'input', 'media_type': 'episode'
    },
    'sort_by': {
        'label': 'Sort By', 'key': 'sort_by', 'display_key': 'sort_by_display',
        'filter_key': 'sort_by', 'icon': 'lists', 'type': 'select', 'media_type': 'movie',
        'options': [
            {'name': 'Release Date (Newest)', 'value': 'release_date.desc'}, 
            {'name': 'Release Date (Oldest)', 'value': 'release_date.asc'},
            {'name': 'Rating (High to Low)', 'value': 'rating.desc'},
            {'name': 'Rating (Low to High)', 'value': 'rating.asc'},
            {'name': 'Title (A-Z)', 'value': 'title.asc'},
            {'name': 'Title (Z-A)', 'value': 'title.desc'},
            {'name': 'Random', 'value': 'random'}
        ]
    },
    'sort_by_tv': {
        'label': 'Sort By', 'key': 'sort_by_tv', 'display_key': 'sort_by_tv_display',
        'filter_key': 'sort_by', 'icon': 'lists', 'type': 'select', 'media_type': 'tvshow',
        'options': [
            {'name': 'Air Date (Newest)', 'value': 'first_air_date.desc'}, 
            {'name': 'Air Date (Oldest)', 'value': 'first_air_date.asc'},
            {'name': 'Rating (High to Low)', 'value': 'rating.desc'},
            {'name': 'Rating (Low to High)', 'value': 'rating.asc'},
            {'name': 'Title (A-Z)', 'value': 'title.asc'},
            {'name': 'Title (Z-A)', 'value': 'title.desc'},
            {'name': 'Random', 'value': 'random'}
        ]
    }
}

filter_list_id = 2100
button_ids = (10, 11)


class OracInternalIndexerDialog(BaseDialog):
    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, *args)
        self.label = ''
        self.status_label = ''
        self.filter_dict = {}
        self.media_type = kwargs.get('media_type', 'movie')
        self.is_edit = kwargs.get('is_edit') == 'true'
        self.index_name = kwargs.get('index_name', '')
        self.setProperty('media_type_label', '%sS' % self.media_type.upper())
        self._init_attributes(kwargs)

    def _init_attributes(self, kwargs):
        """Initialize filter attributes."""
        for key, values in discover_items.items():
            self.set_attribute(self, values['key'], '')
            self.set_attribute(self, values['display_key'], '')
        
        if self.is_edit and kwargs.get('parameters'):
            self.label = self.index_name
            params = json.loads(kwargs['parameters'])
            for key, values in discover_items.items():
                # Skip items not relevant to this media type
                item_media_type = values.get('media_type')
                if item_media_type and item_media_type != self.media_type:
                    continue
                filter_key = values.get('filter_key')
                if filter_key and filter_key in params:
                    param_value = str(params[filter_key])
                    self.set_attribute(self, values['key'], param_value)
                    
                    if values['type'] == 'genre':
                        # Map genre IDs to names for display
                        genre_list = movie_genres if self.media_type == 'movie' else tvshow_genres
                        genre_ids = param_value.split('|')
                        genre_names = [next((g['name'] for g in genre_list if str(g['id']) == gid), gid) for gid in genre_ids]
                        self.set_attribute(self, values['display_key'], '|'.join(genre_names))
                    elif values['type'] == 'select':
                        # Map value to display name
                        display_name = next((opt['name'] for opt in values['options'] if opt['value'] == param_value), param_value)
                        self.set_attribute(self, values['display_key'], display_name)
                    else:
                        self.set_attribute(self, values['display_key'], param_value)
            self._update_status()

    def onInit(self):
        self.make_menu()

    def run(self):
        self.doModal()
        self.clearProperties()

    def onClick(self, controlID):
        if controlID == filter_list_id:
            self._handle_filter_selection()
        elif controlID in button_ids:
            self._handle_button(controlID)

    def _handle_filter_selection(self):
        """Handle filter selection."""
        try:
            list_item = self.get_listitem(filter_list_id)
            key = list_item.getProperty('key')
            chosen_item = discover_items[key]
            
            # Check if clearing or setting
            current_value = self.get_attribute(self, chosen_item['display_key'])
            if current_value:
                clear = confirm_dialog(
                    heading='Internal Index',
                    text='Clear current value?',
                    ok_label='Clear', cancel_label='Change', default_control=11
                )
                if clear:
                    self.set_attribute(self, chosen_item['key'], '')
                    self.set_attribute(self, chosen_item['display_key'], '')
                    list_item.setProperty('label2', '')
                    self._update_status()
                    return
                elif clear is None:
                    return
            
            if chosen_item['type'] == 'genre':
                # Genre selection
                genres = movie_genres if self.media_type == 'movie' else tvshow_genres
                list_items = [{'line1': g['name'], 'icon': get_icon(g.get('icon', 'genres'))} for g in genres]
                kwargs_dialog = {'items': json.dumps(list_items), 'heading': chosen_item['label'], 'multi_choice': 'true'}
                choices = select_dialog(genres, **kwargs_dialog)
                
                if choices:
                    ids = '|'.join([str(g['id']) for g in choices])
                    names = '|'.join([g['name'] for g in choices])
                    self.set_attribute(self, chosen_item['key'], ids)
                    self.set_attribute(self, chosen_item['display_key'], names)
                    list_item.setProperty('label2', names)
                    
                    # Clear opposite genres if needed
                    if key in ('with_genres', 'without_genres'):
                        opposite_key = 'without_genres' if key == 'with_genres' else 'with_genres'
                        self.set_attribute(self, opposite_key, '')
                        self.set_attribute(self, discover_items[opposite_key]['display_key'], '')
                        self.refresh_menu()
            elif chosen_item['type'] == 'select':
                # Custom selection dialog
                options = chosen_item['options']
                list_items = [{'line1': opt['name']} for opt in options]
                kwargs_dialog = {'items': json.dumps(list_items), 'heading': chosen_item['label']}
                choice = select_dialog(options, **kwargs_dialog)
                if choice:
                    self.set_attribute(self, chosen_item['key'], choice['value'])
                    self.set_attribute(self, chosen_item['display_key'], choice['name'])
                    list_item.setProperty('label2', choice['name'])
            elif chosen_item['type'] == 'tag':
                # Fetch tags from Orac
                result = _get_data_via_ipc('tags', params={'action': 'get_all'})
                if not result or not result.get('success'):
                    kodi_utils.ok_dialog(text='No tags found.')
                    return
                
                tags = result.get('tags', [])
                if not tags:
                     kodi_utils.ok_dialog(text='No tags in database.')
                     return

                # Create list of dicts for select_dialog
                # Using strings directly if possible, or forcing dict structure
                tag_options = [{'name': t, 'value': t} for t in tags]
                
                # Preselect
                current_val = self.get_attribute(self, chosen_item['key'])
                current_ids = current_val.split('|') if current_val else []
                preselect = [i for i, item in enumerate(tag_options) if item['value'] in current_ids]

                kwargs_dialog = {'items': json.dumps([{'line1': t['name']} for t in tag_options]), 'heading': chosen_item['label'], 'multi_choice': 'true', 'preselect': preselect}
                choices = select_dialog(tag_options, **kwargs_dialog)
                
                if choices:
                    # Store as pipe separated string
                    val_str = '|'.join([c['value'] for c in choices])
                    self.set_attribute(self, chosen_item['key'], val_str)
                    self.set_attribute(self, chosen_item['display_key'], val_str)
                    list_item.setProperty('label2', val_str)
            elif chosen_item['type'] == 'date':
                # Date input with offset support
                value = kodi_dialog().input(chosen_item['label'], defaultt=current_value)
                if value:
                    final_date = None
                    import re
                    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
                    offset_pattern = re.compile(r'^[Tt]([+-])(\d{1,3})$')
                    if date_pattern.match(value):
                        from datetime import datetime
                        try:
                            datetime.strptime(value, '%Y-%m-%d')
                            final_date = value
                        except ValueError:
                            kodi_utils.ok_dialog(text='Invalid date format. Please use YYYY-MM-DD.')
                    else:
                        match = offset_pattern.match(value)
                        if match:
                            days = int(match.group(2))
                            if 1 <= days <= 365:
                                final_date = value.upper()
                            else:
                                kodi_utils.ok_dialog(text='Offset must be between 1 and 365 days.')
                        else:
                            kodi_utils.ok_dialog(text='Invalid format. Use YYYY-MM-DD or T+/-X (e.g., T-7, T+30).')
                    
                    if final_date:
                        self.set_attribute(self, chosen_item['key'], final_date)
                        self.set_attribute(self, chosen_item['display_key'], final_date)
                        list_item.setProperty('label2', final_date)
            elif chosen_item['type'] == 'list':
                # Fetch lists from Orac
                ipc_params = {'name': 'my_lists', 'item_type': 'all', 'exclude_empty': 'false'}
                all_lists = _get_data_via_ipc('get_lists', params=ipc_params)
                if not all_lists:
                    kodi_utils.ok_dialog(text='No lists found.')
                    return

                # Prepare list items
                dialog_list = [{'name': l['name'], 'id': f"{l.get('user')}|{l.get('slug')}"} for l in all_lists]
                
                # Preselect
                current_value = self.get_attribute(self, chosen_item['display_key'])
                current_ids = self.get_attribute(self, chosen_item['key']).split(',') if self.get_attribute(self, chosen_item['key']) else []
                preselect = [i for i, item in enumerate(dialog_list) if item['id'] in current_ids]
                
                kwargs_dialog = {'items': json.dumps([{'line1': item['name'], 'icon': kodi_utils.get_icon('lists')} for item in dialog_list]), 'heading': chosen_item['label'], 'multi_choice': 'true', 'preselect': preselect}
                
                choices = select_dialog(dialog_list, **kwargs_dialog)
                
                if choices:
                    # Store IDs comma separated
                    ids_str = ','.join([i['id'] for i in choices])
                    names_str = ', '.join([i['name'] for i in choices])
                    self.set_attribute(self, chosen_item['key'], ids_str)
                    self.set_attribute(self, chosen_item['display_key'], names_str)
                    list_item.setProperty('label2', names_str)
            elif chosen_item['type'] == 'select_language':
                # Fetch languages from Orac
                result = _get_data_via_ipc('get_available_languages')
                if not result or not result.get('success'):
                    kodi_utils.ok_dialog(text='No languages found.')
                    return
                
                languages = result.get('languages', [])
                if not languages:
                     kodi_utils.ok_dialog(text='No languages in database.')
                     return

                # Create list of dicts for select_dialog
                lang_options = [{'name': lang, 'value': lang} for lang in languages]
                
                kwargs_dialog = {'items': json.dumps([{'line1': l['name']} for l in lang_options]), 'heading': chosen_item['label']}
                choice = select_dialog(lang_options, **kwargs_dialog)
                
                if choice:
                    self.set_attribute(self, chosen_item['key'], choice['value'])
                    self.set_attribute(self, chosen_item['display_key'], choice['name'])
                    list_item.setProperty('label2', choice['name'])
            else:
                # Text/Numeric input
                value = kodi_dialog().input(chosen_item['label'], defaultt=current_value)
                if value:
                    self.set_attribute(self, chosen_item['key'], value)
                    self.set_attribute(self, chosen_item['display_key'], value)
                    list_item.setProperty('label2', value)
            
            self._update_status()
        except Exception:
            pass

    def _handle_button(self, controlID):
        """Handle save/exit buttons."""
        if controlID == 10:  # Save
            # If editing, use the original index_name as the default.
            # Otherwise use the generated summary label as a suggestion.
            default_name = self.index_name if self.is_edit else self.status_label
            label = kodi_dialog().input('Index Name', defaultt=default_name)
            if not label:
                return
            
            # Build parameters
            self.filter_dict = {}
            for key, values in discover_items.items():
                # Skip items not relevant to this media type
                item_media_type = values.get('media_type')
                if item_media_type and item_media_type != self.media_type:
                    continue
                val = self.get_attribute(self, values['key'])
                if val:
                    self.filter_dict[values['filter_key']] = val
            
            payload = {
                'item_type': self.media_type,
                'label': label,
                'parameters': self.filter_dict
            }
            if self.is_edit:
                payload['original_label'] = self.index_name
                
            result = _get_data_via_ipc('add_internal_index', json_body=payload)
            if result and result.get('status') == 'success':
                kodi_utils.notification(f'Index "{label}" saved.')
            else:
                kodi_utils.notification('Failed to save index.')
            self.close()
            sleep(500)
            container_refresh()
        else:  # Cancel
            self.close()

    def make_menu(self):
        """Build the filter menu."""
        def builder():
            with_genres_set = self.get_attribute(self, 'with_genres_display')
            without_genres_set = self.get_attribute(self, 'without_genres_display')
            for key, values in discover_items.items():
                # Filter by media type
                item_media_type = values.get('media_type')
                if item_media_type and item_media_type != self.media_type:
                    continue
                    
                # Mutually exclusive genres
                if key == 'with_genres' and without_genres_set:
                    continue
                if key == 'without_genres' and with_genres_set:
                    continue
                listitem = self.make_listitem()
                listitem.setProperty('label1', values['label'])
                listitem.setProperty('label2', self.get_attribute(self, values['display_key']) or '')
                listitem.setProperty('icon', get_icon(values['icon']))
                listitem.setProperty('key', key)
                yield listitem
        self.add_items(filter_list_id, list(builder()))
        self.setFocusId(filter_list_id)

    def refresh_menu(self):
        """Refresh the menu after changes."""
        position = self.get_position(filter_list_id)
        self.reset_window(filter_list_id)
        self.make_menu()
        self.select_item(filter_list_id, position)
        self.setFocusId(filter_list_id)

    def _update_status(self):
        """Update UI status based on active filters."""
        active = any(self.get_attribute(self, v['key']) for v in discover_items.values())
        self.setProperty('active_attributes', 'true' if active else 'false')
        if active:
            label_parts = ['[B]%sS[/B]' % self.media_type.upper()]
            for key, values in discover_items.items():
                display = self.get_attribute(self, values['display_key'])
                if display:
                    prefix = '' if key == 'with_genres' else 'exclude ' if key == 'without_genres' else '%s: ' % (values['label'].replace(' (mins)', ''))
                    label_parts.append('%s%s' % (prefix, display))
            self.status_label = ' | '.join(label_parts[1:]) if len(label_parts) > 1 else label_parts[0]
            self.setProperty('list_label', self.status_label)
        else:
            self.status_label = ''
            self.setProperty('list_label', '')


def open_internal_indexer_dialog(params):
    """Opens the internal indexer dialog."""
    from windows.base_window import open_window
    open_window(
        ('windows.orac_internal_indexer_dialog', 'OracInternalIndexerDialog'),
        'orac_indexer.xml',
        media_type=params.get('item_type', 'movie'),
        is_edit=params.get('is_edit', 'false'),
        index_name=params.get('index_id', ''),
        parameters=params.get('parameters', '{}')
    )
