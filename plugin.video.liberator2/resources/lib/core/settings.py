# -*- coding: utf-8 -*-
import xbmcaddon

ADDON_ID = 'plugin.video.liberator2'


def _addon():
    return xbmcaddon.Addon(ADDON_ID)


def get_setting(setting_id, default=''):
    value = _addon().getSetting(setting_id)
    return value if value != '' else default


def set_setting(setting_id, value):
    _addon().setSetting(setting_id, str(value))


def get_bool(setting_id, default=False):
    val = get_setting(setting_id)
    if val == '':
        return default
    return val.lower() == 'true'


def get_int(setting_id, default=0):
    try:
        return int(get_setting(setting_id, str(default)))
    except (ValueError, TypeError):
        return default


def orac_base_url():
    address = get_setting('orac_address', '').strip()
    if not address:
        return ''
    port = get_setting('orac_port', '5555').strip() or '5555'
    if not address.startswith(('http://', 'https://')):
        address = f'http://{address}'
    host_part = address.split('://', 1)[-1].split('/')[0]
    if ':' not in host_part:
        address = f'{address.rstrip("/")}:{port}'
    return address.rstrip('/')


def trakt_user():
    return get_setting('trakt.user', '')


def paginate(is_home=False):
    return get_bool('paginate.lists', True)


def page_limit(is_home=False):
    key = 'paginate.limit_widgets' if is_home else 'paginate.limit_addon'
    return get_int(key, 20)


def widget_hide_watched():
    return get_bool('widget_hide_watched', False)


def widget_hide_next_page():
    return get_bool('widget_hide_next_page', False)


def show_specials():
    return get_bool('show_specials', False)


def default_all_episodes():
    return get_int('default_all_episodes', 0)


def nextep_include_unaired():
    return get_bool('nextep.include_unaired', False)


def nextep_sort_key():
    return get_setting('nextep.sort_key', 'last_played')


def nextep_sort_descending():
    return get_bool('nextep.sort_descending', True)


EPISODE_TITLE_FORMATS = (
    (0, 'Show: 01x01 - Episode', 'Breaking Bad: 01x01 - Pilot'),
    (1, '01x01 - Episode', '01x01 - Pilot'),
    (2, 'Episode', 'Pilot'),
    (3, 'Show: S01E01 - Episode', 'Breaking Bad: S01E01 - Pilot'),
    (4, 'S01E01 - Episode', 'S01E01 - Pilot'),
    (5, 'Show: Episode S01E01', 'Breaking Bad: Pilot S01E01'),
)


def episode_title_format_label(fmt_id):
    try:
        idx = int(fmt_id)
    except (ValueError, TypeError):
        idx = 0
    for fid, label, _example in EPISODE_TITLE_FORMATS:
        if fid == idx:
            return label
    return EPISODE_TITLE_FORMATS[0][1]


def episode_display_format():
    return get_int('episode_display', 1)


def single_ep_display_format(is_external=False):
    if is_external:
        return get_int('single_ep_display_widget', 1)
    return get_int('single_ep_display', 0)


def format_episode_title(fmt_id, show_title, season_num, episode_num, ep_title):
    s = f'{int(season_num):02d}'
    e = f'{int(episode_num):02d}'
    show = (show_title or '').strip()
    ep = (ep_title or f'Episode {episode_num}').strip()
    try:
        fid = int(fmt_id)
    except (ValueError, TypeError):
        fid = 0

    if fid == 0:
        return f'{show}: {s}x{e} - {ep}' if show else f'{s}x{e} - {ep}'
    if fid == 1:
        return f'{s}x{e} - {ep}'
    if fid == 2:
        return ep
    if fid == 3:
        return f'{show}: S{s}E{e} - {ep}' if show else f'S{s}E{e} - {ep}'
    if fid == 4:
        return f'S{s}E{e} - {ep}'
    if fid == 5:
        return f'{show}: {ep} S{s}E{e}' if show else f'{ep} S{s}E{e}'
    return f'{show}: {s}x{e} - {ep}' if show else f'{s}x{e} - {ep}'


def media_open_action(media_type):
    if media_type == 'movie':
        return get_int('media_open_action.movie', 0)
    if media_type == 'tvshow':
        return get_int('media_open_action.tvshow', 0)
    return 0


def autoplay_enabled(media_type):
    if media_type == 'movie':
        return get_bool('autoplay_movies', False)
    return get_bool('autoplay_episodes', False)


def strict_dedupe():
    return get_bool('orac.strict_dedupe', False)


def use_local_files():
    return get_bool('orac.use_local_files', True)


def skip_intro():
    return get_bool('orac.skip_intro', False)


def use_viewtypes():
    return get_bool('use_viewtypes', False)


DEFAULT_PROVIDER_COLORS = {
    'realdebrid': 'FF4ADE80',
    'premiumize': 'FFFF6B35',
    'torbox': 'FFA855F7',
    'alldebrid': 'FFFACC15',
    'offcloud': 'FF38BDF8',
    'easydebrid': 'FFF472B6',
    'easynews': 'FF22D3EE',
    'local': 'FF2DD4BF',
}

DEFAULT_QUALITY_COLORS = {
    '4k': 'FFD946EF',
    '1080p': 'FF38BDF8',
    '720p': 'FF4ADE80',
    'sd': 'FFFB923C',
}


def source_highlight_settings():
    return {
        'mode': get_setting('sources.highlight_mode', 'provider'),
        'providers': {k: get_setting(f'color.provider.{k}', v) for k, v in DEFAULT_PROVIDER_COLORS.items()},
        'qualities': {k: get_setting(f'color.quality.{k}', v) for k, v in DEFAULT_QUALITY_COLORS.items()},
    }
