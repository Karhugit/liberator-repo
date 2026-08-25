# -*- coding: utf-8 -*-
import json
import time
import requests
from caches.settings_cache import get_setting
from modules import kodi_utils, settings
from modules.utils import sort_list

sleep, get_property = kodi_utils.sleep, kodi_utils.get_property
logger, notification = kodi_utils.logger, kodi_utils.notification
trakt_user_active = settings.trakt_user_active
trakt_client = settings.trakt_client
empty_setting_check = (None, 'empty_setting', '')
API_ENDPOINT = 'https://api.trakt.tv/%s'
timeout = 20

def no_client_key():
    notification('Please set a valid Trakt Client ID Key')
    return None

def call_trakt(path, params={}, data=None, is_delete=False, with_auth=True, method=None, pagination=False, page_no=1):
    def send_query():
        resp = None
        if with_auth:
            token = get_setting('liberator.trakt.token')
            if token and token not in empty_setting_check:
                headers['Authorization'] = 'Bearer ' + token
        try:
            if method:
                if method == 'post':
                    resp = requests.post(API_ENDPOINT % path, headers=headers, timeout=timeout)
                elif method == 'delete':
                    resp = requests.delete(API_ENDPOINT % path, headers=headers, timeout=timeout)
                elif method == 'sort_by_headers':
                    resp = requests.get(API_ENDPOINT % path, params=params, headers=headers, timeout=timeout)
            elif data is not None:
                assert not params
                resp = requests.post(API_ENDPOINT % path, json=data, headers=headers, timeout=timeout)
            elif is_delete: resp = requests.delete(API_ENDPOINT % path, headers=headers, timeout=timeout)
            else: resp = requests.get(API_ENDPOINT % path, params=params, headers=headers, timeout=timeout)
            resp.raise_for_status()
        except Exception as e: return logger('Trakt Error', str(e))
        return resp
    CLIENT_ID = trakt_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': CLIENT_ID}
    if pagination: params['page'] = page_no
    response = send_query()
    try: status_code = response.status_code
    except: return None
    if status_code == 429:
        headers = response.headers
        if 'Retry-After' in headers:
            sleep(1000 * headers['Retry-After'])
            response = send_query()
    response.encoding = 'utf-8'
    try: result = response.json()
    except: return None
    headers = response.headers
    if method == 'sort_by_headers' and 'X-Sort-By' in headers and 'X-Sort-How' in headers:
        try: result = sort_list(headers['X-Sort-By'], headers['X-Sort-How'], result)
        except: pass
    if pagination: return (result, headers['X-Pagination-Page-Count'])
    else: return result

def make_trakt_slug(name):
    import re
    name = name.strip()
    name = name.lower()
    name = re.sub('[^a-z0-9_]', '-', name)
    name = re.sub('--+', '-', name)
    return name

