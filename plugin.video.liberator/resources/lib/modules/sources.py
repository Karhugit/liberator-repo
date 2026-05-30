# -*- coding: utf-8 -*-
import json
import re
import time
import threading
from threading import Thread
import itertools, queue
from windows.base_window import open_window, create_window
from caches.episode_groups_cache import episode_groups_cache
from caches.settings_cache import get_setting
from scrapers import folders
from modules import debrid, kodi_utils, settings, metadata, watched_status
from modules.player import LiberatorPlayer
from modules.source_utils import get_cache_expiry, make_alias_dict, get_file_info, normalize
from modules.utils import clean_file_name, string_to_float, safe_string, remove_accents, get_datetime, append_module_to_syspath, manual_function_import, manual_module_import
from apis.orac_api import OracClient  # The global instance
from apis.orac_api import _get_data_via_ipc
logger = kodi_utils.logger

get_icon, notification, sleep, xbmc_monitor = kodi_utils.get_icon, kodi_utils.notification, kodi_utils.sleep, kodi_utils.xbmc_monitor
select_dialog, confirm_dialog, close_all_dialog = kodi_utils.select_dialog, kodi_utils.confirm_dialog, kodi_utils.close_all_dialog
show_busy_dialog, hide_busy_dialog, xbmc_player = kodi_utils.show_busy_dialog, kodi_utils.hide_busy_dialog, kodi_utils.xbmc_player
get_property, set_property, clear_property = kodi_utils.get_property, kodi_utils.set_property, kodi_utils.clear_property
auto_play, active_internal_scrapers, provider_sort_ranks, audio_filters = settings.auto_play, settings.active_internal_scrapers, settings.provider_sort_ranks, settings.audio_filters
check_prescrape_sources, auto_resume = settings.check_prescrape_sources, settings.auto_resume
store_resolved_to_cloud, source_folders_directory, watched_indicators = settings.store_resolved_to_cloud, settings.source_folders_directory, settings.watched_indicators
quality_filter, sort_to_top, tmdb_api_key, mpaa_region = settings.quality_filter, settings.sort_to_top, settings.tmdb_api_key, settings.mpaa_region
scraping_settings, include_prerelease_results = settings.scraping_settings, settings.include_prerelease_results
ignore_results_filter, results_sort_order, results_format, filter_status = settings.ignore_results_filter, settings.results_sort_order, settings.results_format, settings.filter_status
autoplay_next_episode, autoscrape_next_episode, limit_resolve = settings.autoplay_next_episode, settings.autoscrape_next_episode, settings.limit_resolve
orac_scraping = settings.orac_scraping
auto_episode_group, preferred_autoplay, debrid_enabled = settings.auto_episode_group, settings.preferred_autoplay, debrid.debrid_enabled

internal_include_list = ['easynews', 'rd_cloud', 'pm_cloud', 'ad_cloud', 'oc_cloud', 'tb_cloud']
external_exclude_list = ['easynews', 'gdrive', 'library', 'filepursuit', 'plexshare']
sd_check = ('SD', 'CAM', 'TELE', 'SYNC')
rd_info, pm_info, ad_info = ('apis.real_debrid_api', 'RealDebridAPI'), ('apis.premiumize_api', 'PremiumizeAPI'), ('apis.alldebrid_api', 'AllDebridAPI')
oc_info, ed_info, tb_info = ('apis.offcloud_api', 'OffcloudAPI'), ('apis.easydebrid_api', 'EasyDebridAPI'), ('apis.torbox_api', 'TorBoxAPI')
debrids = {'Real-Debrid': rd_info, 'rd_cloud': rd_info, 'rd_browse': rd_info, 'Premiumize.me': pm_info, 'pm_cloud': pm_info, 'pm_browse': pm_info,
            'AllDebrid': ad_info, 'ad_cloud': ad_info, 'ad_browse': ad_info, 'Offcloud': oc_info, 'oc_cloud': oc_info, 'oc_browse': oc_info,
            'EasyDebrid': ed_info, 'ed_cloud': ed_info, 'ed_browse': ed_info, 'TorBox': tb_info, 'tb_cloud': tb_info, 'tb_browse': tb_info}
debrid_providers = ('Real-Debrid', 'Premiumize.me', 'AllDebrid', 'Offcloud', 'EasyDebrid', 'TorBox')
debrid_token_dict = {'Real-Debrid': 'rd.token', 'Premiumize.me': 'pm.token', 'AllDebrid': 'ad.token', 'Offcloud': 'oc.token', 'EasyDebrid': 'ed.token', 'TorBox': 'tb.token'}
quality_ranks = {'4K': 1, '1080p': 2, '720p': 3, 'SD': 4, 'SCR': 5, 'CAM': 5, 'TELE': 5}
cloud_scrapers, folder_scrapers = ('rd_cloud', 'pm_cloud', 'ad_cloud', 'oc_cloud', 'tb_cloud'), ('folder1', 'folder2', 'folder3', 'folder4', 'folder5')
default_internal_scrapers = ('easynews', 'rd_cloud', 'pm_cloud', 'ad_cloud', 'oc_cloud', 'tb_cloud', 'folders')
main_line = '%s[CR]%s[CR]%s'
int_window_prop = 'liberator.internal_results.%s'
scraper_timeout = 25
filter_keys = {'hevc': '[B]HEVC[/B]', '3d': '[B]3D[/B]', 'hdr': '[B]HDR[/B]', 'dv': '[B]D/VISION[/B]', 'av1': '[B]AV1[/B]', 'enhanced_upscaled': '[B]AI ENHANCED/UPSCALED[/B]'}
preference_values = {0:100, 1:50, 2:20, 3:10, 4:5, 5:2}

# --- GLOBAL VARIABLE TO HOLD THE ORAC CLIENT INSTANCE ---
_orac_client_instance = None

def set_orac_client(client_instance):
    """
    Sets the global OracClient instance for this module.
    Called by the main router script.
    """
    global _orac_client_instance
    _orac_client_instance = client_instance
#    logger("Orac", "Episodes: OracClient instance set for module.")

class Sources():
    def __init__(self):
        self.params = {}
        self.orac_meta = None
        self.search_info = {}
        self.search_info_temp = {}
        self.prescrape_scrapers, self.prescrape_threads, self.prescrape_sources, self.uncached_results = [], [], [], []
        self.threads, self.providers, self.sources, self.internal_scraper_names, self.remove_scrapers = [], [], [], [], []
        self.rescrape_with_episode_group = False
        self.clear_properties, self.filters_ignored, self.active_folders, self.resolve_dialog_made, self.episode_group_used = True, False, False, False, False
        self.sources_total = self.sources_4k = self.sources_1080p = self.sources_720p = self.sources_sd = 0
        self.prescrape, self.disabled_ext_ignored = 'true', 'false'
        self.orac_movie_meta = None
        self.orac_scraping_initiated = False
        self.orac_episode_meta = None
        self.progress_dialog, self.progress_thread = None, None
        self.playing_filename = ''
        self.count_tuple = (('sources_4k', '4K', self._quality_length), ('sources_1080p', '1080p', self._quality_length), ('sources_720p', '720p', self._quality_length),
                            ('sources_sd', '', self._quality_length_sd), ('sources_total', '', self._quality_length_final))
        self.playback_successful = None
        self.scrape_start_time = time.time()

    def playback_prep(self, params=None):
        hide_busy_dialog()
        if params: self.params = params
        params_get = self.params.get
        self.play_type, self.background, self.prescrape = params_get('play_type', ''), params_get('background', 'false') == 'true', params_get('prescrape', self.prescrape) == 'true'
        self.random, self.random_continual = params_get('random', 'false') == 'true', params_get('random_continual', 'false') == 'true'
        if self.play_type:
            if self.play_type == 'autoplay_nextep': self.autoplay_nextep, self.autoscrape_nextep = True, False
            elif self.play_type == 'random_continual': self.autoplay_nextep, self.autoscrape_nextep = False, False
            else: self.autoplay_nextep, self.autoscrape_nextep = False, True
        else: self.autoplay_nextep, self.autoscrape_nextep = autoplay_next_episode(), autoscrape_next_episode()
        self.autoscrape = self.autoscrape_nextep and self.background
        self.orac_scraping = orac_scraping()
        self.auto_episode_group = auto_episode_group()
        self.nextep_settings, self.disable_autoplay_next_episode = params_get('nextep_settings', {}), params_get('disable_autoplay_next_episode', 'false') == 'true'        
        self.orac_strict_dedupe = settings.orac_strict_dedupe()
        self.ignore_scrape_filters = params_get('ignore_scrape_filters', 'false') == 'true'
        self.disabled_ext_ignored = params_get('disabled_ext_ignored', self.disabled_ext_ignored) == 'true'
        self.folders_ignore_filters = get_setting('liberator.results.folders_ignore_filters', 'false') == 'true'
        self.filter_size_method = int(get_setting('liberator.results.filter_size_method', '0'))
        self.media_type, self.tmdb_id = params_get('media_type'), params_get('tmdb_id')
        self.custom_title, self.custom_year = params_get('custom_title', None), params_get('custom_year', None)
        self.episode_group_label = params_get('episode_group_label', '')
        self.percent_watched = int(params_get('percent_watched', '0'))
        if self.media_type == 'episode':
# Add show_trakt_id
            self.show_trakt_id = params_get('show_trakt_id',0)
            self.season, self.episode = int(params_get('season')), int(params_get('episode'))
            self.custom_season, self.custom_episode = params_get('custom_season', None), params_get('custom_episode', None)
            self.check_episode_group()
        else: self.season, self.episode, self.custom_season, self.custom_episode = '', '', '', ''
        if 'autoplay' in self.params: self.autoplay = params_get('autoplay', 'false') == 'true'
        else: self.autoplay = auto_play(self.media_type)
        self.orac_meta = None
        self.get_meta()
        self.determine_scrapers_status()
        self.sleep_time, self.provider_sort_ranks, self.scraper_settings = 100, provider_sort_ranks(), scraping_settings()
        self.include_prerelease_results, self.ignore_results_filter, self.limit_resolve = include_prerelease_results(), ignore_results_filter(), limit_resolve()
        self.sort_function, self.quality_filter = results_sort_order(), self._quality_filter()
        self.include_unknown_size = get_setting('liberator.results.size_unknown', 'false') == 'true'
        self.make_search_info()
        if self.search_info: self.search_info_temp = self.search_info.copy()
        if self.autoscrape: self.autoscrape_nextep_handler()
        if self.autoscrape: self.autoscrape_nextep_handler()
        return self.get_sources()

    def orac_scraping_handler(self):
        try:

            
            # Call Orac /scrape via IPC
            self.search_info['strict_dedupe'] = str(self.orac_strict_dedupe).lower()
            scrape_results = _get_data_via_ipc('get_orac_scrape', self.search_info)
            if not scrape_results or not scrape_results.get('success'):
                logger('Orac', 'Orac Scraping failed or returned no results.')
                return False
            
            raw_results = scrape_results.get('results', [])
            if not raw_results:
                logger('Orac', 'Orac Scraping: No results found.')
                return False
                
            processed_results = []
            for item in raw_results:
                processed_results.append({
                    'name': item.get('name'),
                    'url': item.get('url'),
                    'hash': item.get('hash', '').lower(),
                    'quality': item.get('quality', 'SD'),
                    'size': item.get('size', 0),
                    'source': item.get('source', 'torrent'),
                    'name_info': item.get('name_info'),
                    'scrape_provider': 'external',
                    'provider': item.get('provider', 'orac'),
                })
            
            # Normalize results
            processed_results = self.process_external_results('orac', processed_results)
            
            # Check debrid cache
            orac_results = self.check_debrid_cache(processed_results)
            
            if orac_results:
                logger('Orac', f'Orac Scraping: {len(orac_results)} cached results found. Adding to sources.')
                self._sources_quality_count(orac_results)
                self.sources.extend(orac_results)
                self.orac_scraping_initiated = True
            else:
                logger('Orac', 'Orac Scraping: No cached results found after Debrid check.')
            
            # Return False to continue with normal scraping flow (which includes Easynews)
            return False
                
        except Exception as e:
            logger('Orac', 'Error in Orac Scraping Handler: %s' % str(e))
            import traceback
            logger('Orac', traceback.format_exc())
            return False

    def check_episode_group(self):
        try:
            if any([self.custom_season, self.custom_episode]) or 'skip_episode_group_check' in self.params: return
            group_info = episode_groups_cache.get(self.tmdb_id)
            if not group_info: return
            group_details = metadata.group_episode_data(metadata.group_details(group_info['id']), None, self.season, self.episode)
            if group_details:
                self.custom_season, self.custom_episode, self.episode_group_used = group_details['season'], group_details['episode'], True
                self.episode_group_label = '[B]CUSTOM GROUP: S%02dE%02d[/B]' % (self.custom_season, self.custom_episode)
        except: self.custom_season, self.custom_episode = None, None

    def determine_scrapers_status(self):
        self.active_internal_scrapers = active_internal_scrapers()
        self.debrid_enabled = debrid.debrid_enabled()
        self.active_external = False

    def get_sources(self):
        if not self.progress_dialog and not self.background: self._make_progress_dialog()
        results = []

        if self.prescrape and any(x in self.active_internal_scrapers for x in default_internal_scrapers):
            if self.prepare_internal_scrapers():
                results = self.collect_prescrape_results()
                if results: results = self.process_results(results)
        if not results:
            self.prescrape = False
            self.prepare_internal_scrapers()
            if not self.active_internal_scrapers and not self.orac_scraping: self._kill_progress_dialog()

            self.orig_results = self.collect_results()
            if not self.orig_results: self._kill_progress_dialog()
            results = self.process_results(self.orig_results)
        if not results: return self._process_post_results()
        if self.autoscrape: return results
        else: return self.play_source(results)

    def collect_results(self):
        logger('Orac', f'collect_results START: self.sources count = {len(self.sources)}')
        self.sources.extend(self.prescrape_sources)
        threads_append = self.threads.append
        if self.active_folders: self.append_folder_scrapers(self.providers)
        self.providers.extend(self.internal_sources())
        if self.orac_scraping:
            threads_append(Thread(target=self.orac_scraping_handler, name='Orac'))
        if self.providers or self.orac_scraping:
            for i in self.providers: threads_append(Thread(target=self.activate_providers, args=(i[0], i[1], False), name=i[2]))
            [i.start() for i in self.threads]
            self.scraper_dialog()
        elif self.active_internal_scrapers: self.scraper_dialog()
        logger('Orac', f'collect_results END: self.sources count = {len(self.sources)}')
        return self.sources

    def collect_prescrape_results(self):
        threads_append = self.prescrape_threads.append
        if self.active_folders:
            if self.autoplay or check_prescrape_sources('folders', self.media_type):
                self.append_folder_scrapers(self.prescrape_scrapers)
                self.remove_scrapers.append('folders')
        self.prescrape_scrapers.extend(self.internal_sources(True))
        if not self.prescrape_scrapers: return []
        for i in self.prescrape_scrapers: threads_append(Thread(target=self.activate_providers, args=(i[0], i[1], True), name=i[2]))
        [i.start() for i in self.prescrape_threads]
        self.remove_scrapers.extend(i[2] for i in self.prescrape_scrapers)
        if self.background: [i.join() for i in self.prescrape_threads]
        else: self.scraper_dialog()
        return self.prescrape_sources

    def process_results(self, results):
        if self.prescrape: self.all_scrapers = self.active_internal_scrapers
        else:
            self.all_scrapers = list(set(self.active_internal_scrapers + self.remove_scrapers))
            clear_property('fs_filterless_search')
            
        if self.orac_scraping:
            self.uncached_results = []
        else:
            self.uncached_results = self.sort_results([i for i in results if 'Uncached' in i.get('cache_provider', '')])
            results = [i for i in results if not i in self.uncached_results]
        
        if self.ignore_scrape_filters:
            self.filters_ignored = True
            results = self.sort_results(results)
        else:
            results = self.sort_results(results)
            results = self.filter_results(results)
            results = self.filter_audio(results)
# SXM do not do this for orac scraping
            if not self.orac_scraping:
                for file_type in filter_keys: results = self.special_filter(results, file_type)
        results = self.sort_preferred_autoplay(results)
        results = self.sort_first(results)
        return results

    def sort_results(self, results):
        for item in results:
            provider = item['scrape_provider']
            if provider == 'external': account_type = item['debrid'].lower() if 'debrid' in item else 'orac'
            else: account_type = provider.lower()
            item['provider_rank'] = self._get_provider_rank(account_type)
            item['quality_rank'] = self._get_quality_rank(item.get('quality', 'SD'))
        results.sort(key=self.sort_function)
        results = self._sort_uncached_results(results)
        return results

    def filter_results(self, results):
        if self.folders_ignore_filters:
            folder_results = [i for i in results if i['scrape_provider'] == 'folders']
            results = [i for i in results if not i in folder_results]
        else: folder_results = []
        results = [i for i in results if i['quality'] in self.quality_filter]
        if self.filter_size_method:
            min_size = string_to_float(get_setting('liberator.results.%s_size_min' % self.media_type, '0'), '0') / 1000
            if min_size == 0.0 and not self.include_unknown_size: min_size = 0.02
            if self.filter_size_method == 1:
                meta_dict = self.orac_movie_meta if self.media_type == 'movie' else self.orac_episode_meta
                duration = (meta_dict.get('duration') if meta_dict else None) or (5400 if self.media_type == 'movie' else 2400)
                max_size = ((0.125 * (0.90 * string_to_float(get_setting('results.line_speed', '25'), '25'))) * duration)/1000
            elif self.filter_size_method == 2:
                max_size = string_to_float(get_setting('liberator.results.%s_size_max' % self.media_type, '10000'), '10000') / 1000
            results = [i for i in results if i['scrape_provider'] in ('external', 'folders') or min_size <= i['size'] <= max_size]
        results += folder_results
        return results

    def filter_audio(self, results):
        return [i for i in results if not any(x in i['extraInfo'] for x in audio_filters())]

    def special_filter(self, results, file_type):
        enable_setting, key = filter_status(file_type), filter_keys[file_type]
        if key == '[B]HEVC[/B]' and enable_setting == 0:
            hevc_max_quality = self._get_quality_rank(get_setting('liberator.filter.hevc.%s' % ('max_autoplay_quality' if self.autoplay else 'max_quality'), '4K'))
            results = [i for i in results if not key in i['extraInfo'] or i['quality_rank'] >= hevc_max_quality]
        if enable_setting == 1:
            if key == '[B]D/VISION[/B]' and filter_status('hdr') == 0:
                results = [i for i in results if all(x in i['extraInfo'] for x in (key, '[B]HDR[/B]')) or not key in i['extraInfo']]
            else: results = [i for i in results if not key in i['extraInfo']]
        return results

    def sort_first(self, results):
        try:
            sort_first_scrapers = []
            if 'folders' in self.all_scrapers and sort_to_top('folders'): sort_first_scrapers.append('folders')
            sort_first_scrapers.extend([i for i in self.all_scrapers if i in cloud_scrapers and sort_to_top(i)])
            if not sort_first_scrapers: return results
            sort_first = [i for i in results if i['scrape_provider'] in sort_first_scrapers]
            sort_first.sort(key=lambda k: (self._sort_folder_to_top(k['scrape_provider']), k['quality_rank']))
            sort_last = [i for i in results if not i in sort_first]
            results = sort_first + sort_last
        except: pass
        return results

    def sort_preferred_autoplay(self, results):
        if not self.autoplay: return results
        try:
            preferences = preferred_autoplay()
            if not preferences: return results
            preference_results = [i for i in results if any(x in i['extraInfo'] for x in preferences)]
            if not preference_results: return results
            results = [i for i in results if not i in preference_results]
            preference_results = sorted([dict(item, **{'pref_includes': sum([preference_values[preferences.index(x)] for x in [i for i in preferences if i in item['extraInfo']]])}) \
                        for item in preference_results], key=lambda k: k['pref_includes'], reverse=True)
            return preference_results + results
        except: return results

    def prepare_internal_scrapers(self):
        active_internal_scrapers = [i for i in self.active_internal_scrapers if not i in self.remove_scrapers]
        if self.prescrape and not any([check_prescrape_sources(i, self.media_type) for i in active_internal_scrapers]): return False
        if 'folders' in active_internal_scrapers:
            self.folder_info = [i for i in self.get_folderscraper_info() if source_folders_directory(self.media_type, i[1])]
            if self.folder_info:
                self.active_folders = True
                self.internal_scraper_names = [i for i in active_internal_scrapers if not i == 'folders'] + [i[0] for i in self.folder_info]
            else: self.internal_scraper_names = [i for i in active_internal_scrapers if not i == 'folders']
        else:
            self.folder_info = []
            self.internal_scraper_names = active_internal_scrapers[:]
        self.active_internal_scrapers = active_internal_scrapers
        if self.clear_properties: self._clear_properties()
        return True

    def activate_providers(self, module_type, function, prescrape):
        sources = self._get_module(module_type, function).results(self.search_info)
        if not sources: 
            logger('Sources', 'No Sources Found for %s' % module_type)
            return
        if prescrape: self.prescrape_sources.extend(sources)
        else:
            self.sources.extend(sources)

    def activate_external_providers(self):
        # Legacy external providers are deprecated in favor of Orac
        pass
    
    def import_external_scrapers(self):
        try:
            append_module_to_syspath('special://home/addons/%s/lib' % self.ext_folder)
            self.ext_sources = manual_module_import('%s.sources_%s' % (self.ext_name, self.ext_name))
            self.provider_defaults = [k.split('.')[1] for k, v in manual_function_import('%s.modules.control' % self.ext_name, 'getProviderDefaults')().items() if v == 'true']
        except: return False
        return True

    def disable_external(self, line1=''):
        if line1: notification(line1, 2000)
        try: self.active_internal_scrapers.remove('external')
        except: pass
        self.active_external, self.external_providers = False, []

    def internal_sources(self, prescrape=False):
        active_sources = [i for i in self.active_internal_scrapers if i in internal_include_list]
        try: sourceDict = [('internal', manual_function_import('scrapers.%s' % i, 'source'), i) for i in active_sources \
                                                if not (prescrape and not check_prescrape_sources(i, self.media_type))]
        except: sourceDict = []
        return sourceDict

    def external_sources(self):
        try:
            all_sources = self.ext_sources.total_providers['torrents']
            if self.disabled_ext_ignored: active_sources = all_sources
            elif self.default_ext_only: active_sources = [i for i in self.provider_defaults if i in all_sources]
            else: active_sources = [i for i in all_sources if json.loads(get_property('%s_settings' % self.ext_name)).get('provider.%s' % i, 'false') == 'true']
            sourceDict = [(i, manual_function_import('%s.sources_%s.%s.%s' % (self.ext_name, self.ext_name, 'torrents', i), 'source')) for i in active_sources]
        except: sourceDict = self.legacy_external_sources()
        return sourceDict

    def legacy_external_sources(self):
        return []

    def folder_sources(self):
        def import_info():
            for item in self.folder_info:
                scraper_name = item[0]
                module = manual_function_import('scrapers.folders', 'source')
                yield ('folders', (module, (item[1], scraper_name, item[2])), scraper_name)
        sourceDict = list(import_info())
        try: sourceDict = list(import_info())
        except: sourceDict = []
        return sourceDict

    def play_source(self, results):
        if self.background or self.autoplay: return self.play_file(results)
        return self.display_results(results)

    def append_folder_scrapers(self, current_list):
        current_list.extend(self.folder_sources())

    def get_folderscraper_info(self):
        folder_info = [(get_setting('liberator.%s.display_name' % i), i, source_folders_directory(self.media_type, i)) for i in folder_scrapers]
        return [i for i in folder_info if not i[0] in (None, 'None', '') and i[2]]

    def process_external_results(self, provider, sources):
        for i in sources:
            try:
                i_get = i.get
                # Initialize defaults
                display_name = i_get('name', 'Unknown')
                quality = i_get('quality', 'SD')
                extraInfo = ''
                size_label = 'N/A'
                size = 0
                
                # Try to normalize the display name
                try:
                    if 'name' in i:
                        display_name = clean_file_name(normalize(i['name'].replace('html', ' ').replace('+', ' ').replace('-', ' ')))
                except:
                    display_name = clean_file_name(i.get('name', 'Unknown'))
                
                # Ensure hash is lowercase string
                if 'hash' in i:
                    try:
                        _hash = i_get('hash').lower()
                        i['hash'] = str(_hash)
                    except: pass
                
                # Try to get quality and extraInfo
                try:
                    if 'name_info' in i and i.get('name_info'): 
                        quality, extraInfo = get_file_info(name_info=i_get('name_info'))
                    else: 
                        quality, extraInfo = get_file_info(url=i_get('url'))
                except Exception as e:
                    # Fallback to existing quality or SD
                    quality = i_get('quality', 'SD')
                    extraInfo = ''
                
                # Try to format size
                try:
                    size = float(i_get('size', 0))
                    if size > 0:
                        size_label = '%.2f GB' % size
                except: pass
                
                # Preserve original provider if it's already there and specific, otherwise use 'orac'
                final_provider = i_get('provider') or provider
                
                # Always update with required keys
                i.update({
                    'provider': final_provider, 
                    'display_name': display_name, 
                    'external': True, 
                    'scrape_provider': 'external', 
                    'extraInfo': extraInfo,
                    'quality': quality, 
                    'size_label': size_label, 
                    'size': round(size, 2) if size > 0 else 0
                })
            except Exception as e:
                # Last resort: add minimal required keys to prevent UI errors
                logger('Sources', 'Error processing external result, using fallbacks: %s' % str(e))
                i.update({
                    'provider': provider,
                    'display_name': i.get('name', 'Unknown'),
                    'external': True,
                    'scrape_provider': 'external',
                    'extraInfo': '',
                    'quality': i.get('quality', 'SD'),
                    'size_label': 'N/A',
                    'size': 0
                })
        return sources

    def check_debrid_cache(self, results):
        if not self.debrid_enabled: return []
        def _process_cache_check(provider, function):
            cached = function(hash_list, cached_hashes)
            final_results.extend([dict(i, **{'cache_provider': provider if i['hash'] in cached else 'Uncached %s' % provider, 'debrid':provider}) for i in results if i['hash'] in cached])
        
        try:
            final_results = []
            hash_list = list(set([i['hash'] for i in results if i.get('hash')]))
            if not hash_list: return []
            cached_hashes = debrid.query_local_cache(hash_list)
            
            debrid_runners = {'Real-Debrid': ('Real-Debrid', debrid.RD_check), 'Premiumize.me': ('Premiumize.me', debrid.PM_check), 'AllDebrid': ('AllDebrid', debrid.AD_check),
                                'Offcloud': ('Offcloud', debrid.OC_check), 'EasyDebrid': ('EasyDebrid', debrid.ED_check), 'TorBox': ('TorBox', debrid.TB_check)}
            
            debrid_check_threads = [Thread(target=_process_cache_check, args=debrid_runners[item], name=item) for item in self.debrid_enabled if item in debrid_runners]
            [i.start() for i in debrid_check_threads]
            
            if self.background: [i.join() for i in debrid_check_threads]
            else: self._debrid_check_dialog(debrid_check_threads)
            
            return final_results
        except Exception as e:
            logger('Sources', 'Error in check_debrid_cache: %s' % str(e))
            return []

    def _debrid_check_dialog(self, debrid_check_threads):
        if not self.progress_dialog: return
        self.progress_dialog.reset_is_cancelled()
        start_time, timeout = time.time(), 20
        self.progress_dialog.update_scraper(0, 0, 0, 0, 0, 'Checking Debrid...', 0)
        while not self.progress_dialog.iscanceled() and not kodi_utils.xbmc_monitor().abortRequested():
            try:
                remaining_debrids = [x.getName() for x in debrid_check_threads if x.is_alive()]
                kodi_utils.sleep(100)
                if len(remaining_debrids) == 0: break
                if (time.time() - start_time) > timeout: break
            except: pass

    def scraper_dialog(self):
        def _scraperDialog():
            monitor = xbmc_monitor()
            start_time = time.time()
            self.progress_dialog.update_scraper(0, 0, 0, 0, 0, 'Scraping...', 0)
            while not self.progress_dialog.iscanceled() and not monitor.abortRequested():
                try:
                    remaining_providers = [x.getName() for x in _threads if x.is_alive() is True]
                    self._process_internal_results()
                    sleep(self.sleep_time)
                    if len(remaining_providers) == 0: break
                    if (time.time() - start_time) > scraper_timeout: break
                except:	return self._kill_progress_dialog()
        if self.prescrape: scraper_list, _threads = self.prescrape_scrapers, self.prescrape_threads
        else: scraper_list, _threads = self.providers, self.threads
        self.internal_scrapers = self._get_active_scraper_names(scraper_list)
        if not self.internal_scrapers and not self.orac_scraping: return
        _scraperDialog()
        try: del monitor
        except: pass

    def display_results(self, results):
        window_format, window_number = results_format()
        if self.media_type == 'episode' and self.orac_episode_meta:
            meta = self.orac_episode_meta
        elif self.media_type == 'movie' and self.orac_movie_meta:
            meta = self.orac_movie_meta
        action, chosen_item = open_window(('windows.sources', 'SourcesResults'), 'sources_results.xml',
                window_format=window_format, window_id=window_number, results=results, meta=meta, episode_group_label=self.episode_group_label,
                scraper_settings=self.scraper_settings, prescrape=self.prescrape, filters_ignored=self.filters_ignored, uncached_results=self.uncached_results,
                scrape_duration=time.time() - self.scrape_start_time)
        if not action: self._kill_progress_dialog()
        elif action == 'play': return self.play_file(results, chosen_item)
        elif self.prescrape and action == 'perform_full_search':
            self.prescrape, self.clear_properties = False, False
            return self.get_sources()
        elif action == 'rescrap':
            self._kill_progress_dialog()
            # Reinitializing class variables for a fresh scrape
            
            # Save original params for fresh playback prep
            original_params = getattr(self, 'params', {}).copy()
            
            self.__init__()
            return self.playback_prep(params=original_params)

    def _get_active_scraper_names(self, scraper_list):
        return [i[2] for i in scraper_list]

    def _process_post_results(self):
        if self.media_type == 'episode' and self.auto_episode_group in (1, 2) and not self.rescrape_with_episode_group:
            self.rescrape_with_episode_group = True
            if self.auto_episode_group == 1 or confirm_dialog(heading=self.meta.get('rootname', ''), text='No results.[CR]Retry With Custom Episode Group if Possible?'):
                if self.episode_group_used:
                    self.params.update({'custom_season': None, 'custom_episode': None, 'episode_group_label': '[B]CUSTOM GROUP: S%02dE%02d[/B]' % (self.season, self.episode),
                                        'skip_episode_group_check': True})
                    self.threads, self.disabled_ext_ignored, self.prescrape = [], True, False
                    return self.playback_prep()
                if self.auto_episode_group == 2:
                    from indexers.dialogs import episode_groups_choice
                    try: group_id = episode_groups_choice({'meta': self.meta, 'poster': self.meta['poster']})
                    except: group_id = None
                else:
                    try: group_id = metadata.episode_groups(self.tmdb_id)[0]['id']
                    except: group_id = None
                if group_id:
                    try: group_details = metadata.group_episode_data(metadata.group_details(group_id), None, self.season, self.episode)
                    except: group_details = None
                    if group_details:
                        season, episode = group_details['season'], group_details['episode']
                        self.params.update({'custom_season': season, 'custom_episode': episode, 'episode_group_label': '[B]CUSTOM GROUP: S%02dE%02d[/B]' % (season, episode)})
                        self.threads, self.rescrape_with_episode_group, self.disabled_ext_ignored, self.prescrape = [], True, True, False
                        return self.playback_prep()
        if self.orig_results and not self.background:
            if self.ignore_results_filter == 0: return self._no_results()
            if self.ignore_results_filter == 1 or confirm_dialog(heading=self.meta.get('rootname', ''), text='No results. Access Filtered Results?'):
                return self._process_ignore_filters()
        return self._no_results()

    def _process_ignore_filters(self):
        if self.autoplay: notification('Filters Ignored & Autoplay Disabled')
        self.filters_ignored, self.autoplay = True, False
        results = self.sort_results(self.orig_results)
        results = self.sort_preferred_autoplay(results)
        results = self.sort_first(results)
        return self.play_source(results)

    def _no_results(self):
        self._kill_progress_dialog()
        hide_busy_dialog()
        if self.background: return notification('[B]Next Up:[/B] No Results', 5000)
        notification('No Results', 2000)

    def get_search_title(self):
        if self.orac_meta:
            search_title = self.orac_meta.get('custom_title', None) or self.orac_meta.get('english_title') or self.orac_meta.get('title')
        elif self.orac_movie_meta:
            search_title = self.orac_movie_meta.get('custom_title', None) or self.orac_movie_meta.get('title')
        elif self.orac_episode_meta:
            search_title = self.orac_episode_meta.get('tvshowtitle')
        else:
            search_title = self.params.get('title')
        return search_title

    def get_search_year(self):
        if self.orac_meta:
            year = self.orac_meta.get('custom_year', None) or self.orac_meta.get('year')
        elif self.orac_movie_meta:
            year = self.orac_movie_meta.get('custom_year', None) or self.orac_movie_meta.get('year')
        elif self.orac_episode_meta:
            year = self.orac_episode_meta.get('year')
        else:
            year = self.params.get('year')
        return year

    def get_season(self):
        season = self.orac_episode_meta.get('custom_season', None) or self.orac_episode_meta.get('season')
        try: season = int(season)
        except: season = None
        return season

    def get_episode(self):
        episode = self.orac_episode_meta.get('custom_episode', None) or self.orac_episode_meta.get('episode')
        try: episode = int(episode)
        except: episode = None
        return episode

    def get_ep_name(self):
        ep_name = None
        ep_name = self.orac_episode_meta.get('title')
        try: ep_name = safe_string(remove_accents(ep_name))
        except: ep_name = safe_string(ep_name)  
        return ep_name

    def _process_internal_results(self):
        for i in self.internal_scrapers:
            win_property = get_property(int_window_prop % i)
            if win_property in ('checked', '', None): continue
            try: sources = json.loads(win_property)
            except: continue
            set_property(int_window_prop % i, 'checked')
            self._sources_quality_count(sources)
    
    def _sources_quality_count(self, sources):
        for item in self.count_tuple: setattr(self, item[0], getattr(self, item[0]) + item[2](sources, item[1]))

    def _quality_filter(self):
        setting = 'results_quality_%s' % self.media_type if not self.autoplay else 'autoplay_quality_%s' % self.media_type
        filter_list = quality_filter(setting)
        if self.include_prerelease_results and 'SD' in filter_list: filter_list += ['SCR', 'CAM', 'TELE']
        return filter_list

    def _get_quality_rank(self, quality):
        return quality_ranks[quality]

    def _get_provider_rank(self, account_type):
        return self.provider_sort_ranks[account_type] or 11

    def _sort_folder_to_top(self, provider):
        if provider == 'folders': return 0
        else: return 1

    def _sort_uncached_results(self, results):
        uncached = [i for i in results if 'Uncached' in i.get('cache_provider', '')]
        cached = [i for i in results if not i in uncached]
        return cached + uncached

    def get_meta(self):
        self.orac_meta = None
        if self.media_type == 'movie':
            ipc_params = {'tmdb_id': self.tmdb_id, 'item_type': 'movie'}
            movies = _get_data_via_ipc('get_movie_details',params=ipc_params)
# Build orac_meta dict with everything needed for movies
            self.orac_movie_meta = {
                'media_type': 'movie',
                'background': self.background,
                'custom_title': self.custom_title,
                'custom_year': self.custom_year,
                'tmdb_id': self.tmdb_id, 
                'imdb_id': movies.get('imdb_id') or '',
                'title': movies.get('title'),
                'original_title': movies.get('original_title'),
                'year': movies.get('year'),
                'duration': movies.get('runtime'),
                'poster': movies.get('poster_path'),
                'fanart': movies.get('fanart_path'),
                'clearlogo': movies.get('clearlogo_path'),
                'genre': movies.get('genres', []),
                'overview': movies.get('overview'),
                'premiered': movies.get('release_date'),
                'rating': movies.get('rating'),
                'studio': movies.get('studio'),
                'tagline': movies.get('tagline'),
                'country': movies.get('country')
                }
            
            self.orac_meta = movies if movies else {}
            self.meta = self.orac_meta
            logger('Sources', 'get_meta (movie) orac_movie_meta: %s' % ('Success' if self.orac_movie_meta else 'Failed'))
            return
        else:
            ipc_params = {'tmdb_id': self.tmdb_id, 'item_type': 'tvshow', 'season': self.season}
            show_meta = _get_data_via_ipc('get_show_details', params=ipc_params)
            self.orac_meta = show_meta if show_meta else {}
            self.meta = self.orac_meta
            self.orac_episode_meta = {
                'media_type': 'episode',
                'background': self.background,
                'custom_title': self.custom_title,
                'custom_year': self.custom_year,
                'tmdb_id': self.tmdb_id, 
                'imdb_id': show_meta.get('imdb_id') or '',
                'original_title': show_meta.get('original_title'),
                'year': show_meta.get('year'),
                'season': self.season,  
                'episode': self.episode,
                'tvshowtitle': show_meta.get('title'),
                'genre': show_meta.get('genres', []),
                'status': show_meta.get('status'),
                'tvdb_id': show_meta.get('tvdb_id', 0),
                'rating': show_meta.get('rating'),
                'network': show_meta.get('network'),
                'tagline': show_meta.get('tagline'),
                'country': show_meta.get('country'),
                'total_seasons': len(show_meta.get('seasons', []))
                }
            episode_count = 0
            show_pack_enable, season_pack_enable = True, True
            for season in show_meta.get('seasons', []):
                episode_count += season.get('episode_count', 0)
                if season.get('season') == self.season:
                    for episode in season.get('episodes', []):
                        if episode.get('episode_number') == self.episode:
                            self.orac_episode_meta.update({
                            'episode_count': season.get('episode_count', 0),
                            'duration': episode.get('runtime'),
                            'poster': episode.get('episode_poster_path'),
                            'fanart': episode.get('episode_fanart_path'),
                            'clearlogo': episode.get('episode_clearlogo_path'),
                            'premiered': episode.get('first_aired'),
                            'overview': episode.get('episode_overview'),
                            'title': episode.get('episode_title')})
                        aired_date = episode.get('air_date')
                        if get_datetime(aired_date, '%Y-%m-%d') > get_datetime(get_datetime(), '%Y-%m-%d'):
                            show_pack_enable = False
                           # If the episode is unaired, we need to mark the show as not packable
                        if season.get('season') == self.season and episode.get('episode_number') == self.episode:
                            if get_datetime(aired_date, '%Y-%m-%d') > get_datetime(get_datetime(), '%Y-%m-%d'):
                                season_pack_enable = False
                            # If the episode is unaired, we need to mark the season as not packable
            self.orac_episode_meta.update({'show_pack_enable': show_pack_enable, 'season_pack_enable': season_pack_enable})
            self.orac_episode_meta.update({'total_episodes': episode_count})
            logger('Sources', 'get_meta (episode) orac_episode_meta: %s' % ('Success' if self.orac_episode_meta else 'Failed'))

    def make_search_info(self):
# The search info for episodes comes from the show data
        if self.media_type == 'episode':

            title, year, ep_name = self.orac_episode_meta.get('title'), self.orac_episode_meta.get('year'), self.orac_episode_meta.get('title')
            aliases = make_alias_dict(self.orac_episode_meta, title)
            expiry_times = (168,240,240)
            self.search_info = {'media_type': self.media_type, 'item_type': self.media_type, 'title': title, 'year': str(year), 'tmdb_id': self.tmdb_id, 'imdb_id': self.orac_episode_meta.get('imdb_id'),
                                'aliases': aliases,
                                'season': str(self.get_season()), 'episode': str(self.get_episode()), 'tvdb_id': self.orac_episode_meta.get('tvdb_id',0),
                                'ep_name': self.orac_episode_meta.get('title'),
                                'expiry_times': expiry_times,
                                'total_seasons': self.orac_episode_meta.get('total_seasons', 1),
                                'tvshowtitle': self.orac_episode_meta.get('tvshowtitle')}
            return

        else:
            # This section for movies
            title, year = self.orac_movie_meta.get('title'), self.orac_movie_meta.get('year')
            aliases = make_alias_dict(self.orac_movie_meta, title)
            expiry_times = (168,240,240)
            self.search_info = {'media_type': self.media_type, 'item_type': self.media_type, 'title': title, 'year': str(year), 'tmdb_id': self.tmdb_id, 'imdb_id': self.orac_movie_meta.get('imdb_id'),
                                'aliases': aliases, 'tvdb_id': self.orac_movie_meta.get('tvdb_id',0), 'expiry_times': expiry_times}
            return

    def _get_module(self, module_type, function):
        if module_type == 'external': module = function.source(*self.external_args)
        elif module_type == 'folders': module = function[0](*function[1])
        else: module = function()
        return module

    def _clear_properties(self):
        for item in default_internal_scrapers: clear_property(int_window_prop % item)
        if self.active_folders:
            for item in self.folder_info: clear_property(int_window_prop % item[0])

    def _make_progress_dialog(self):
        if self.media_type == 'movie' and self.orac_movie_meta:
            self.progress_dialog = create_window(('windows.sources', 'SourcesPlayback'), 'sources_playback.xml', meta=self.orac_movie_meta)
        else:
            self.progress_dialog = create_window(('windows.sources', 'SourcesPlayback'), 'sources_playback.xml', meta=self.orac_episode_meta)
        self.progress_thread = Thread(target=self.progress_dialog.run)
        self.progress_thread.start()

    def _make_resolve_dialog(self):
        self.resolve_dialog_made = True
        if not self.progress_dialog: self._make_progress_dialog()
        self.progress_dialog.enable_resolver()

    def _make_resume_dialog(self, percent):
        if not self.progress_dialog: self._make_progress_dialog()
        self.progress_dialog.enable_resume(percent)
        return self.progress_dialog.resume_choice

    def _make_nextep_dialog(self, default_action='cancel'):
        try: action = open_window(('windows.next_episode', 'NextEpisode'), 'next_episode.xml', meta=self.meta, default_action=default_action)
        except: action = 'cancel'
        return action

    def _kill_progress_dialog(self):
        success = 0
        try:
            self.progress_dialog.close()
            success += 1
        except: pass
        try:
            self.progress_thread.join()
            success += 1
        except: pass
        if not success == 2: close_all_dialog()
        del self.progress_dialog
        del self.progress_thread
        self.progress_dialog, self.progress_thread = None, None

    def debridPacks(self, debrid_provider, name, magnet_url, info_hash, download=False):
        show_busy_dialog()
        debrid_info = {'Real-Debrid': 'rd_browse', 'Premiumize.me': 'pm_browse', 'AllDebrid': 'ad_browse',
                        'Offcloud': 'oc_browse', 'EasyDebrid': 'ed_browse', 'TorBox': 'tb_browse'}[debrid_provider]
        debrid_function = self.debrid_importer(debrid_info)
        try: debrid_files = debrid_function().display_magnet_pack(magnet_url, info_hash)
        except: debrid_files = None
        hide_busy_dialog()
        if not debrid_files: return notification('Error')
        debrid_files.sort(key=lambda k: k['filename'].lower())
        if download: return debrid_files, debrid_function
        list_items = [{'line1': '%.2f GB | %s' % (float(item['size'])/1073741824, clean_file_name(item['filename']).upper())} for item in debrid_files]
        kwargs = {'items': json.dumps(list_items), 'heading': name, 'enumerate': 'true', 'narrow_window': 'true'}
        chosen_result = select_dialog(debrid_files, **kwargs)
        if chosen_result is None: return None
        link = self.resolve_internal(debrid_info, chosen_result['link'], '')
        name = chosen_result['filename']
        self._kill_progress_dialog()
        return LiberatorPlayer().run(link, 'video')

    def play_file(self, results, source={}):
        self.playback_successful, self.cancel_all_playback = None, False
        try:
            try:
                hide_busy_dialog()
                url = None
                results = [i for i in results if not 'Uncached' in i.get('cache_provider', '')]
                if not source: source = results[0]
                items = [source]
                if not self.limit_resolve: 
                    source_index = results.index(source)
                    results.remove(source)
                    items_prev = results[:source_index]
                    items_prev.reverse()
                    items_next = results[source_index:]
                    items = items + items_next + items_prev
                processed_items = []
                processed_items_append = processed_items.append
                for count, item in enumerate(items, 1):
                    resolve_item = dict(item)
                    provider = item['scrape_provider']
                    if provider == 'external': provider = item['debrid'].replace('.me', '')
                    elif provider == 'folders': provider = item['source']
                    provider_text = provider.upper()
                    extra_info = '[B]%s[/B] | [B]%s[/B] | %s' %  (item['quality'], item['size_label'], item['extraInfo'])
                    display_name = item['display_name'].upper()
                    resolve_item['resolve_display'] = '%02d. [B]%s[/B][CR]%s[CR]%s' % (count, provider_text, extra_info, display_name)
                    processed_items_append(resolve_item)
                    if provider == 'easynews':
                        for retry in range(1, 2):
                            resolve_item = dict(item)
                            resolve_item['resolve_display'] = '%02d. [B]%s (RETRYx%s)[/B][CR]%s[CR]%s' % (count, provider_text, retry, extra_info, display_name)
                            processed_items_append(resolve_item)
                items = list(processed_items)
                if not self.continue_resolve_check(): return self._kill_progress_dialog()
                hide_busy_dialog()
                percent = 0
                if any((self.random, self.random_continual)): percent = 0
                else:
                    percent = 0 if not self.percent_watched else self.percent_watched
                
                # If percent was passed in params, we assume the decision was already made (e.g. by skin/widget).
                # Checking self.percent_watched directly avoids re-triggering dialog.
                if self.percent_watched > 0:
                    self.playback_percent = float(self.percent_watched)
                else:
                    # Not passed in params, so check metadata/bookmarks internally
                    # The value passed to _make_resume_dialog is used in a setProperty call, which requires a string.
                    if percent > 5 and percent < 95:
                        action = self._make_resume_dialog(str(percent))
                        if action == 'cancel':
                            self._kill_progress_dialog()
                            return
                        if action == 'start_over':
                            percent = 0
                    self.playback_percent = float(percent)

                if not self.resolve_dialog_made: self._make_resolve_dialog()
                if self.background: sleep(1000)
                monitor = xbmc_monitor()
                for count, item in enumerate(items, 1):
                    try:
                        hide_busy_dialog()
                        if not self.progress_dialog: break
                        self.progress_dialog.reset_is_cancelled()
                        self.progress_dialog.update_resolver(text=item['resolve_display'])
                        self.progress_dialog.busy_spinner()
                        if count > 1:
                            sleep(200)
                            try: del player
                            except: pass
                        url, self.playback_successful, self.cancel_all_playback = None, None, False
                        self.playing_filename = item['name']
                        self.playing_item = item
                        player = LiberatorPlayer()
                        try:
                            if self.progress_dialog.iscanceled() or monitor.abortRequested(): break
                            logger('Sources', '###PLAY_FILE_RESOLVING###: %s' % json.dumps(item))
                            url = self.resolve_sources(item)
                            if url:
                                resolve_percent = 0
                                self.progress_dialog.busy_spinner('false')
                                self.progress_dialog.update_resolver(percent=resolve_percent)
                                sleep(200)
                                player.run(url, self)
                            else: continue
                            if self.cancel_all_playback: break
                            if self.playback_successful: break
                            if count == len(items):
                                self.cancel_all_playback = True
                                player.stop()
                                break
                        except: 
                            logger('Sources','Error 1 occurred while playing file from source: %s' % source)
                            pass
                    except: 
                        logger('Sources','Error 2 occurred while playing file from source: %s' % source)
                        pass
            except:
                url = None
                logger('Sources','Unhandled error occurred while playing file from source: %s' % source)
                self.playback_successful = False
                self.cancel_all_playback = True
                pass
        except: 
            logger('Sources','Error 3 occurred while playing file from source: %s' % source)
            self._kill_progress_dialog()
        if self.cancel_all_playback: return self._kill_progress_dialog()
        if not self.playback_successful or not url: self.playback_failed_action()
        try: del monitor
        except: 
            logger('Sources','Error 4 occurred while playing file from source: %s' % source)
            pass

    def get_playback_percent(self):
        if any((self.random, self.random_continual)): return 0.0
        percent = self.percent_watched
        if not percent: return 0.0
        action = self.get_resume_status(percent)
        if action == 'cancel': return None
        if action == 'start_over':
            return 0.0
        return float(percent)

    def get_resume_status(self, percent):
        if auto_resume(self.media_type): return float(percent)
        return self._make_resume_dialog(percent)

    def playback_failed_action(self):
        self._kill_progress_dialog()
        if self.prescrape and self.autoplay:
            self.resolve_dialog_made, self.prescrape, self.prescrape_sources = False, False, []
            self.get_sources()

    def continue_resolve_check(self):
        try:
            if not self.background or self.autoscrape_nextep: return True
            if self.autoplay_nextep: return self.autoplay_nextep_handler()
            return self.random_continual_handler()
        except: return False

    def random_continual_handler(self):
        notification('[B]Next Up:[/B] %s S%02dE%02d' % (self.meta.get('title'), self.meta.get('season'), self.meta.get('episode')), 6500, self.meta.get('poster'))
        player = xbmc_player()
        while player.isPlayingVideo(): sleep(100)
        self._make_resolve_dialog()
        return True

    def autoplay_nextep_handler(self):
        if not self.nextep_settings: return False
        player = xbmc_player()
        if player.isPlayingVideo():
            total_time = player.getTotalTime()
            use_window, window_time, default_action = self.nextep_settings['use_window'], self.nextep_settings['window_time'], self.nextep_settings['default_action']
            action = None if use_window else 'close'
            continue_nextep = False
            while player.isPlayingVideo():
                try:
                    remaining_time = round(total_time - player.getTime())
                    if remaining_time <= window_time:
                        continue_nextep = True
                        break
                    sleep(100)
                except: pass
            if continue_nextep:
                if use_window: action = self._make_nextep_dialog(default_action=default_action)
                else: notification('[B]Next Up:[/B] %s S%02dE%02d' % (self.meta.get('title'), self.meta.get('season'), self.meta.get('episode')), 6500, self.meta.get('poster'))
                if not action: action = default_action
                if action == 'cancel': return False
                elif action == 'pause':
                    player.stop()
                    return False
                elif action == 'play':
                    self._make_resolve_dialog()
                    player.stop()
                    return True
                else:
                    while player.isPlayingVideo(): sleep(100)
                    self._make_resolve_dialog()
                    return True
            else: return False
        else: return False


    def autoscrape_nextep_handler(self):
        player = xbmc_player()
        if player.isPlayingVideo():
            results = self.get_sources()
            if not results: return notification(33092, 3000)
            else:
                notification('[B]Next Episode Ready:[/B] %s S%02dE%02d' % (self.meta.get('title'), self.meta.get('season'), self.meta.get('episode')), 6500, self.meta.get('poster'))
                while player.isPlayingVideo(): sleep(100)
            self.display_results(results)
        else: return

    def debrid_importer(self, debrid_provider, timeout=10):
        return manual_function_import(*debrids[debrid_provider])

    def resolve_sources(self, item, meta=None):
        logger('Sources', '###RESOLVE_SOURCES_START###')
        try:
            if self.media_type == 'episode' and meta is None: meta = self.orac_episode_meta
            elif self.media_type == 'movie' and meta is None: meta = self.orac_movie_meta
            
            logger('Sources', 'resolve_sources: media_type=%s, meta_exists=%s' % (self.media_type, meta is not None))
            
            url = None
            if 'cache_provider' in item:
                cache_provider = item['cache_provider']
                title = self.get_search_title()
                if self.media_type == 'episode' and meta:
                    season, episode, pack = int(meta.get('season')), int(meta.get('episode')), 'package' in item
                elif self.media_type == 'movie' and meta:
                    season, episode, pack = None, None, False
                else:
                    logger('Sources', 'Metadata missing for resolution! Falling back to empty season/ep')
                    season, episode, pack = None, None, False
                
                logger('Sources', 'Resolving cached: %s | %s | %s' % (cache_provider, title, item['hash']))
                if cache_provider in debrid_providers: url = self.resolve_cached(cache_provider, item['url'], item['hash'], title, season, episode, pack)

            elif item.get('scrape_provider', None) in default_internal_scrapers:
                url = self.resolve_internal(item['scrape_provider'], item['id'], item['url_dl'], item.get('direct_debrid_link', False))
            else: url = item['url']
            return url
        except Exception as e:
            logger('Sources', 'Error in resolve_sources: %s' % str(e))
            import traceback
            logger('Sources', traceback.format_exc())
            return None

    def resolve_cached(self, debrid_provider, item_url, _hash, title, season, episode, pack, timeout=10):
        debrid_function = self.debrid_importer(debrid_provider)
        store_to_cloud = store_resolved_to_cloud(debrid_provider, pack)
        try: url = debrid_function().resolve_magnet(item_url, _hash, store_to_cloud, title, season, episode, timeout=timeout)
        except: url = None
        return url

    def resolve_internal(self, scrape_provider, item_id, url_dl, direct_debrid_link=False):
        url = None
        try:
            if direct_debrid_link or scrape_provider == 'folders': url = url_dl
            elif scrape_provider == 'easynews':
                from indexers.easynews import resolve_easynews
                url = resolve_easynews({'url_dl': url_dl, 'play': 'false'})
            else:
                debrid_function = self.debrid_importer(scrape_provider)
                if any(i in scrape_provider for i in ('rd_', 'ad_', 'tb_')):
                    url = debrid_function().unrestrict_link(item_id)
                else:
                    if '_cloud' in scrape_provider: item_id = debrid_function().get_item_details(item_id)['link']
                    url = debrid_function().add_headers_to_url(item_id)
        except: pass
        return url

    def _quality_length(self, items, quality):
        return len([i for i in items if i['quality'] == quality])

    def _quality_length_sd(self, items, dummy):
        return len([i for i in items if i['quality'] in sd_check])

    def _quality_length_final(self, items, dummy):
        return len(items)
