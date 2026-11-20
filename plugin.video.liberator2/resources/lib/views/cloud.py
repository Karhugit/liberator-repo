# -*- coding: utf-8 -*-
import xbmc
from core.kodi import (
    add_items,
    build_url,
    container_refresh,
    dialog_confirm,
    dialog_ok,
    end_directory,
    make_dir_item,
    make_listitem,
    notification,
    set_category,
    set_content,
)
from orac.client import OracClientError, get_orac_client

RUN_PLUGIN = 'RunPlugin(%s)'


def pm_files(handle, params):
    folder_id = params.get('folder_id')
    try:
        resp = get_orac_client().premiumize_cloud({'folder_id': folder_id} if folder_id else None) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    items = resp.get('content') or resp.get('items') or []
    kodi_items = []
    for entry in items:
        name = entry.get('name', 'Unnamed')
        entry_id = entry.get('id', '')
        entry_type = entry.get('type', 'file')
        cm = [(
            '[B]Delete[/B]',
            RUN_PLUGIN % build_url({'mode': 'cloud.pm_delete', 'id': entry_id, 'type': entry_type, 'name': name}),
        )]
        if entry_type == 'folder':
            kodi_items.append(make_dir_item(
                {'mode': 'cloud.pm_files', 'folder_id': entry_id, 'name': name},
                name,
                icon='folder',
                is_folder=True,
                cm_items=cm,
            ))
        else:
            stream_link = entry.get('link') or entry.get('stream_link') or ''
            li = make_listitem(name)
            li.setProperty('IsPlayable', 'true')
            li.addContextMenuItems(cm)
            url = build_url({'mode': 'cloud.pm_play', 'id': entry_id, 'link': stream_link, 'name': name})
            kodi_items.append((url, li, False))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, params.get('name', 'Premiumize Cloud'))
    end_directory(handle)


def pm_play(handle, params):
    link = params.get('link')
    item_id = params.get('id')
    name = params.get('name', 'Premiumize Stream')
    if not link and item_id:
        try:
            details = get_orac_client().premiumize_item_details({'id': item_id}) or {}
            link = details.get('link') or details.get('stream_link') or ''
        except OracClientError as exc:
            notification(str(exc))
            return
    if not link:
        notification('No playable link found')
        return
    li = make_listitem(name)
    li.setPath(link)
    xbmc.Player().play(link, li)


def pm_delete(handle, params):
    item_id = params.get('id')
    item_type = params.get('type', 'file')
    name = params.get('name', 'item')
    if not item_id or not dialog_confirm('Delete', f'Delete [B]{name}[/B] from Premiumize?'):
        return
    try:
        get_orac_client().premiumize_delete({'id': item_id, 'type': item_type})
        notification(f'Deleted {name}')
        container_refresh()
    except OracClientError as exc:
        notification(f'Delete failed: {exc}')


def pm_transfers(handle, params):
    try:
        resp = get_orac_client().premiumize_transfers() or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    transfers = resp.get('transfers') or []
    kodi_items = []
    for tr in transfers:
        name = tr.get('name', 'Transfer')
        status = tr.get('status', '')
        progress = tr.get('progress', '')
        label = f'{name} [{status} {progress}]'
        kodi_items.append(make_dir_item({'mode': 'noop'}, label, icon='premiumize', is_folder=False))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, 'Premiumize Transfers')
    end_directory(handle)


def pm_account(handle, params):
    try:
        info = get_orac_client().premiumize_account_info() or {}
        space_used = info.get('space_used', 0)
        limit_used = info.get('limit_used', 0)
        premium_until = info.get('premium_until', 'N/A')
        dialog_ok(
            'Premiumize Account',
            f'Premium Until: {premium_until}\nSpace Used: {space_used}\nFair-Use Limit: {limit_used}',
        )
    except OracClientError as exc:
        dialog_ok('Premiumize Account', f'Error: {exc}')
