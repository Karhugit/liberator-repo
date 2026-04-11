import requests
from modules.kodi_utils import notification
from apis.orac_api import _get_data_via_ipc

def mdblist_authenticate(params):
    mdblist_api = params.get('mdblist_api')
    if not mdblist_api or mdblist_api == 'empty_setting':
        _get_data_via_ipc('update_mdblist_tokens', {'mdblist_api': 'empty_setting', 'mdblist.user': 'empty_setting'})
        return

    try:
        url = f"https://api.mdblist.com/user?apikey={mdblist_api}"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        
        username = data.get('username') or data.get('name') or 'mdblist_user'
        
        _get_data_via_ipc('update_mdblist_tokens', {'mdblist_api': mdblist_api, 'mdblist.user': username})
        notification('MDBList', f'Authenticated as {username}')

    except Exception as e:
        notification('MDBList', 'Authentication Failed.')
        _get_data_via_ipc('update_mdblist_tokens', {'mdblist_api': 'empty_setting', 'mdblist.user': 'empty_setting'})
