# -*- coding: utf-8 -*-
from apis.orac_api import _get_data_via_ipc
from caches.settings_cache import get_setting

def aiostreams_sync():
    username = get_setting('aio.username', 'empty_setting')
    password = get_setting('aio.password', 'empty_setting')
    instance_id = get_setting('aiostreams_instance', '0')
    custom_url = get_setting('aio.custom_url', 'empty_setting')
    
    params = {
        'aio.username': username,
        'aio.password': password,
        'aiostreams_instance': instance_id,
        'aio.custom_url': custom_url
    }
    
    # Send PUT command to Orac server
    _get_data_via_ipc('update_aiostreams_settings', params)
