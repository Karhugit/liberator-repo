# -*- coding: utf-8 -*-
from datetime import datetime
import xbmc
import xbmcgui
import xbmcplugin
from core.kodi import (
    FANART_PATH,
    add_items,
    build_url,
    container_refresh,
    dialog_confirm,
    dialog_ok,
    end_directory,
    get_icon,
    make_dir_item,
    make_listitem,
    notification,
    set_category,
    set_content,
)
from orac.client import OracClientError, get_orac_client

RUN_PLUGIN = 'RunPlugin(%s)'
GB_DIVISOR = float(1024 ** 3)
TORBOX_PLANS = {0: 'Free Plan', 1: 'Essential Plan', 2: 'Pro Plan', 3: 'Standard Plan'}


def _format_size(num_bytes):
    try:
        val = float(num_bytes or 0)
        if val <= 0:
            return ''
        return f'{val / GB_DIVISOR:.2f} GB'
    except (ValueError, TypeError):
        return ''


def _days_remaining(iso_str):
    if not iso_str:
        return None
    raw = str(iso_str).strip()
    for fmt in ('%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            dt = datetime.strptime(raw[:26], fmt)
            return (dt - datetime.utcnow()).days
        except ValueError:
            continue
    return None


def _play_stream(handle, url, name):
    li = make_listitem(name)
    li.setPath(url)
    info_tag = li.getVideoInfoTag()
    info_tag.setTitle(name or 'Cloud Stream')
    info_tag.setMediaType('video')
    if handle >= 0:
        xbmcplugin.setResolvedUrl(handle, True, li)
    else:
        xbmc.Player().play(url, li)


def _fail_play(handle, message):
    notification(message)
    if handle >= 0:
        xbmcplugin.setResolvedUrl(handle, False, make_listitem())


# =====================================================================
# UNIFIED MULTI-SERVICE CLOUD HANDLERS
# =====================================================================

def service_cloud(handle, params):
    service = (params.get('service') or '').lower()
    if service == 'premiumize':
        pm_files(handle, params)
        return

    icon_name = params.get('icon') or service or 'folder'
    icon_img = get_icon(icon_name)
    try:
        resp = get_orac_client().debrid_cloud(service) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    items = resp.get('items') or []
    kodi_items = []
    for count, entry in enumerate(items, 1):
        entry_id = str(entry.get('id', ''))
        name = entry.get('name') or 'Unnamed'
        entry_type = entry.get('type', 'folder')
        media_type = entry.get('media_type', 'torrent')
        size_str = _format_size(entry.get('size'))

        cm = [(
            '[B]Delete[/B]',
            RUN_PLUGIN % build_url({
                'mode': 'cloud.delete',
                'service': service,
                'id': entry_id,
                'item_type': entry_type,
                'media_type': media_type,
                'name': name,
            }),
        )]

        if entry_type == 'folder':
            parts = [f'{count:02d}', '[B]FOLDER[/B]']
            if size_str:
                parts.append(size_str)
            parts.append(name.upper())
            label = ' | '.join(parts)
            kodi_items.append(make_dir_item(
                {
                    'mode': 'cloud.browse',
                    'service': service,
                    'folder_id': entry_id,
                    'media_type': media_type,
                    'name': name,
                    'icon': icon_name,
                },
                label,
                icon=icon_name,
                is_folder=True,
                cm_items=cm,
            ))
        else:
            parts = [f'{count:02d}', '[B]FILE[/B]']
            if size_str:
                parts.append(size_str)
            parts.append(name.upper())
            label = ' | '.join(parts)
            li = make_listitem(label)
            li.setArt({'icon': icon_img, 'thumb': icon_img, 'poster': icon_img, 'fanart': FANART_PATH})
            li.setProperty('IsPlayable', 'true')
            li.addContextMenuItems(cm)
            url = build_url({
                'mode': 'cloud.play',
                'service': service,
                'link': entry.get('link', ''),
                'needs_unrestrict': str(bool(entry.get('needs_unrestrict', False))).lower(),
                'name': name,
            })
            kodi_items.append((url, li, False))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, params.get('name', 'Cloud Storage'))
    end_directory(handle, cache_to_disc=False)


def service_browse(handle, params):
    service = (params.get('service') or '').lower()
    folder_id = params.get('folder_id') or ''
    media_type = params.get('media_type', 'torrent')
    icon_name = params.get('icon') or service or 'folder'
    icon_img = get_icon(icon_name)

    try:
        resp = get_orac_client().debrid_cloud(service, folder_id=folder_id, params={'media_type': media_type}) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    items = resp.get('items') or []
    kodi_items = []
    for count, entry in enumerate(items, 1):
        name = entry.get('name') or 'Video'
        size_str = _format_size(entry.get('size'))
        parts = [f'{count:02d}', '[B]FILE[/B]']
        if size_str:
            parts.append(size_str)
        parts.append(name.upper())
        label = ' | '.join(parts)

        li = make_listitem(label)
        li.setArt({'icon': icon_img, 'thumb': icon_img, 'poster': icon_img, 'fanart': FANART_PATH})
        li.setProperty('IsPlayable', 'true')
        url = build_url({
            'mode': 'cloud.play',
            'service': service,
            'folder_id': entry.get('folder_id', folder_id),
            'file_id': entry.get('id', ''),
            'media_type': entry.get('media_type', media_type),
            'link': entry.get('link', ''),
            'needs_unrestrict': str(bool(entry.get('needs_unrestrict', False))).lower(),
            'name': name,
        })
        kodi_items.append((url, li, False))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, params.get('name', 'Cloud Folder'))
    end_directory(handle, cache_to_disc=False)


def service_downloads(handle, params):
    service = (params.get('service') or '').lower()
    if service == 'premiumize':
        pm_transfers(handle, params)
        return

    icon_name = params.get('icon') or service or 'folder'
    icon_img = get_icon(icon_name)
    try:
        resp = get_orac_client().debrid_downloads(service) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    items = resp.get('items') or []
    kodi_items = []
    for count, entry in enumerate(items, 1):
        entry_id = str(entry.get('id', ''))
        name = entry.get('name') or 'Download'
        size_str = _format_size(entry.get('size'))
        date_str = entry.get('date') or ''
        parts = [f'{count:02d}']
        if size_str:
            parts.append(size_str)
        if date_str:
            parts.append(date_str)
        parts.append(name.upper())
        label = ' | '.join(parts)

        cm = [(
            '[B]Delete[/B]',
            RUN_PLUGIN % build_url({
                'mode': 'cloud.delete',
                'service': service,
                'id': entry_id,
                'item_type': 'download',
                'name': name,
            }),
        )]
        li = make_listitem(label)
        li.setArt({'icon': icon_img, 'thumb': icon_img, 'poster': icon_img, 'fanart': FANART_PATH})
        li.setProperty('IsPlayable', 'true')
        li.addContextMenuItems(cm)
        url = build_url({
            'mode': 'cloud.play',
            'service': service,
            'link': entry.get('link', ''),
            'needs_unrestrict': 'false',
            'name': name,
        })
        kodi_items.append((url, li, False))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, params.get('name', 'History'))
    end_directory(handle, cache_to_disc=False)


def service_play(handle, params):
    service = (params.get('service') or '').lower()
    name = params.get('name', 'Cloud Stream')
    link = params.get('link', '')
    needs_unrestrict = params.get('needs_unrestrict', 'false') == 'true'

    if needs_unrestrict:
        try:
            body = {
                'link': link,
                'folder_id': params.get('folder_id', ''),
                'file_id': params.get('file_id', ''),
                'media_type': params.get('media_type', 'torrent'),
            }
            resp = get_orac_client().debrid_unrestrict(service, body) or {}
            link = resp.get('url') or ''
        except OracClientError as exc:
            _fail_play(handle, f'Failed to resolve stream: {exc}')
            return

    if not link:
        _fail_play(handle, 'No playable link found')
        return

    _play_stream(handle, link, name)


def service_delete(handle, params):
    service = (params.get('service') or '').lower()
    item_id = params.get('id') or ''
    item_type = params.get('item_type', 'torrent')
    media_type = params.get('media_type', 'torrent')
    name = params.get('name', 'item')

    if not item_id or not dialog_confirm('Delete', f'Delete [B]{name}[/B] from {service.title()}?'):
        return

    try:
        get_orac_client().debrid_delete(service, {
            'id': item_id,
            'item_type': item_type,
            'media_type': media_type,
        })
        notification(f'Deleted {name}')
        container_refresh()
    except OracClientError as exc:
        notification(f'Delete failed: {exc}')


def service_account_info(handle, params):
    service = (params.get('service') or '').lower()
    title = params.get('name') or service.title()

    try:
        client = get_orac_client()
        if service == 'premiumize':
            data = client.premiumize_account_info() or {}
        else:
            resp = client.debrid_account_info(service) or {}
            data = resp.get('data') if isinstance(resp.get('data'), dict) else resp
    except OracClientError as exc:
        dialog_ok(f'{title} Account', f'Error: {exc}')
        return

    lines = []
    if service == 'realdebrid':
        exp = data.get('expiration', '')
        days = _days_remaining(exp)
        lines.append(f'[B]Account:[/B] {data.get("email", "N/A")}')
        lines.append(f'[B]Username:[/B] {data.get("username", "N/A")}')
        lines.append(f'[B]Status:[/B] {str(data.get("type", "N/A")).capitalize()}')
        lines.append(f'[B]Expires:[/B] {str(exp)[:19].replace("T", " ") or "N/A"}')
        if days is not None:
            lines.append(f'[B]Days Remaining:[/B] {days}')
        lines.append(f'[B]Fidelity Points:[/B] {data.get("points", 0)}')
    elif service == 'premiumize':
        customer_id = data.get('customer_id', 'N/A')
        premium_until = data.get('premium_until')
        exp_str = 'N/A'
        days = None
        if premium_until:
            try:
                dt = datetime.fromtimestamp(float(premium_until))
                exp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                days = (dt - datetime.now()).days
            except (ValueError, TypeError, OSError):
                exp_str = str(premium_until)
        space_gb = _format_size(data.get('space_used')) or '0.00 GB'
        limit_used = data.get('limit_used')
        limit_str = f'{round(float(limit_used) * 100)}%' if limit_used is not None else 'N/A'
        lines.append(f'[B]Customer ID:[/B] {customer_id}')
        lines.append(f'[B]Expires:[/B] {exp_str}')
        if days is not None:
            lines.append(f'[B]Days Remaining:[/B] {days}')
        lines.append(f'[B]Cloud Storage Used:[/B] {space_gb}')
        lines.append(f'[B]Fair-Use Limit Used:[/B] {limit_str}')
    elif service == 'torbox':
        exp = data.get('premium_expires_at', '')
        days = _days_remaining(exp)
        plan = TORBOX_PLANS.get(data.get('plan'), str(data.get('plan', 'N/A')))
        lines.append(f'[B]Email:[/B] {data.get("email", "N/A")}')
        lines.append(f'[B]Customer:[/B] {data.get("customer", "N/A")}')
        lines.append(f'[B]Plan:[/B] {plan}')
        lines.append(f'[B]Expires:[/B] {str(exp)[:19].replace("T", " ") or "N/A"}')
        if days is not None:
            lines.append(f'[B]Days Remaining:[/B] {days}')
        lines.append(f'[B]Total Downloaded:[/B] {data.get("total_downloaded", 0):,}')
    elif service == 'alldebrid':
        status = 'Premium' if data.get('isPremium') else 'Not Active'
        exp_ts = data.get('premiumUntil')
        exp_str = 'N/A'
        days = None
        if exp_ts:
            try:
                dt = datetime.fromtimestamp(float(exp_ts))
                exp_str = dt.strftime('%Y-%m-%d %H:%M:%S')
                days = (dt - datetime.now()).days
            except (ValueError, TypeError, OSError):
                exp_str = str(exp_ts)
        lines.append(f'[B]Username:[/B] {data.get("username", "N/A")}')
        lines.append(f'[B]Email:[/B] {data.get("email", "N/A")}')
        lines.append(f'[B]Status:[/B] {status}')
        lines.append(f'[B]Expires:[/B] {exp_str}')
        if days is not None:
            lines.append(f'[B]Days Remaining:[/B] {days}')
    elif service == 'offcloud':
        limits = data.get('limits') if isinstance(data.get('limits'), dict) else {}
        lines.append(f'[B]Email:[/B] {data.get("email", "N/A")}')
        lines.append(f'[B]User ID:[/B] {data.get("userId", "N/A")}')
        lines.append(f'[B]Premium:[/B] {data.get("isPremium", "N/A")}')
        lines.append(f'[B]Expires:[/B] {data.get("expirationDate", "N/A")}')
        if 'cloud' in limits:
            lines.append(f'[B]Cloud Limit:[/B] {limits["cloud"]:,}')
    elif service == 'easydebrid':
        paid_until = data.get('paid_until') or data.get('expiration') or 'N/A'
        if isinstance(paid_until, (int, float)):
            try:
                paid_until = datetime.fromtimestamp(paid_until).strftime('%Y-%m-%d %H:%M:%S')
            except (ValueError, OSError):
                paid_until = str(paid_until)
        lines.append(f'[B]User ID:[/B] {data.get("id", "N/A")}')
        lines.append(f'[B]Paid Until:[/B] {paid_until}')
    elif service == 'easynews':
        exp = data.get('expires', '')
        days = _days_remaining(exp)
        lines.append(f'[B]Username:[/B] {data.get("username", "N/A")}')
        if data.get('account'):
            lines.append(f'[B]Account:[/B] {data["account"]}')
        lines.append(f'[B]Status:[/B] {data.get("status", "N/A")}')
        if exp:
            lines.append(f'[B]Expires:[/B] {exp}')
        if days is not None:
            lines.append(f'[B]Days Remaining:[/B] {days}')
        if data.get('subscription'):
            lines.append(f'[B]Subscription:[/B] {data["subscription"]}')
        if data.get('data_used'):
            lines.append(f'[B]Data Used:[/B] {data["data_used"]}')
        if data.get('data_remaining'):
            lines.append(f'[B]Data Remaining:[/B] {data["data_remaining"]}')
    else:
        for k, v in data.items():
            lines.append(f'[B]{k}:[/B] {v}')

    xbmcgui.Dialog().textviewer(f'{title.upper()} — ACCOUNT INFO', '\n\n'.join(lines))


# =====================================================================
# PREMIUMIZE CLOUD HANDLERS (kept for direct & legacy route compatibility)
# =====================================================================

def pm_files(handle, params):
    folder_id = params.get('folder_id')
    icon_img = get_icon('premiumize')
    try:
        resp = get_orac_client().premiumize_cloud({'folder_id': folder_id} if folder_id else None) or {}
    except OracClientError as exc:
        notification(str(exc))
        end_directory(handle, cache_to_disc=False)
        return

    items = resp.get('content') or resp.get('items') or []
    kodi_items = []
    for count, entry in enumerate(items, 1):
        name = entry.get('name', 'Unnamed')
        entry_id = entry.get('id', '')
        entry_type = entry.get('type', 'file')
        cm = [(
            '[B]Delete[/B]',
            RUN_PLUGIN % build_url({'mode': 'cloud.pm_delete', 'id': entry_id, 'type': entry_type, 'name': name}),
        )]
        if entry_type == 'folder':
            label = f'{count:02d} | [B]FOLDER[/B] | {name.upper()}'
            kodi_items.append(make_dir_item(
                {'mode': 'cloud.pm_files', 'folder_id': entry_id, 'name': name},
                label,
                icon='premiumize',
                is_folder=True,
                cm_items=cm,
            ))
        else:
            size_str = _format_size(entry.get('size'))
            parts = [f'{count:02d}', '[B]FILE[/B]']
            if size_str:
                parts.append(size_str)
            parts.append(name.upper())
            label = ' | '.join(parts)
            stream_link = entry.get('link') or entry.get('stream_link') or ''
            li = make_listitem(label)
            li.setArt({'icon': icon_img, 'thumb': icon_img, 'poster': icon_img, 'fanart': FANART_PATH})
            li.setProperty('IsPlayable', 'true')
            li.addContextMenuItems(cm)
            url = build_url({'mode': 'cloud.pm_play', 'id': entry_id, 'link': stream_link, 'name': name})
            kodi_items.append((url, li, False))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, params.get('name', 'Premiumize Cloud'))
    end_directory(handle, cache_to_disc=False)


def pm_play(handle, params):
    link = params.get('link')
    item_id = params.get('id')
    name = params.get('name', 'Premiumize Stream')
    if not link and item_id:
        try:
            details = get_orac_client().premiumize_item_details({'id': item_id}) or {}
            link = details.get('link') or details.get('stream_link') or ''
        except OracClientError as exc:
            _fail_play(handle, str(exc))
            return
    if not link:
        _fail_play(handle, 'No playable link found')
        return
    _play_stream(handle, link, name)


def pm_delete(handle, params):
    item_id = params.get('id')
    item_type = params.get('type', 'file')
    name = params.get('name', 'item')
    if not item_id or not dialog_confirm('Delete', f'Delete [B]{name}[/B] from Premiumize?'):
        return
    try:
        file_type = 'folder' if item_type == 'folder' else 'item'
        get_orac_client().premiumize_delete({'id': item_id, 'file_type': file_type})
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
    for count, tr in enumerate(transfers, 1):
        name = tr.get('name', 'Transfer')
        status = tr.get('status', '')
        progress = tr.get('progress', '')
        label = f'{count:02d} | [{status.upper()} {progress}] | {name.upper()}'
        kodi_items.append(make_dir_item({'mode': 'noop'}, label, icon='premiumize', is_folder=False))

    add_items(handle, kodi_items)
    set_content(handle, 'files')
    set_category(handle, 'Premiumize History')
    end_directory(handle, cache_to_disc=False)


def pm_account(handle, params):
    service_account_info(handle, {'service': 'premiumize', 'name': 'Premiumize.me'})
