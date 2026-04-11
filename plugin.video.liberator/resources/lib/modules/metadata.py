# -*- coding: utf-8 -*-
from apis import tmdb_api
from caches.meta_cache import meta_cache
from modules.utils import jsondate_to_datetime, subtract_dates
# from modules.kodi_utils import logger

movie_details, season_episodes_details = tmdb_api.movie_details, tmdb_api.season_episodes_details
episode_groups_data, episode_group_details = tmdb_api.episode_groups_data, tmdb_api.episode_group_details
metacache_get, metacache_set, metacache_get_season, metacache_set_season = meta_cache.get, meta_cache.set, meta_cache.get_season, meta_cache.set_season
writer_credits = ('Author', 'Writer', 'Screenplay', 'Characters')
alt_titles_check, finished_show_check, empty_value_check = ('US', 'GB', 'UK', ''), ('Ended', 'Canceled'), ('', 'None', None)
tmdb_image_url, youtube_url, date_format = 'https://image.tmdb.org/t/p/%s%s', 'plugin://plugin.video.youtube/play/?video_id=%s', '%Y-%m-%d'
EXPIRES_1_DAYS, EXPIRES_4_DAYS, EXPIRES_7_DAYS, EXPIRES_14_DAYS, EXPIRES_30_DAYS, EXPIRES_182_DAYS = 24, 96, 168, 336, 720, 4368
invalid_error_codes = (6, 34, 37)




def episode_groups(media_id):
	try: groups = episode_groups_data(media_id)['results']
	except: groups = None
	return groups or None

def group_details(group_id):
	return episode_group_details(group_id)

def group_episode_data(details, episode_id=None, season_number=None, episode_number=None):
	def _comparer(episode_item):
		if episode_id: return episode_item['id'] == int(episode_id)
		else: return episode_item['season_number'] == int(season_number) and episode_item['episode_number'] == int(episode_number)
	episode_data = next(({'season': item['order'], 'episode': i['order'] + 1} for item in details['groups'] for i in item['episodes'] if _comparer(i)), None)
	return episode_data

def is_anime_check(tmdb_id):
	from modules.utils import get_datetime
	from modules.settings import tmdb_api_key, mpaa_region
#	meta = tvshow_meta('tmdb_id', tmdb_id, tmdb_api_key(), mpaa_region(), get_datetime())
	genre = meta['genre']
	if not genre or 'Animation' in genre:
		try: keywords = meta.get('keywords', None) or tmdb_api.tmdb_tv_keywords(tmdb_id)['results']
		except: return False
		if not keywords: return False
		try: is_anime = next((i for i in keywords['results'] if i['id'] == 210024), None) is not None
		except: is_anime = False
		return is_anime
	return False


def movie_expiry(current_date, meta):
	try:
		difference = subtract_dates(current_date, jsondate_to_datetime(meta['premiered'], date_format, remove_time=True))
		if difference < 0: expiration = abs(difference) + 1
		elif difference <= 14: expiration = EXPIRES_7_DAYS
		elif difference <= 30: expiration = EXPIRES_14_DAYS
		elif difference <= 180: expiration = EXPIRES_30_DAYS
		else: expiration = EXPIRES_182_DAYS
	except: return EXPIRES_30_DAYS
	return max(expiration, EXPIRES_7_DAYS)

def tvshow_expiry(current_date, meta):
	try:
		if meta['status'] in finished_show_check: expiration = EXPIRES_182_DAYS
		else:
			data = subtract_dates(jsondate_to_datetime(meta['extra_info']['next_episode_to_air']['air_date'], date_format, remove_time=True), current_date) - EXPIRES_1_DAYS
			if data <= 1: expiration = EXPIRES_1_DAYS
			else: expiration = data*24
	except: expiration = EXPIRES_4_DAYS
	return expiration
