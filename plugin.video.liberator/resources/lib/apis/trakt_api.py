# -*- coding: utf-8 -*-
import json
import time
import requests
from urllib.parse import unquote, quote_plus
from caches.settings_cache import get_setting, set_setting
from caches.main_cache import cache_object
from caches.lists_cache import lists_cache_object
from modules import kodi_utils, settings
from modules.utils import sort_list, sort_for_article, get_datetime, timedelta, replace_html_codes, copy2clip, title_key, jsondate_to_datetime as js2date
from modules.thread_manager import make_thread_list
from apis.orac_api import _get_data_via_ipc

sleep, with_media_removals, get_property = kodi_utils.sleep, kodi_utils.with_media_removals, kodi_utils.get_property
logger, notification, xbmc_player, confirm_dialog = kodi_utils.logger, kodi_utils.notification, kodi_utils.xbmc_player, kodi_utils.confirm_dialog
kodi_dialog, addon_installed, addon_enabled, addon = kodi_utils.kodi_dialog, kodi_utils.addon_installed, kodi_utils.addon_enabled, kodi_utils.addon
path_check, get_icon, clear_property, remove_keys = kodi_utils.path_check, kodi_utils.get_icon, kodi_utils.clear_property, kodi_utils.remove_keys
execute_builtin, select_dialog, kodi_refresh = kodi_utils.execute_builtin, kodi_utils.select_dialog, kodi_utils.kodi_refresh
progress_dialog, external, trakt_user_active, show_unaired_watchlist = kodi_utils.progress_dialog, kodi_utils.external, settings.trakt_user_active, settings.show_unaired_watchlist
lists_sort_order, trakt_client, trakt_secret, tmdb_api_key = settings.lists_sort_order, settings.trakt_client, settings.trakt_secret, settings.tmdb_api_key
empty_setting_check = (None, 'empty_setting', '')
standby_date = '2050-01-01T01:00:00.000Z'
res_format = '%Y-%m-%dT%H:%M:%S.%fZ'
API_ENDPOINT = 'https://api.trakt.tv/%s'
timeout = 20
EXPIRY_1_DAY, EXPIRY_1_WEEK = 24, 168

def no_client_key():
    notification('Please set a valid Trakt Client ID Key')
    return None

def no_secret_key():
    notification('Please set a valid Trakt Client Secret Key')
    return None

def call_trakt(path, params={}, data=None, is_delete=False, with_auth=True, method=None, pagination=False, page_no=1):
    def send_query():
        resp = None
        if with_auth:
            try:
                try: expires_at = float(get_setting('liberator.trakt.expires'))
                except: expires_at = 0.0
                if time.time() > expires_at: trakt_refresh_token()
            except: pass
            token = get_setting('liberator.trakt.token')
            if token: headers['Authorization'] = 'Bearer ' + token
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
    if status_code == 401:
        if xbmc_player().isPlaying() == False:
            if with_auth and confirm_dialog(heading='Authorize Trakt', text='You must authenticate with Trakt. Do you want to authenticate now?') and trakt_authenticate():
                response = send_query()
            else: pass
        else: return
    elif status_code == 429:
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

def trakt_get_device_code():
    CLIENT_ID = trakt_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    data = {'client_id': CLIENT_ID}
    return call_trakt('oauth/device/code', data=data, with_auth=False)

def trakt_get_device_token(device_codes):
    CLIENT_ID = trakt_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    CLIENT_SECRET = trakt_secret()
    if CLIENT_SECRET in empty_setting_check: return no_secret_key()
    result = None
    try:
        headers = {'Content-Type': 'application/json', 'trakt-api-version': '2', 'trakt-api-key': CLIENT_ID}
        data = {'code': device_codes['device_code'], 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
        start = time.time()
        expires_in = device_codes['expires_in']
        sleep_interval = device_codes['interval']
        user_code = str(device_codes['user_code'])
        try: copy2clip(user_code)
        except: pass
        content = '[CR]Navigate to: [B]%s[/B][CR]Enter the following code: [B]%s[/B]' % (str(device_codes['verification_url']), user_code)
        progressDialog = progress_dialog('Trakt Authorize', get_icon('trakt_qrcode'))
        progressDialog.update(content, 0)
        try:
            time_passed = 0
            while not progressDialog.iscanceled() and time_passed < expires_in:
                sleep(max(sleep_interval, 1)*1000)
                response = requests.post(API_ENDPOINT % 'oauth/device/token', data=json.dumps(data), headers=headers, timeout=timeout)
                status_code = response.status_code
                if status_code == 200:
                    result = response.json()
                    break
                elif status_code == 400:
                    time_passed = time.time() - start
                    progress = int(100 * time_passed/expires_in)
                    progressDialog.update(content, progress)
                else: break
        except: pass
        try: progressDialog.close()
        except: pass
    except: pass
    return result

def trakt_refresh_token():
    CLIENT_ID = trakt_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    CLIENT_SECRET = trakt_secret()
    if CLIENT_SECRET in empty_setting_check: return no_secret_key()
    data = {        
        'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET, 'redirect_uri': 'urn:ietf:wg:oauth:2.0:oob',
        'grant_type': 'refresh_token', 'refresh_token': get_setting('liberator.trakt.refresh')}
    response = call_trakt("oauth/token", data=data, with_auth=False)
    if response:
        set_setting('trakt.token', response["access_token"])
        set_setting('trakt.refresh', response["refresh_token"])
        set_setting('trakt.expires', str(time.time() + 86000))

def trakt_authenticate(dummy=''):
    code = trakt_get_device_code()
    token = trakt_get_device_token(code)
    if token:
# Set up ipc parameters for orac
        params = {}
        params['trakt_token'] = token["access_token"]
        params['trakt_refresh'] = token["refresh_token"]
        params['trakt_expires'] = str(time.time() + 86000)
        params['client_id'] = trakt_client()
        params['client_secret'] = trakt_secret()

        set_setting('trakt.token', token["access_token"])
        set_setting('trakt.refresh', token["refresh_token"])
        set_setting('trakt.expires', str(time.time() + 86000))
        set_setting('watched_indicators', '1')
        sleep(1000)
        try:
            user = call_trakt('/users/me')
            params['trakt_user'] = str(user['username'])
            set_setting('trakt.user', str(user['username']))
            _get_data_via_ipc('update_trakt_tokens', params)
        except: pass
        notification('Trakt Account Authorized', 3000)
#        trakt_sync_activities(force_update=True)
        return True
    notification('Trakt Error Authorizing', 3000)
    return False

def trakt_revoke_authentication(dummy=''):
    set_setting('trakt.user', 'empty_setting')
    set_setting('trakt.expires', '')
    set_setting('trakt.token', '')
    set_setting('trakt.refresh', '')
    set_setting('watched_indicators', '0')
    notification('Trakt Account Authorization Reset', 3000)
    CLIENT_ID = trakt_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    CLIENT_SECRET = trakt_secret()
    if CLIENT_SECRET in empty_setting_check: return no_secret_key()
    data = {'token': get_setting('liberator.trakt.token'), 'client_id': CLIENT_ID, 'client_secret': CLIENT_SECRET}
    response = call_trakt("oauth/revoke", data=data, with_auth=False)

def make_trakt_slug(name):
    import re
    name = name.strip()
    name = name.lower()
    name = re.sub('[^a-z0-9_]', '-', name)
    name = re.sub('--+', '-', name)
    return name

