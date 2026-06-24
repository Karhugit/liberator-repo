# -*- coding: utf-8 -*-
from apis.orac_api import _get_data_via_ipc
from caches.settings_cache import get_setting
try:
    import xbmc
    def _log(msg): xbmc.log('[Liberator][Fanart] %s' % msg, xbmc.LOGINFO)
except Exception:
    def _log(msg): print('[Liberator][Fanart] %s' % msg)

def fanart_sync():
    api_key = get_setting('liberator.fanart_api_key', '')
    enabled = get_setting('liberator.fanart_enabled', 'false')
    storage_mode = get_setting('liberator.fanart_storage_mode_name', 'URL')

    _log('fanart_sync called - values read from Kodi settings:')
    _log('  api_key      = %s' % repr(api_key))
    _log('  enabled      = %s' % repr(enabled))
    _log('  storage_mode = %s' % repr(storage_mode))

    params = {
        'fanart_api_key': api_key,
        'fanart_enabled': enabled,
        'fanart_storage_mode': storage_mode
    }

    _log('Sending POST /api/config/fanart request via Orac IPC...')
    result = _get_data_via_ipc('update_fanart_settings', params)
    _log('Orac response: %s' % repr(result))
