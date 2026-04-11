# -*- coding: utf-8 -*-
import json
import time
import requests
from caches.settings_cache import get_setting, set_setting
from modules import kodi_utils, settings
from modules.utils import copy2clip
from apis.orac_api import _get_data_via_ipc

sleep, get_property = kodi_utils.sleep, kodi_utils.get_property
logger, notification, confirm_dialog = kodi_utils.logger, kodi_utils.notification, kodi_utils.confirm_dialog
get_icon = kodi_utils.get_icon
progress_dialog, simkl_client, simkl_secret = kodi_utils.progress_dialog, settings.simkl_client, settings.simkl_secret
empty_setting_check = (None, 'empty_setting', '')
API_ENDPOINT = 'https://api.simkl.com/%s'
timeout = 20

def no_client_key():
    notification('Please set a valid Simkl Client ID Key')
    return None

def no_secret_key():
    notification('Please set a valid Simkl Client Secret Key')
    return None

def call_simkl(path, params=None, data=None, method=None, with_auth=False):
    CLIENT_ID = simkl_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    headers = {'Content-Type': 'application/json', 'simkl-api-key': CLIENT_ID}
    
    if with_auth:
        token = get_setting('liberator.simkl.token')
        if token: headers['Authorization'] = 'Bearer ' + token

    if params is None: params = {}
    if not 'client_id' in params and not with_auth:
        params['client_id'] = CLIENT_ID

    resp = None
    try:
        url = API_ENDPOINT % path
        if method == 'post' or data is not None:
            resp = requests.post(url, json=data, params=params, headers=headers, timeout=timeout)
        elif method == 'delete':
            resp = requests.delete(url, params=params, headers=headers, timeout=timeout)
        else:
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
        resp.raise_for_status()
    except Exception as e:
        logger('Simkl Error', str(e))
        if resp is not None:
             logger('Simkl Error Response', resp.text)
        return None

    try: result = resp.json()
    except: return None
    return result

def simkl_get_device_code():
    CLIENT_ID = simkl_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    params = {'client_id': CLIENT_ID}
    return call_simkl('oauth/pin', params=params, with_auth=False)

def simkl_get_device_token(device_codes):
    CLIENT_ID = simkl_client()
    if CLIENT_ID in empty_setting_check: return no_client_key()
    result = None
    try:
        start = time.time()
        expires_in = device_codes.get('expires_in', 900)
        sleep_interval = device_codes.get('interval', 5)
        user_code = str(device_codes['user_code'])
        try: copy2clip(user_code)
        except: pass
        content = '[CR]Navigate to: [B]%s[/B][CR]Enter the following code: [B]%s[/B]' % (str(device_codes['verification_url']), user_code)
        progressDialog = progress_dialog('Simkl Authorize', get_icon('simkl_qrcode') or 'DefaultIcon.png')
        progressDialog.update(content, 0)
        try:
            time_passed = 0
            while not progressDialog.iscanceled() and time_passed < expires_in:
                sleep(max(sleep_interval, 1)*1000)
                poll_url = 'oauth/pin/%s' % user_code
                response = call_simkl(poll_url, params={'client_id': CLIENT_ID}, with_auth=False)
                if response and response.get('result') == 'OK' and 'access_token' in response:
                    result = response
                    break
                else:
                    time_passed = time.time() - start
                    progress = int(100 * time_passed/expires_in)
                    progressDialog.update(content, progress)
        except: pass
        try: progressDialog.close()
        except: pass
    except: pass
    return result

def simkl_authenticate(dummy=''):
    code = simkl_get_device_code()
    if not code or 'user_code' not in code:
        notification('Simkl Error Authorizing', 3000)
        return False
    token = simkl_get_device_token(code)
    if token and 'access_token' in token:
        params = {}
        params['simkl.token'] = token["access_token"]
        params['simkl.client'] = simkl_client()
        params['simkl.secret'] = simkl_secret()

        set_setting('simkl.token', token["access_token"])
        sleep(1000)
        try:
            user = call_simkl('users/settings', with_auth=True)
            if user and 'user' in user and 'name' in user['user']:
                username = str(user['user']['name'])
                params['simkl.user'] = username
                set_setting('simkl.user', username)
            else:
                set_setting('simkl.user', 'simkl_user')
                params['simkl.user'] = 'simkl_user'
            _get_data_via_ipc('update_simkl_tokens', params)
        except: pass
        notification('Simkl Account Authorized', 3000)
        return True
    notification('Simkl Error Authorizing', 3000)
    return False

def simkl_revoke_authentication(dummy=''):
    set_setting('simkl.user', 'empty_setting')
    set_setting('simkl.expires', '')
    set_setting('simkl.token', '')
    notification('Simkl Account Authorization Reset', 3000)
