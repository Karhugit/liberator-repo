# -*- coding: utf-8 -*-
import requests
from core.kodi import logger
from core.settings import orac_base_url


class OracClientError(Exception):
    """Raised when an Orac HTTP request fails or returns invalid JSON."""


class OracNotConfiguredError(OracClientError):
    """Raised when Orac Server address is not configured in settings."""


class OracClient:
    """Direct HTTP client for Orac Server using a persistent requests.Session."""

    def __init__(self, base_url, timeout=60):
        self.base_url = base_url.rstrip('/')
        self.timeout = timeout
        self.session = requests.Session()

    def _request(self, method, endpoint, params=None, json_body=None):
        url = f'{self.base_url}/{endpoint.lstrip("/")}'
        logger('OracClient', f'{method} {url} params={params}')
        try:
            resp = self.session.request(
                method, url, params=params, json=json_body, timeout=self.timeout
            )
            resp.raise_for_status()
            if method in ('PUT', 'POST') and not resp.content:
                return {'status': 'ok'}
            return resp.json()
        except requests.exceptions.RequestException as exc:
            logger('OracClient', f'HTTP error on {url}: {exc}')
            raise OracClientError(f'Network error connecting to Orac: {exc}') from exc
        except ValueError as exc:
            logger('OracClient', f'JSON decode error on {url}: {exc}')
            raise OracClientError(f'Invalid JSON from Orac: {exc}') from exc

    def get(self, endpoint, params=None):
        return self._request('GET', endpoint, params=params)

    def post(self, endpoint, params=None, json_body=None):
        return self._request('POST', endpoint, params=params, json_body=json_body)

    def put(self, endpoint, params=None, json_body=None):
        return self._request('PUT', endpoint, params=params, json_body=json_body)

    # --- Lists & Library ---
    def get_lists(self, params=None):
        return self.get('lists', params=params)

    def get_list_overview(self, params=None):
        return self.get('list', params=params)

    def get_next_episodes(self, params=None):
        return self.get('next_episodes', params=params)

    def force_sync(self, params=None):
        return self.get('force_sync', params=params)

    def update_list_library_status(self, params=None):
        return self.put('update_list_library_status', params=params)

    def unlike_trakt_list(self, params=None):
        return self.put('unlike_trakt_list', params=params)

    def add_list_options(self, params=None):
        req = dict(params or {})
        req['name'] = 'add_list_options'
        return self.get('lists', params=req)

    def remove_list_options(self, params=None):
        req = dict(params or {})
        req['name'] = 'remove_list_options'
        return self.get('lists', params=req)

    def add_to_list(self, params=None):
        return self.put('add_to_list', params=params)

    def remove_from_list(self, params=None):
        return self.put('remove_from_list', params=params)

    # --- Media Details ---
    def get_movie_details(self, params=None):
        return self.get('movie', params=params)

    def get_show_details(self, params=None):
        return self.get('show', params=params)

    def get_seasons_overview(self, params=None):
        return self.get('seasons', params=params)

    def get_collections(self, params=None):
        return self.get('collections/movies', params=params)

    def get_movie_recommendations(self, params=None):
        return self.get('recommendations/movies', params=params)

    def get_reviews(self, params=None):
        return self.get('reviews', params=params)

    def search_person(self, query, page=1):
        return self.get('person/search', params={'query': query, 'page': page})

    def get_person_details(self, person_id):
        return self.get(f'person/{person_id}')

    # --- Watched Status ---
    def mark_watched(self, params=None):
        return self.put('watched', params=params)

    def drop_tvshow(self, params=None):
        return self.put('drop_tvshow', params=params)

    # --- Scraping & Playback ---
    def scrape(self, params=None):
        return self.get('scrape', params=params)

    def resolve(self, params=None):
        return self.get('resolve', params=params)

    def get_fast_start_episode(self, params=None):
        return self.get('fast_start_episode', params=params)

    def mark_undesirable(self, params=None):
        return self.put('mark_undesirable', params=params)

    # --- Search, Discovery & Indexers ---
    def search_tmdb(self, params=None):
        return self.get('search_tmdb', params=params)

    def discover_movie(self, params=None):
        return self.get('discover/movie', params=params)

    def discover_tvshow(self, params=None):
        return self.get('discover/tvshow', params=params)

    def get_genres(self, params=None):
        return self.get('get_genres', params=params)

    def get_tmdb_keywords(self, params=None):
        return self.get('tmdb_keywords', params=params)

    def get_watch_providers(self, media_type=None):
        params = {'media_type': media_type} if media_type else None
        result = self.get('providers', params=params)
        if result and result.get('success'):
            return result.get('providers', [])
        return []

    def get_available_languages(self, params=None):
        return self.get('get_available_languages', params=params)

    def get_external_indexes(self, params=None):
        return self.get('get_external_indexes', params=params)

    def add_external_index(self, json_body):
        return self.put('add_ext_index', json_body=json_body)

    def delete_external_index(self, params=None):
        return self.put('del_ext_index', params=params)

    def get_internal_indexes(self, params=None):
        return self.get('get_internal_indexes', params=params)

    def add_internal_index(self, json_body):
        return self.put('add_internal_index', json_body=json_body)

    def delete_internal_index(self, params=None):
        return self.put('del_internal_index', params=params)

    def internal_index_contents(self, params=None):
        return self.get('internal_index_contents', params=params)

    # --- Tags ---
    def get_all_tags(self, details=False):
        return self.get('tags', params={'details': 'true'} if details else None)

    def get_tag_items(self, tag_name):
        return self.get(f'tags/{tag_name}/items')

    def get_tags_for_item(self, media_type, tmdb_id):
        return self.get(f'tags/{media_type}/{tmdb_id}')

    def add_tag(self, media_type, tmdb_id, tag_name):
        return self.put('add_tag', params={'media_type': media_type, 'tmdb_id': tmdb_id}, json_body={'tag': tag_name})

    def remove_tag(self, media_type, tmdb_id, tag_name):
        return self.put('remove_tag', params={'media_type': media_type, 'tmdb_id': tmdb_id, 'tag': tag_name})

    # --- Anime ---
    def get_anime_list(self, params=None):
        return self.get('anime/list', params=params)

    def get_anime_info(self, params=None):
        return self.get('anime/info', params=params)

    def resolve_anime_coordinates(self, params=None):
        return self.get('anime/resolve', params=params)

    def get_anime_aliases(self, params=None):
        return self.get('anime/aliases', params=params)

    def get_anime_status(self, params=None):
        return self.get('anime/status', params=params)

    def sync_anime_mappings(self, params=None):
        return self.post('anime/sync_mappings', params=params)

    def mark_anime_watched(self, params=None):
        return self.put('anime/watched', params=params)

    # --- Premiumize Cloud (via Orac) ---
    def premiumize_cloud(self, params=None):
        return self.get('api/debrid/premiumize/cloud', params=params)

    def premiumize_cloud_all(self, params=None):
        return self.get('api/debrid/premiumize/cloud_all', params=params)

    def premiumize_transfers(self, params=None):
        return self.get('api/debrid/premiumize/transfers', params=params)

    def premiumize_account_info(self, params=None):
        return self.get('api/debrid/premiumize/account_info', params=params)

    def premiumize_item_details(self, params=None):
        return self.get('api/debrid/premiumize/item_details', params=params)

    def premiumize_rename(self, body):
        return self.post('api/debrid/premiumize/rename', json_body=body)

    def premiumize_delete(self, body):
        return self.post('api/debrid/premiumize/delete', json_body=body)

    def scan_local_folder(self, params=None):
        return self.get('api/local_folders/scan', params=params)


_CLIENT_CACHE = {'url': None, 'client': None}


def get_orac_client():
    base_url = orac_base_url()
    if not base_url:
        raise OracNotConfiguredError('Orac server address is not configured.')
    if _CLIENT_CACHE['client'] is None or _CLIENT_CACHE['url'] != base_url:
        _CLIENT_CACHE['url'] = base_url
        _CLIENT_CACHE['client'] = OracClient(base_url)
    return _CLIENT_CACHE['client']
