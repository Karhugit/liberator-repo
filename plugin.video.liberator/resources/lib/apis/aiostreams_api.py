# -*- coding: utf-8 -*-
from apis.orac_api import _get_data_via_ipc
from caches.settings_cache import get_setting
try:
    import xbmc
    def _log(msg): xbmc.log('[Liberator][AIOStreams] %s' % msg, xbmc.LOGINFO)
except Exception:
    def _log(msg): print('[Liberator][AIOStreams] %s' % msg)

def aiostreams_sync():
    username = get_setting('aio.username', 'empty_setting')
    password = get_setting('aio.password', 'empty_setting')
    instance_id = get_setting('aiostreams_instance', '0')
    custom_url = get_setting('aio.custom_url', 'empty_setting')

    # Mask password for logging - show only first 2 chars
    masked_pw = (password[:2] + '***') if password and password not in ('empty_setting', '') else repr(password)
    _log('aiostreams_sync called - values read from Kodi settings:')
    _log('  username    = %s' % repr(username))
    _log('  password    = %s' % masked_pw)
    _log('  instance_id = %s' % repr(instance_id))
    _log('  custom_url  = %s' % repr(custom_url))

    params = {
        'aio.username': username,
        'aio.password': password,
        'aiostreams_instance': instance_id,
        'aio.custom_url': custom_url
    }

    _log('Sending PUT /update_aiostreams_settings to Orac...')
    result = _get_data_via_ipc('update_aiostreams_settings', params)
    _log('Orac response: %s' % repr(result))
