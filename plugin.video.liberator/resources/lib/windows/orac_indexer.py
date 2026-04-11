# -*- coding: utf-8 -*-
import json
from datetime import datetime, timedelta
from windows.base_window import BaseDialog
import re
from apis import tmdb_api
from modules import kodi_utils, meta_lists
from modules.utils import safe_string, remove_accents
from apis.orac_api import _get_data_via_ipc
# from modules.kodi_utils import logger

kodi_dialog, select_dialog, ok_dialog, get_icon = kodi_utils.kodi_dialog, kodi_utils.select_dialog, kodi_utils.ok_dialog, kodi_utils.get_icon
sleep, container_refresh, confirm_dialog = kodi_utils.sleep, kodi_utils.container_refresh, kodi_utils.confirm_dialog
years_movies, years_tvshows, movie_genres, tvshow_genres, languages = meta_lists.years_movies, meta_lists.years_tvshows, meta_lists.movie_genres, meta_lists.tvshow_genres, meta_lists.languages
movie_certifications, networks, movie_certifications = meta_lists.movie_certifications, meta_lists.networks, meta_lists.movie_certifications
watch_providers_movies, watch_providers_tvshows = meta_lists.watch_providers_movies, meta_lists.watch_providers_tvshows
movie_sorts, tvshow_sorts, status_tvshows = meta_lists.movie_sorts, meta_lists.tvshow_sorts, meta_lists.status_tvshows
ui_languages = meta_lists.ui_languages

discover_items_tvshows = {
'with_lists': {'label': 'Lists', 'key': 'with_lists', 'display_key': 'with_lists_display', 'action': 'lists',
'filter_key': 'with_lists', 'name_value': ' | Lists: %s', 'icon': 'lists'},
'first_air_date_gte': {'label': 'First Air Date >=', 'key': 'first_air_date_gte', 'display_key': 'first_air_date_display', 'action': 'startDate',
'filter_key': 'first_air_date.gte', 'name_value': ' | from %s', 'icon': 'calender'},
'first_air_date_lte': {'label': 'First Air Date <=', 'key': 'first_air_date_lte', 'display_key': 'first_air_date_lte_display', 'action': 'startDate',
'filter_key': 'first_air_date.lte', 'name_value': ' | up to %s', 'icon': 'calender'},
'air_date_gte': {'label': 'Air Date >=', 'key': 'air_date_gte', 'display_key': 'air_date_gte_display', 'action': 'startDate',
'filter_key': 'air_date.gte', 'name_value': ' | from %s', 'icon': 'calender'},
'air_date_lte': {'label': 'Air Date <=', 'key': 'air_date_lte', 'display_key': 'air_date_lte_display', 'action': 'startDate',
'filter_key': 'air_date.lte', 'name_value': ' | up to %s', 'icon': 'calender'},
'with_networks': {'label': 'Networks', 'key': 'with_networks', 'display_key': 'with_network_display', 'action': 'networks',
'filter_key': 'with_networks', 'name_value': ' | %s','icon': 'networks'},
'with_status': {'label': 'TV Show Status', 'key': 'with_status', 'display_key': 'with_status_display', 'action': 'status',
'filter_key': 'with_status', 'name_value': ' | %s', 'icon': 'status'}
}

discover_items_movies = {
'primary_release_date_gte': {'label': 'Primary Release Date >=', 'key': 'primary_release_date_gte', 'display_key': 'primary_release_date_gte_display', 'action': 'startDate',
'filter_key': 'primary_release_date.gte', 'name_value': ' | from %s', 'icon': 'calender'},
'primary_release_date_lte': {'label': 'Primary Release Date <=', 'key': 'primary_release_date_lte', 'display_key': 'primary_release_date_lte_display', 'action': 'startDate',
 'filter_key': 'primary_release_date.lte', 'name_value': ' | up to %s', 'icon': 'calender'},
'with_certification': {'label': 'Certification', 'key': 'with_certification', 'display_key': 'with_certification_display', 'action': 'certifications',
'filter_key': 'certification', 'name_value': ' | %s', 'icon': 'certifications'},
'with_certification_and_lower': {'label': 'Certification (& lower)', 'key': 'with_certification_and_lower', 'display_key': 'with_certification_and_lower_display',
'action': 'certification_and_lowers', 'filter_key': 'certification.lte', 'name_value': ' | %s', 'icon': 'certifications'},
'with_cast': {'label': 'Include Cast', 'key': 'with_cast', 'display_key': 'with_cast_display', 'action': 'casts',
'filter_key': 'with_cast', 'name_value': ' | with %s', 'icon': 'people'},
'with_adult': {'label': 'Include Adult', 'key': 'with_adult', 'display_key': 'with_adult_display', 'action': 'adult',
'filter_key': 'include_adult', 'name_value': ' | Include Adult', 'icon': 'genre_romance'},
}


discover_items_shared = {
'with_genres': {'label': 'With Genres', 'key': 'with_genres', 'display_key': 'with_genres_display', 'action': 'genres',
'filter_key': 'with_genres', 'name_value': ' | %s', 'icon': 'genres'},
'without_genres': {'label': 'Without Genres', 'key': 'without_genres', 'display_key': 'without_genres_display', 'action': 'genres',
'filter_key': 'without_genres', 'name_value': ' | exclude %s', 'icon': 'genres'},
'with_original_language': {'label': 'With Original Language', 'key': 'with_original_language', 'display_key': 'with_original_language_display', 'action': 'languages',
'filter_key': 'with_original_language', 'name_value': ' | %s', 'icon': 'languages'},
'with_provider': {'label': 'Provider', 'key': 'with_provider', 'display_key': 'with_provider_display', 'action': 'provider',
'filter_key': 'with_watch_providers', 'name_value': ' | %s', 'icon': 'providers'},
'with_keywords': {'label': 'With Keywords', 'key': 'with_keywords', 'display_key': 'with_keywords_display', 'action': 'keywords',
'filter_key': 'with_keywords', 'name_value': ' | Keywords: %s', 'icon': 'genre_fantasy'},
'with_rating': {'label': 'Minimum Rating', 'key': 'with_rating', 'display_key': 'with_rating_display', 'action': 'ratings',
'filter_key': 'vote_average.gte', 'name_value': ' | %s+', 'icon': 'most_watched'},
'with_rating_votes': {'label': 'Minimum Number of Votes', 'key': 'with_rating_votes', 'display_key': 'with_rating_votes_display', 'action': 'votes',
'filter_key': 'vote_count.gte', 'name_value': ' | %s votes', 'icon': 'most_voted'},
'with_sort': {'label': 'Sort By', 'key': 'with_sort', 'display_key': 'with_sort_display', 'action': 'sort',
'filter_key': 'sort_by', 'name_value': ' | %s', 'icon': 'lists'},
'with_origin_country': {'label': 'Origin Country', 'key': 'with_origin_country', 'display_key': 'with_origin_country_display', 'action': 'countries',
'filter_key': 'with_origin_country', 'name_value': ' | %s', 'icon': 'countries'},
'with_language': {'label': 'UI Language', 'key': 'with_language', 'display_key': 'with_language_display', 'action': 'ui_language', 
'filter_key': 'language', 'name_value': ' | UI: %s', 'icon': 'languages'},
'add_to_library': {'label': 'Add to Library', 'key': 'add_to_library', 'display_key': 'add_to_library_display', 'action': 'library',
'filter_key': 'add_to_library', 'name_value': ' | Add to Library', 'icon': 'lists'}
}

filter_list_id = 2100
button_ids = (10, 11)
button_actions = {10: 'Save and Exit', 11: 'Exit'}
default_key_values = ('key', 'display_key')

class OracIndexer(BaseDialog):
    discover_items = {}

    def __init__(self, *args, **kwargs):
        BaseDialog.__init__(self, *args)
        # Initialize basic attributes FIRST
        self.label = ''
        self.filter_dict = {}
        
        self.media_type = kwargs.get('media_type')
        self.setProperty('media_type_label', '%sS' % self.media_type.upper())
        if self.media_type == 'movie':
            self.discover_items = {**discover_items_movies, **discover_items_shared}
        else: # tvshow
            self.discover_items = {**discover_items_tvshows, **discover_items_shared}
        
        self.set_starting_constants(kwargs)
        # set_starting_constants already calls set_attributes_status() at the end
        # so we don't need to call it here

    def onInit(self):
        self.make_menu()

    def run(self):
        self.doModal()
        self.clearProperties()


    def onClick(self, controlID):
        if controlID == filter_list_id:
            try:
                self.list_item = self.get_listitem(filter_list_id)
                self.chosen_item = self.discover_items[self.list_item.getProperty('key')]
                selection = self.selection_action()
                
                if selection == 'clear':
                    current_position = self.get_position(filter_list_id)
                    self.refresh_menu(current_position)
                    active_attributes = self.get_active_attributes()
                    if active_attributes:
                        self.filter_dict = self.make_filter_dict(active_attributes)
                        self.make_label(active_attributes)
                        self.set_attributes_status('true')
                    else:
                        self.set_attributes_status('false')
                        
                elif selection:
                    current_position = self.get_position(filter_list_id)
                    exec('self.%s()' % self.chosen_item['action'])
                    
                    # Refresh menu if genres were changed (handled in set_key_values now)
                    # No need to do it here anymore
                    
                    active_attributes = self.get_active_attributes()
                    if active_attributes:
                        self.filter_dict = self.make_filter_dict(active_attributes)
                        self.make_label(active_attributes)
                        self.set_attributes_status('true')
                    else: 
                        self.set_attributes_status('false')
                        
                self.chosen_item = None
            except:
                self.chosen_item = None
                return
                
        elif controlID in button_ids:
            refresh_listings = False
            if controlID == 10:
                label = kodi_dialog().input('List Name', defaultt=self.label)
                if not label: return
                refresh_listings = True
                
                # Extract add_to_library value if present
                add_to_library_value = self.filter_dict.pop('add_to_library', None)
                
                payload = {
                    'item_type': self.media_type, 
                    'label': label,
                    'parameters': self.filter_dict
                }
                
                # Add add_to_library as a separate parameter if it exists
                if add_to_library_value == 'True':
                    payload['add_to_library'] = True
                
                result = _get_data_via_ipc('add_ext_index', json_body=payload)
            self.close()
            if refresh_listings:
                sleep(500)
                container_refresh()


    def make_menu(self):
        def builder():
            with_genres_set = self.get_attribute(self, 'with_genres_display')
            without_genres_set = self.get_attribute(self, 'without_genres_display')
            for key, values in self.discover_items.items():
                kodi_utils.logger("orac_indexer", f"Processing filter key: {key}")
                if key == 'with_genres' and without_genres_set: continue
                if key == 'without_genres' and with_genres_set: continue
                if 'certification' in key:
                    if key == 'with_certification' and self.with_certification_and_lower: continue
                    if key == 'with_certification_and_lower' and self.with_certification: continue
                if self.media_type == 'tvshow':
                    if key == 'with_networks' and self.with_provider: continue
                    if key == 'with_provider' and self.with_networks: continue
                listitem = self.make_listitem()
                listitem.setProperty('label1', values['label'])
                try: listitem.setProperty('label2', self.get_attribute(self, values['display_key']))
                except: pass
                try: listitem.setProperty('icon', get_icon(values['icon']))
                except: listitem.setProperty('icon', get_icon('discover'))
                listitem.setProperty('key', key)
                yield listitem
        self.add_items(filter_list_id, list(builder()))
        self.setFocusId(filter_list_id)

    def startDate(self):
        user_input = kodi_dialog().input(self.chosen_item['label'])
        if not user_input: return
        final_date = None
        date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
        offset_pattern = re.compile(r'^[Tt]([+-])(\d{1,3})$')
        if date_pattern.match(user_input):
            try:
                datetime.strptime(user_input, '%Y-%m-%d')
                final_date = user_input
            except ValueError:
                ok_dialog(text='Invalid date format. Please use YYYY-MM-DD.')
                return
        else:
            match = offset_pattern.match(user_input)
            if match:
                days = int(match.group(2))
                if 1 <= days <= 365:
                    final_date = user_input.upper()
                else:
                    ok_dialog(text='Offset must be between 1 and 365 days.')
                    return
            else:
                ok_dialog(text='Invalid format. Use YYYY-MM-DD or T+/-X (e.g., T-7, T+30).')
                return
        if final_date:
            self.set_key_values(final_date, final_date)

# Shared functions

    def genres(self):
        genres = movie_genres if self.media_type == 'movie' else tvshow_genres
        choice = self.multiselect_dialog(self.chosen_item['label'], [{'name': i['name'], 'icon': get_icon(i['icon'])} for i in genres], genres)
        if choice != None: self.set_key_values('|'.join([i['id'] for i in choice]), '|'.join([i['name'] for i in choice]))

    def languages(self):
        current_values = self.get_attribute(self, self.chosen_item['display_key']).split('| ')
        preselect = [i for i, j in enumerate(languages) if j['name'] in current_values]
        dialog_list = [{'name': i['name']} for i in languages]
        choices = self.multiselect_dialog(self.chosen_item['label'], dialog_list, languages, preselect)
        if choices is not None: self.set_key_values('|'.join([i['id'] for i in choices]), '|'.join([i['name'] for i in choices]))

    def lists(self):
        # Fetch all lists from Orac
        ipc_params = {'name': 'my_lists', 'item_type': 'all', 'exclude_empty': 'false'}
        all_lists = _get_data_via_ipc('get_lists', params=ipc_params)
        
        if not all_lists:
            ok_dialog(text='No lists found.')
            return

        # Prepare list for dialog
        # Use user|slug as ID to be unique
        dialog_list = []
        for l in all_lists:
            user = l.get('user', '')
            slug = l.get('slug', '')
            name = l.get('name', '')
            list_id = f"{user}|{slug}"
            dialog_list.append({'name': name, 'id': list_id})

        # Preselect existing
        current_ids = self.get_attribute(self, self.chosen_item['key']).split(',')
        preselect = [i for i, item in enumerate(dialog_list) if item['id'] in current_ids]
        
        choices = self.multiselect_dialog(self.chosen_item['label'], dialog_list, dialog_list, preselect)
        
        if choices is not None:
            # Store IDs as comma separated: user|slug,user|slug
            ids_str = ','.join([i['id'] for i in choices])
            # Display names comma separated
            names_str = ', '.join([i['name'] for i in choices])
            self.set_key_values(ids_str, names_str)


    def ui_language(self):
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in ui_languages], ui_languages)
        if choice != None: self.set_key_values(str(choice['id']), str(choice['name']))

    def library(self):
        if not self.get_attribute(self, self.chosen_item['display_key']): self.set_key_values('True', 'True')
        else: self.set_key_values('', '')

    def keywords(self):
        keyword = kodi_dialog().input(self.chosen_item['label'])
        if not keyword: return
        payload =   {
            'item_type': self.media_type, 
            'keyword': keyword,
        }
        result = _get_data_via_ipc('get_tmdb_keywords', json_body=payload)
        if not result or not result.get('success'): return ok_dialog()
        
        keywords_list = result.get('keywords', [])
        if not keywords_list: return ok_dialog()
        
        choice = self.multiselect_dialog(self.chosen_item['label'], [{'name': i} for i in keywords_list], keywords_list)
        if choice != None:
            self.set_key_values(','.join(choice), ', '.join(choice))

    def provider(self):
        providers = watch_providers_movies if self.media_type == 'movie' else watch_providers_tvshows
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in providers], providers)
        if choice != None: self.set_key_values(str(choice['id']), str(choice['name']))

    def ratings(self):
        ratings = [{'name': str(float(i)), 'id': str(i)} for i in range(1,11)]
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in ratings], ratings)
        if choice != None: self.set_key_values(choice['id'], choice['name'])

    def votes(self):
        votes = [{'name': '1', 'id': '1'}] + [{'name': str(i), 'id': str(i)} for i in range(50, 1001, 50)]
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in votes], votes)
        if choice != None: self.set_key_values(choice['id'], choice['name'])

    def sort(self):
        if self.media_type == 'movie': sort_by_list = movie_sorts
        else: sort_by_list = tvshow_sorts
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in sort_by_list], sort_by_list)
        if choice != None: self.set_key_values(choice['id'], choice['name'])

    def countries(self):
        country_list = meta_lists.regions
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in country_list], country_list)
        if choice != None: self.set_key_values(str(choice['id']), str(choice['name']))


# TV Show functions

    def networks(self):
        network_list = sorted(networks, key=lambda k: k['name'])
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in network_list], network_list)
        if choice != None: self.set_key_values(str(choice['id']), str(choice['name']))

    def status(self):
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in status_tvshows], status_tvshows)
        if choice != None: self.set_key_values(str(choice['id']), str(choice['name']))

# Movie functions

# Undefined

    def years(self):
        years = years_movies if self.media_type == 'movie' else years_tvshows
        if self.chosen_item['key'] == 'first_air_date_gte' and self.with_year_end_display: years = [i for i in years if i['id'] <= int(self.with_year_end_display)]
        elif self.first_air_date_display: years = [i for i in years if i['id'] >= int(self.first_air_date_display)]
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in years], years)
        if choice != None: self.set_key_values(f"{choice['id']}-12-31", str(choice['id']))





# Done to here



    def certifications(self):
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in movie_certifications], movie_certifications)
        if choice != None: self.set_key_values(str(choice['id']), str(choice['name']))

    def certification_and_lowers(self):
        movie_and_lower_certifications = [{'name': '%s and lower' % i['name'], 'id': i['id']} for i in movie_certifications if not i['id'] == 'g']
        choice = self.selection_dialog(self.chosen_item['label'], [{'name': i['name']} for i in movie_and_lower_certifications], movie_and_lower_certifications)
        if choice != None: self.set_key_values(str(choice['id']), str(choice['name']))


    def casts(self):
        result, actor_id, search_name = None, None, None
        search_name = kodi_dialog().input(self.chosen_item['label'])
        if not search_name: return
        try: result = tmdb_api.tmdb_people_info(search_name)['results']
        except: result = None
        if not result: return ok_dialog()
        actor_list = []
        append = actor_list.append
        if len(result) > 1:
            for item in result:
                name = item['name']
                known_for_list = [i.get('title') for i in item['known_for'] if i.get('title', 'NA') != 'NA']
                known_for = ', '.join(known_for_list) if known_for_list else ''
                if item.get('profile_path'): icon = 'https://image.tmdb.org/t/p/h632/%s' % item['profile_path']
                else: icon = get_icon('genre_family')
                append({'line1': name, 'line2': known_for, 'icon': icon, 'name': name, 'id': item['id']})
            kwargs = {'items': json.dumps(actor_list), 'heading': self.chosen_item['label'], 'enumerate': 'false', 'multi_line': 'true'}
            choice = select_dialog(actor_list, **kwargs)
        else: choice = result[0]
        if choice != None: self.set_key_values(choice['id'], choice['name'])


    def adult(self):
        if not self.get_attribute(self, self.chosen_item['display_key']): self.set_key_values('true', 'True')
        else: self.set_key_values('', '')

    def selection_action(self):
        current_value = self.get_attribute(self, self.chosen_item['display_key'])
        if not current_value or self.chosen_item['key'] in ('with_released', 'with_adult', 'add_to_library'): return True
        clear_value = confirm_dialog(heading='Orac Indexer', text='Value of [B]%s[/B] already exists.[CR]Change current value or Clear current value?' % current_value,
                                                ok_label='Clear', cancel_label='Change', default_control=11)
        if clear_value is None: return False
        self.set_key_values('', '')
        if clear_value:
            if self.chosen_item['key'] in ('with_genres', 'without_genres'):
                self.make_menu()
            return 'clear'
        return True

    def get_active_attributes(self):
        return {key: values for key, values in self.discover_items.items() if self.get_attribute(self, values['key'])}

    def make_filter_dict(self, active_attributes):
        filter_dict = {}
        for key in active_attributes:
            values = self.discover_items[key]
            filter_value = self.get_attribute(self, key)
            filter_key = values.get('filter_key')
            if not filter_key:
                if self.media_type == 'movie':
                    filter_key = values.get('filter_key_movie')
                else:
                    filter_key = values.get('filter_key_tvshow')
            if filter_key:
                filter_dict[filter_key] = filter_value

            # Special handling for certification
            if key in ('with_certification', 'with_certification_and_lower'):
                filter_dict['certification_country'] = 'US'

        return filter_dict

    def make_label(self, active_attributes):
        if self.is_edit:
            return
        label = '[B]%sS[/B]' % self.media_type.upper()
        ignore_year_end = False
        for key, values in active_attributes.items():
            attribute_value = self.get_attribute(self, values['display_key'])
            if key == 'first_air_date_gte':
                if 'with_year_end' in active_attributes:
                    ignore_year_end = True
                    year_end = self.get_attribute(self, self.discover_items['with_year_end']['display_key'])
                    if attribute_value == year_end: label_extend = ' | %s' % attribute_value
                    else: label_extend = ' | %s-%s' % (attribute_value, year_end)
                else: label_extend = values['name_value'] % attribute_value
            elif key == 'with_year_end':
                if ignore_year_end: continue
                label_extend = values['name_value'] % attribute_value
            elif key == 'with_released':
                if attribute_value == 'True': label_extend = values['name_value']
                else: continue
            elif key == 'with_adult':
                if attribute_value == 'True': label_extend = values['name_value']
                else: continue
            elif key == 'add_to_library':
                if attribute_value == 'True': label_extend = values['name_value']
                else: continue
            elif key == 'watched_status':
                if attribute_value == 'True': label_extend = values['name_value'] % 'Watched'
                else: label_extend = values['name_value'] % 'Unwatched'
            else: label_extend = values['name_value'] % attribute_value
            label += label_extend
        self.label = label

    def set_key_values(self, key_content, display_key_content):
        """Set key values and handle mutual exclusivity for genres."""
        current_position = self.get_position(filter_list_id)
        
        self.set_attribute(self, self.chosen_item['key'], key_content)
        self.set_attribute(self, self.chosen_item['display_key'], display_key_content)
        
        rebuild_menu = False
        
        # Handle genre mutual exclusivity
        if key_content:  # Only clear opposite if we're setting a value
            if self.chosen_item['key'] == 'with_genres':
                if self.get_attribute(self, 'without_genres'):
                    self.set_attribute(self, 'without_genres', '')
                    self.set_attribute(self, 'without_genres_display', '')
                    rebuild_menu = True
            elif self.chosen_item['key'] == 'without_genres':
                if self.get_attribute(self, 'with_genres'):
                    self.set_attribute(self, 'with_genres', '')
                    self.set_attribute(self, 'with_genres_display', '')
                    rebuild_menu = True
        
        # Update the current list item display
        self.list_item.setProperty('label2', display_key_content)
        
        # Rebuild menu if genres changed
        if rebuild_menu:
            self.refresh_menu(current_position)

    def refresh_menu(self, position=0):
        """Refresh the menu and restore focus position."""
        self.reset_window(filter_list_id)
        self.make_menu()
        self.select_item(filter_list_id, position)
        self.setFocusId(filter_list_id)

    def selection_dialog(self, heading, dialog_list, function_list=None):
        list_items = [{'line1': item['name']} for item in dialog_list]
        kwargs = {'items': json.dumps(list_items), 'heading': heading, 'narrow_window': 'true'}
        return select_dialog(function_list, **kwargs)

    def multiselect_dialog(self, heading, dialog_list, function_list=None, preselect= []):
        if not function_list: function_list = dialog_list
        list_items = [{'line1': item['name'], 'icon': item.get('icon', 'discover')} for item in dialog_list]
        kwargs = {'items': json.dumps(list_items), 'heading': heading, 'enumerate': 'false', 'multi_choice': 'true', 'preselect': preselect}
        return select_dialog(function_list, **kwargs)

    def set_attributes_status(self, status='false'):
        self.setProperty('active_attributes', status)
        if status == 'true':
            self.setProperty('list_label', self.label)
            self.setProperty('url_label', json.dumps(self.filter_dict))
        else:
            self.setProperty('list_label', '')
            self.setProperty('url_label', '')

    def set_starting_constants(self, kwargs):
        self.chosen_item, self.list_item, self.media_type, self.active_attributes, self.label, self.url = None, None, kwargs['media_type'], [], '', ''
        self.is_edit = kwargs.get('is_edit') == 'true'
        self.index_name = kwargs.get('index_name', '')
        for key, values in self.discover_items.items():
            for key_value in default_key_values: self.set_attribute(self, values[key_value], '')
        if self.is_edit:
                self.label, parameters = self.index_name, json.loads(kwargs['parameters'])
                if str(kwargs.get('add_to_library')) in ('True', 'true', '1'): parameters['add_to_library'] = 'True'
                for key, values in self.discover_items.items():
                    filter_key = values.get('filter_key')
                    if not filter_key:
                        if self.media_type == 'movie':
                            filter_key = values.get('filter_key_movie')
                        else:
                            filter_key = values.get('filter_key_tvshow')
                    if filter_key and filter_key in parameters:
                        param_value = parameters[filter_key]
                        self.set_attribute(self, values['key'], param_value)
                        if key == 'with_networks':
                            display_value = next((i['name'] for i in networks if str(i['id']) == str(param_value)), param_value)
                        elif key == 'with_status':
                            display_value = next((i['name'] for i in status_tvshows if str(i['id']) == str(param_value)), param_value)
                        elif key == 'with_genres' or key == 'without_genres':
                            genre_list = movie_genres if self.media_type == 'movie' else tvshow_genres
                            genre_ids = param_value.split('|')
                            genre_names = []
                            for genre_id in genre_ids:
                                genre_names.append(next((i['name'] for i in genre_list if str(i['id']) == genre_id), genre_id))
                            display_value = '|'.join(genre_names)
                        else: display_value = param_value
                        self.set_attribute(self, values['display_key'], display_value)
                self.active_attributes = self.get_active_attributes()
                if self.active_attributes:
                    self.filter_dict = self.make_filter_dict(self.active_attributes)
                    self.make_label(self.active_attributes)
                    self.set_attributes_status('true')
                else: self.set_attributes_status('false')