# -*- coding: utf-8 -*-
from caches.settings_cache import get_setting
from modules.settings import tmdb_api_key
from modules.kodi_utils import make_session, notification

base_url = 'https://api.themoviedb.org/3'
movies_append = 'external_ids,videos,credits,release_dates,alternative_titles,translations,images,keywords'
empty_setting_check = (None, 'empty_setting', '')
session = make_session(base_url)
timeout = 20.0

def no_api_key():
	notification('Please set a valid TMDb API Key')
	return []

# This is used to check the api key
def movie_details(tmdb_id, api_key):
	try:
		url = '%s/movie/%s?api_key=%s&language=en&append_to_response=%s&include_image_language=en' % (base_url, tmdb_id, api_key, movies_append)
		return get_tmdb(url).json()
	except: return None

def episode_groups_data(tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/tv/%s/episode_groups?api_key=%s' % (base_url, tmdb_id, api_key)
	try: return get_tmdb(url).json()
	except: return None

def episode_group_details(group_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/tv/episode_group/%s?api_key=%s' % (base_url, group_id, api_key)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_company_id(query):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/search/company?api_key=%s&query=%s' % (base_url, api_key, query)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_media_images(media_type, tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	if media_type in ('movie', 'movies'): media_type = 'movie'
	else: media_type = 'tv'
	url = '%s/%s/%s/images?include_image_language=en,null&api_key=%s' % (base_url, media_type, tmdb_id, api_key)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_media_videos(media_type, tmdb_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	if media_type in ('movie', 'movies'): media_type = 'movie'
	else: media_type = 'tv'
	url = '%s/%s/%s/videos?api_key=%s' % (base_url, media_type, tmdb_id, api_key)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_popular_people(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/person/popular?api_key=%s&language=en&page=%s' % (base_url, api_key, page_no)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_trending_people_day(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/trending/person/day?api_key=%s&page=%s' % (base_url, api_key, page_no)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_trending_people_week(page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/trending/person/week?api_key=%s&page=%s' % (base_url, api_key, page_no)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_people_full_info(actor_id):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/person/%s?api_key=%s&language=en&append_to_response=external_ids,combined_credits,images,tagged_images' % (base_url, actor_id, api_key)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_people_info(query, page_no=1):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	from modules.settings import get_meta_filter
	meta_filter = get_meta_filter()
	url = '%s/search/person?api_key=%s&language=en&include_adult=%s&query=%s&page=%s' % (base_url, api_key, meta_filter, query, page_no)
	try: return get_tmdb(url).json()
	except: return None

def season_episodes_details(tmdb_id, season_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	try:
		url = '%s/tv/%s/season/%s?api_key=%s&language=en&append_to_response=credits' % (base_url, tmdb_id, season_no, api_key)
		return get_tmdb(url).json()
	except: return None

def get_reviews_data(media_type, tmdb_id):
	reviews_list, all_data = [], []
	template = '[B]%02d. %s%s[/B][CR][CR]%s'
	media_type = 'movie' if media_type in ('movie', 'movies') else 'tv'
	function = tmdb_movies_reviews if media_type == 'movie' else tmdb_tv_reviews
	next_page, total_pages = 1, 1
	try:
		while next_page <= total_pages:
			data = function(tmdb_id, next_page)
			all_data += data['results']
			total_pages = data['total_pages']
			next_page = data['page'] + 1
		if all_data:
			for count, item in enumerate(all_data, 1):
				try:
					user = item['author'].upper()
					rating = item['author_details'].get('rating')
					if rating: rating = ' - %s/10' % str(rating).split('.')[0]
					else: rating = ''
					content = template % (count, user, rating, item['content'])
					reviews_list.append(content)
				except: pass
	except: pass
	return reviews_list

def tmdb_movies_reviews(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/movie/%s/reviews?api_key=%s&page=%s' % (base_url, tmdb_id, api_key, page_no)
	try: return get_tmdb(url).json()
	except: return None

def tmdb_tv_reviews(tmdb_id, page_no):
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return no_api_key()
	url = '%s/tv/%s/reviews?api_key=%s&page=%s' % (base_url, tmdb_id, api_key, page_no)
	try: return get_tmdb(url).json()
	except: return None

def get_tmdb(url):
	try: response = session.get(url, timeout=timeout)
	except: response = None
	return response

def tmdb_get_details(dummy=''):
	pass

# Helper metadata functions transitioned from deleted modules/metadata.py
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
	api_key = tmdb_api_key()
	if api_key in empty_setting_check: return False
	try:
		url = '%s/tv/%s/keywords?api_key=%s' % (base_url, tmdb_id, api_key)
		response = get_tmdb(url)
		if response.status_code == 200:
			keywords = response.json().get('results', [])
			return any(i['id'] == 210024 for i in keywords)
	except: pass
	return False
