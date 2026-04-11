# -*- coding: utf-8 -*-
from caches.settings_cache import get_setting, set_setting
from modules import kodi_utils
# logger = kodi_utils.logger

translate_path, get_property = kodi_utils.translate_path, kodi_utils.get_property
download_directories_dict = {'movie': 'liberator.movie_download_directory', 'episode': 'liberator.tvshow_download_directory', 'thumb_url': 'liberator.image_download_directory',
							'image_url': 'liberator.image_download_directory','image': 'liberator.image_download_directory', 'premium': 'liberator.premium_download_directory',
							None: 'liberator.premium_download_directory', 'None': False}
results_window_numbers_dict = {'List': 2000, 'Rows': 2001, 'WideList': 2002}
default_action_dict = {'0': 'play', '1': 'cancel', '2': 'pause'}
paginate_dict = {True: 'liberator.paginate.limit_widgets', False: 'liberator.paginate.limit_addon'}
nextep_sort_key_dict = {0: 'last_played', 1: 'first_aired', 2: 'name'}
prescrape_scrapers_tuple = ('easynews', 'rd_cloud', 'pm_cloud', 'ad_cloud', 'oc_cloud', 'tb_cloud', 'folders')
sort_to_top_dict = {'folders': 'liberator.results.sort_folders_first', 'rd_cloud': 'liberator.results.sort_rdcloud_first', 'pm_cloud': 'liberator.results.sort_pmcloud_first',
					'ad_cloud': 'liberator.results.sort_adcloud_first', 'oc_cloud': 'liberator.results.sort_occloud_first', 'tb_cloud': 'liberator.results.sort_tbcloud_first'}
internal_scrapers_clouds_list = [('rd', 'provider.rd_cloud'), ('pm', 'provider.pm_cloud'), ('ad', 'provider.ad_cloud'), ('oc', 'provider.oc_cloud'), ('tb', 'provider.tb_cloud')]

def tmdb_api_key():
	return get_setting('liberator.tmdb_api', '')

def tmdb_user_active():
	return get_setting('liberator.tmdb.user', 'empty_setting') not in ('empty_setting', '')

def trakt_client():
	return get_setting('liberator.trakt.client', '')

def trakt_secret():
	return get_setting('liberator.trakt.secret', '')

def trakt_user_active():
	return get_setting('liberator.trakt.user', 'empty_setting') not in ('empty_setting', '')

def simkl_client():
	return get_setting('liberator.simkl.client', '')

def simkl_secret():
	return get_setting('liberator.simkl.secret', '')

def simkl_user_active():
	return get_setting('liberator.simkl.user', 'empty_setting') not in ('empty_setting', '')

def results_format():
	window_format = str(get_setting('liberator.results.list_format', 'List'))
	if not window_format in results_window_numbers_dict:
		window_format = 'List'
		set_setting('results.list_format', window_format)
	window_number = results_window_numbers_dict[window_format]
	return window_format.lower(), window_number

def store_resolved_to_cloud(debrid_service, pack):
	setting_value = int(get_setting('liberator.store_resolved_to_cloud.%s' % debrid_service.lower(), '0'))
	return setting_value in (1, 2) if pack else setting_value == 1

def enabled_debrids_check(debrid_service):
	if not get_setting('liberator.%s.enabled' % debrid_service) == 'true': return False
	return authorized_debrid_check(debrid_service)

def authorized_debrid_check(debrid_service):
	if get_setting('liberator.%s.token' % debrid_service) in (None, '', 'empty_setting'): return False
	return True

def playback_settings():
	return (int(get_setting('liberator.playback.watched_percent', '90')), int(get_setting('liberator.playback.resume_percent', '5')))

def limit_resolve():
	return get_setting('liberator.playback.limit_resolve', 'false') == 'true'

def movies_directory():
	return translate_path(get_setting('liberator.movies_directory'))
	
def tv_show_directory():
	return translate_path(get_setting('liberator.tv_shows_directory'))

def download_directory(media_type):
	return translate_path(get_setting(download_directories_dict[media_type]))

def show_unaired_watchlist():
	return get_setting('liberator.show_unaired_watchlist', 'true') == 'true'

def auto_start_liberator():
	return get_setting('liberator.auto_start_liberator', 'false') == 'true'

def orac_scraping():
	return get_setting('liberator.orac_scraping', 'false') == 'true'

def orac_strict_dedupe():
	return get_setting('liberator.orac.strict_dedupe', 'false') == 'true'


def source_folders_directory(media_type, source):
	setting = 'liberator.%s.movies_directory' % source if media_type == 'movie' else 'liberator.%s.tv_shows_directory' % source
	if get_setting(setting) not in ('', 'None', None): return translate_path( get_setting(setting))
	else: return False

def paginate(is_home):
	paginate_lists = int(get_setting('liberator.paginate.lists', '0'))
	if is_home: return paginate_lists in (2, 3)
	else: return paginate_lists in (1, 3)

def page_limit(is_home):	
	return int(get_setting(paginate_dict[is_home], '20'))

def quality_filter(setting):
	return get_setting('liberator.%s' % setting).split(', ')

def audio_filters():
	setting = get_setting('liberator.filter_audio')
	if setting in ('empty_setting', ''): return []
	return setting.split(', ')

def preferred_autoplay():
	setting = get_setting('liberator.preferred_autoplay')
	if setting in ('empty_setting', ''): return []
	return setting.split(', ')

def include_prerelease_results():
	return int(get_setting('liberator.filter.include_prerelease', '0')) == 0

def auto_play(media_type):
	return get_setting('liberator.auto_play_%s' % media_type, 'false') == 'true'

def autoplay_next_episode():
	if auto_play('episode') and get_setting('liberator.autoplay_next_episode', 'false') == 'true': return True
	else: return False

def autoscrape_next_episode():
	if not auto_play('episode') and get_setting('liberator.autoscrape_next_episode', 'false') == 'true': return True
	else: return False



def auto_episode_group():
	return int(get_setting('liberator.results.auto_episode_group', '0'))

def auto_nextep_settings(play_type):
	play_type = 'autoplay' if play_type == 'autoplay_nextep' else 'autoscrape'
	window_percentage = 100 - int(get_setting('liberator.%s_next_window_percentage' % play_type, '95'))
	use_chapters = get_setting('liberator.%s_use_chapters' % play_type, 'true') == 'true'
	scraper_time = 80
	if play_type == 'autoplay':
		alert_method = int(get_setting('liberator.autoplay_alert_method', '0'))
		default_action = default_action_dict[get_setting('liberator.autoplay_default_action', '1')]
	else: alert_method, default_action = '', ''
	return {'scraper_time': scraper_time, 'window_percentage': window_percentage, 'alert_method': alert_method, 'default_action': default_action, 'use_chapters': use_chapters}

def filter_status(filter_type):
	return int(get_setting('liberator.filter.%s' % filter_type, '0'))

def ignore_results_filter():
	return int(get_setting('liberator.results.ignore_filter', '0'))



def lists_sort_order(setting):
	return int(get_setting('liberator.sort.%s' % setting, '0'))

def show_specials():
	return get_setting('liberator.show_specials', 'false') == 'true'

def single_ep_unwatched_episodes():
	return get_setting('liberator.single_ep_unwatched_episodes', 'false') == 'true'

def single_ep_display_format(is_external):
	if is_external: setting, default = 'liberator.single_ep_display_widget', '1'
	else: setting, default = 'liberator.single_ep_display', ''
	return int(get_setting(setting, default))

def easynews_active():
	if get_setting('liberator.provider.easynews', 'false') == 'true': easynews_status = easynews_authorized()
	else: easynews_status = False
	return easynews_status

def easynews_authorized():
	easynews_user = get_setting('liberator.easynews_user', 'empty_setting')
	easynews_password = get_setting('liberator.easynews_password', 'empty_setting')
	if easynews_user in ('empty_setting', '') or easynews_password in ('empty_setting', ''): easynews_status = False
	else: easynews_status = True
	return easynews_status

def extras_enable_extra_ratings():
	return get_setting('liberator.extras.enable_extra_ratings', 'true') == 'true'

def extras_enable_scrollbars():
	return get_setting('liberator.extras.enable_scrollbars', 'true')

def extras_enabled_menus():
	setting = get_setting('liberator.extras.enabled', '2000,2050,2051,2052,2053,2054,2055,2056,2057,2058,2059,2060,2061,2062')
	if setting in ('', None, 'noop', []): return []
	return [int(i) for i in setting.split(',')]

def recommend_service():
	return int(get_setting('liberator.recommend_service', '0'))

def recommend_seed():
	return int(get_setting('liberator.recommend_seed', '5'))

def tv_progress_location():
	return int(get_setting('liberator.tv_progress_location', '0'))

def check_prescrape_sources(scraper, media_type):
	if scraper in prescrape_scrapers_tuple: return get_setting('liberator.check.%s' % scraper) == 'true'
	if get_setting('liberator.check.%s' % scraper) == 'true' and auto_play(media_type): return True
	else: return False


def filter_by_name(scraper):
	if get_property('fs_filterless_search') == 'true': return False
	return get_setting('liberator.%s.title_filter' % scraper, 'false') == 'true'

def easynews_language_filter():
	enabled = get_setting('liberator.easynews.filter_lang') == 'true'
	if enabled: filters = get_setting('liberator.easynews.lang_filters').split(', ')
	else: filters = []
	return enabled, filters

def results_sort_order():
	sort_direction = -1 if get_setting('liberator.results.size_sort_direction') == '0' else 1
	return (
			lambda k: (k['quality_rank'], k['provider_rank'], sort_direction*k['size']), #Quality, Provider, Size
			lambda k: (k['quality_rank'], sort_direction*k['size'], k['provider_rank']), #Quality, Size, Provider
			lambda k: (k['provider_rank'], k['quality_rank'], sort_direction*k['size']), #Provider, Quality, Size
			lambda k: (k['provider_rank'], sort_direction*k['size'], k['quality_rank']), #Provider, Size, Quality
			lambda k: (sort_direction*k['size'], k['quality_rank'], k['provider_rank']), #Size, Quality, Provider
			lambda k: (sort_direction*k['size'], k['provider_rank'], k['quality_rank'])  #Size, Provider, Quality
			)[int(get_setting('liberator.results.sort_order', '1'))]

def active_internal_scrapers():
	settings = ['provider.easynews', 'provider.folders']
	settings_append = settings.append
	for item in internal_scrapers_clouds_list:
		if enabled_debrids_check(item[0]): settings_append(item[1])
	active = [i.split('.')[1] for i in settings if get_setting('liberator.%s' % i) == 'true']
	return active

def provider_sort_ranks():
	en_priority = int(get_setting('liberator.en.priority', '7'))
	rd_priority = int(get_setting('liberator.rd.priority', '8'))
	ad_priority = int(get_setting('liberator.ad.priority', '9'))
	pm_priority = int(get_setting('liberator.pm.priority', '10'))
	oc_priority = int(get_setting('liberator.oc.priority', '10'))
	ed_priority = int(get_setting('liberator.ed.priority', '10'))
	tb_priority = int(get_setting('liberator.tb.priority', '10'))
	return {'easynews': en_priority, 'real-debrid': rd_priority, 'premiumize.me': pm_priority, 'alldebrid': ad_priority, 'offcloud': oc_priority, 'easydebrid': ed_priority,
			'torbox': tb_priority, 'rd_cloud': rd_priority, 'pm_cloud': pm_priority, 'ad_cloud': ad_priority, 'oc_cloud': oc_priority, 'tb_cloud': tb_priority, 'folders': 0}

def sort_to_top(provider):
	return get_setting(sort_to_top_dict[provider]) == 'true'

def auto_resume(media_type):
	auto_resume = get_setting('liberator.auto_resume_%s' % media_type)
	if auto_resume == '1': return True
	if auto_resume == '2' and auto_play(media_type): return True
	else: return False

def scraping_settings():
	highlight_type = int(get_setting('liberator.highlight.type', '0'))
	if highlight_type == 2:
		highlight = get_setting('liberator.scraper_single_highlight', 'FF008EB2')
		return {'highlight_type': 1, '4k': highlight, '1080p': highlight, '720p': highlight, 'sd': highlight}
	easynews_highlight, debrid_cloud_highlight, folders_highlight = '', '', ''
	rd_highlight, pm_highlight, ad_highlight, oc_highlight, ed_highlight, tb_highlight = '', '', '', '', '', ''
	highlight_4K, highlight_1080P, highlight_720P, highlight_SD = '', '', '', ''
	if highlight_type == 0:
		easynews_highlight = get_setting('liberator.provider.easynews_highlight', 'FF00B3B2')
		debrid_cloud_highlight = get_setting('liberator.provider.debrid_cloud_highlight', 'FF7A01CC')
		folders_highlight = get_setting('liberator.provider.folders_highlight', 'FFB36B00')
		rd_highlight = get_setting('liberator.provider.rd_highlight', 'FF3C9900')
		pm_highlight = get_setting('liberator.provider.pm_highlight', 'FFFF3300')
		ad_highlight = get_setting('liberator.provider.ad_highlight', 'FFE6B800')
		oc_highlight = get_setting('liberator.provider.oc_highlight', 'FF008EB2')
		ed_highlight = get_setting('liberator.provider.ed_highlight', 'FF3233FF')
		tb_highlight = get_setting('liberator.provider.tb_highlight', 'FF01662A')
	else:
		highlight_4K = get_setting('liberator.scraper_4k_highlight', 'FFFF00FE')
		highlight_1080P = get_setting('liberator.scraper_1080p_highlight', 'FFE6B800')
		highlight_720P = get_setting('liberator.scraper_720p_highlight', 'FF3C9900')
		highlight_SD = get_setting('liberator.scraper_SD_highlight', 'FF0166FF')
	return {'highlight_type': highlight_type, 'real-debrid': rd_highlight, 'premiumize': pm_highlight, 'alldebrid': ad_highlight,
			'offcloud': oc_highlight, 'easydebrid': ed_highlight, 'torbox': tb_highlight, 'rd_cloud': debrid_cloud_highlight,
			'pm_cloud': debrid_cloud_highlight, 'ad_cloud': debrid_cloud_highlight, 'oc_cloud': debrid_cloud_highlight, 'tb_cloud': debrid_cloud_highlight,
			'easynews': easynews_highlight, 'folders': folders_highlight, 'orac': rd_highlight, '4k': highlight_4K, '1080p': highlight_1080P, '720p': highlight_720P, 'sd': highlight_SD}

def omdb_api_key():
	return get_setting('liberator.omdb_api', 'empty_setting')

def default_all_episodes():
	return int(get_setting('liberator.default_all_episodes', '0'))

def get_meta_filter():
	return get_setting('liberator.meta_filter', 'true')

def mpaa_region():
	return get_setting('liberator.mpaa_region', 'US')

def widget_hide_next_page():
	return get_setting('liberator.widget_hide_next_page', 'false') == 'true'

def widget_hide_watched():
	return get_setting('liberator.widget_hide_watched', 'false') == 'true'

def calendar_sort_order():
	return int(get_setting('liberator.trakt.calendar_sort_order', '0'))

def date_offset():
	return int(get_setting('liberator.datetime.offset', '0')) + 5

def media_open_action(media_type):
	return int(get_setting('liberator.media_open_action_%s' % media_type, '0'))

def watched_indicators():
	if not trakt_user_active(): return 0
	return 0

def flatten_episodes():
	return get_setting('liberator.trakt.flatten_episodes', 'false') == 'true'

def nextep_method():
	return int(get_setting('liberator.nextep.method', '0'))

def nextep_limit_history():
	return get_setting('liberator.nextep.limit_history', 'false') == 'true'

def nextep_limit():
	return int(get_setting('liberator.nextep.limit', '20'))

def nextep_include_unwatched():
	return int(get_setting('liberator.nextep.include_unwatched', '0'))

def nextep_include_airdate():
	return get_setting('liberator.nextep.include_airdate', 'false') == 'true'

def nextep_airing_today():
	return get_setting('liberator.nextep.airing_today', 'false') == 'true'

def nextep_include_unaired():
	return get_setting('liberator.nextep.include_unaired', 'false') == 'true'

def nextep_sort_key():
	return nextep_sort_key_dict[int(get_setting('liberator.nextep.sort_type', '0'))]

def nextep_sort_direction():
	return int(get_setting('liberator.nextep.sort_order', '0')) == 0

def update_delay():
	return int(get_setting('liberator.update.delay', '45'))

def update_action():
	return int(get_setting('liberator.update.action', '2'))
