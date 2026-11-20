# -*- coding: utf-8 -*-
import json
import os
import re
from core.kodi import (
    ADDON_PATH,
    EMPTY_POSTER,
    FANART_PATH,
    dialog_input,
    dialog_multiselect,
    dialog_ok,
    get_icon,
)
from core.settings import DEFAULT_QUALITY_COLORS, source_highlight_settings
from windows.base import BaseDialog

FLAG_MEDIA_DIR = os.path.join(
    ADDON_PATH, 'resources', 'skins', 'Default', 'media', 'liberator_flags', 'media'
)
_FLAG_CACHE = {}

QUALITY_ICONS = {
    '4k': 'flag_4k',
    '1080p': 'flag_1080p',
    '720p': 'flag_720p',
    'sd': 'flag_sd',
}

PROVIDER_DEFS = (
    ('realdebrid', 'REAL-DEBRID', 'realdebrid', ('real', 'rd')),
    ('premiumize', 'PREMIUMIZE', 'premiumize', ('premiumize', 'pm')),
    ('torbox', 'TORBOX', 'torbox', ('torbox', 'tb')),
    ('alldebrid', 'ALLDEBRID', 'alldebrid', ('alldebrid', 'ad')),
    ('offcloud', 'OFFCLOUD', 'offcloud', ('offcloud', 'oc')),
    ('easydebrid', 'EASYDEBRID', 'easydebrid', ('easydebrid', 'ed')),
    ('easynews', 'EASYNEWS', 'easynews', ('easynews', 'en')),
)

QUALITY_ORDER = ('4K', '1080P', '720P', 'SD')
PROVIDER_ORDER = (
    'ORAC LOCAL', 'REAL-DEBRID', 'PREMIUMIZE', 'TORBOX',
    'ALLDEBRID', 'OFFCLOUD', 'EASYDEBRID', 'EASYNEWS',
)
PROVIDER_LABEL_TO_KEY = {
    'ORAC LOCAL': 'local',
    **{label: key for key, label, _, _ in PROVIDER_DEFS},
}

INFO_FILTER_DEFS = (
    ('res_4k', '4K (2160p)'),
    ('res_1080p', '1080p Full HD'),
    ('res_720p', '720p HD'),
    ('res_sd', 'SD'),
    ('dv', 'Dolby Vision'),
    ('hdr10+', 'HDR10+'),
    ('hdr', 'HDR'),
    ('remux', 'REMUX'),
    ('bluray', 'Blu-Ray'),
    ('webdl', 'WEB-DL / WEBRip'),
    ('imax', 'IMAX'),
    ('3d', '3D'),
    ('av1', 'AV1'),
    ('hevc', 'HEVC (H.265 / x265)'),
    ('h264', 'H.264 (AVC / x264)'),
    ('vp9', 'VP9'),
    ('atmos', 'Dolby Atmos'),
    ('truehd', 'Dolby TrueHD'),
    ('dtsx', 'DTS:X'),
    ('dtshd', 'DTS-HD / MA'),
    ('dts', 'DTS'),
    ('ddplus', 'Dolby Digital Plus (DD+)'),
    ('dd', 'Dolby Digital (AC3)'),
    ('flac', 'FLAC'),
    ('opus', 'Opus'),
    ('aac', 'AAC'),
    ('7.1', '7.1 Audio'),
    ('5.1', '5.1 Audio'),
    ('2.0', '2.0 Audio'),
    ('10bit', '10-Bit'),
    ('hybrid', 'Hybrid'),
    ('multi', 'Multi-Language / Dual Audio'),
    ('pack', 'Season / Full Pack'),
)

_RE_DV = re.compile(r'(?<![a-z0-9])(dolby[\s._-]?vision|dovi|dv)(?![a-z0-9])')
_RE_HDR10P = re.compile(r'(?<![a-z0-9])hdr[\s._-]?10(?:\+|plus)(?![a-z0-9])')
_RE_HDR = re.compile(r'(?<![a-z0-9])hdr(?!ip)(?:10)?(?![a-z0-9])')

_RE_REMUX = re.compile(r'(?<![a-z0-9])(remux|bdremux)(?![a-z0-9])')
_RE_BLURAY = re.compile(r'(?<![a-z0-9])(blu[\s._-]?ray|bdrip|bd[\s._-]?rip|brrip)(?![a-z0-9])')
_RE_WEBDL = re.compile(r'(?<![a-z0-9])(web[\s._-]?dl|webrip|web[\s._-]?rip|web)(?![a-z0-9])')
_RE_IMAX = re.compile(r'(?<![a-z0-9])imax(?![a-z0-9])')
_RE_3D = re.compile(r'(?<![a-z0-9])(3d|hsbs|sbs|htab)(?![a-z0-9])')

_RE_AV1 = re.compile(r'(?<![a-z0-9])av1(?![a-z0-9])')
_RE_HEVC = re.compile(r'(?<![a-z0-9])(hevc|[xh][\s._-]?265)(?![a-z0-9])')
_RE_H264 = re.compile(r'(?<![a-z0-9])([xh][\s._-]?264|avc)(?![a-z0-9])')
_RE_VP9 = re.compile(r'(?<![a-z0-9])vp9(?![a-z0-9])')

_CH_SFX = r'(?:[\s._-]?(?:2\.0|5\.1|7\.1|2ch|6ch|8ch))?'
_RE_ATMOS = re.compile(r'(?<![a-z0-9])atmos(?![a-z0-9])')
_RE_TRUEHD = re.compile(rf'(?<![a-z0-9])true[\s._-]?hd{_CH_SFX}(?![a-z0-9])')
_RE_DTSX = re.compile(rf'(?<![a-z0-9])dts[\s._:-]?x{_CH_SFX}(?![a-z0-9])')
_RE_DTSHD = re.compile(rf'(?<![a-z0-9])(dts[\s._-]?hd|dtshd|hd[\s._-]?ma|hdma){_CH_SFX}(?![a-z0-9])')
_RE_DTS = re.compile(rf'(?<![a-z0-9])dts{_CH_SFX}(?![a-z0-9])')
_RE_DDPLUS = re.compile(
    rf'(?<![a-z0-9])(ddp(?:[\s._-]?(?:2\.0|5\.1|7\.1|[257]))?|dd\+(?:[\s._-]?(?:2\.0|5\.1|7\.1))?|dd[\s._-]?plus|e[\s._-]?ac[\s._-]?3|ec3|dolby[\s._-]?digital[\s._-]?plus){_CH_SFX}(?![a-z0-9])'
)
_RE_DD = re.compile(
    rf'(?<![a-z0-9])(ac[\s._-]?3|dd[\s._-]?(?:2\.0|5\.1|7\.1)|dd(?![a-z])|dolby[\s._-]?digital(?![\s._-]?plus)){_CH_SFX}(?![a-z0-9])'
)
_RE_FLAC = re.compile(rf'(?<![a-z0-9])flac{_CH_SFX}(?![a-z0-9])')
_RE_OPUS = re.compile(rf'(?<![a-z0-9])opus{_CH_SFX}(?![a-z0-9])')
_RE_AAC = re.compile(rf'(?<![a-z0-9])aac{_CH_SFX}(?![a-z0-9])')

_RE_CH71 = re.compile(r'(?<![0-9])(7\.1|8ch|ch8)(?![0-9])')
_RE_CH51 = re.compile(r'(?<![0-9])(5\.1|6ch|ch6)(?![0-9])')
_RE_CH20 = re.compile(r'(?<![0-9v])(2\.0|2ch|ch2)(?![0-9])')

_RE_10BIT = re.compile(r'(?<![a-z0-9])(10[\s._-]?bit|hi10p)(?![a-z0-9])')
_RE_HYBRID = re.compile(r'(?<![a-z0-9])hybrid(?![a-z0-9])')
_RE_MULTI = re.compile(r'(?<![a-z0-9])(multi|dual[\s._-]?audio)(?![a-z0-9])')
_RE_PACK = re.compile(r'(?<![a-z0-9])(season[\s._-]?pack|complete[\s._-]?series|pack)(?![a-z0-9])')


def _get_flag_icon(name):
    if not name:
        return ''
    cached = _FLAG_CACHE.get(name)
    if cached is not None:
        return cached
    path = os.path.join(FLAG_MEDIA_DIR, f'{name}.png')
    resolved = path if os.path.exists(path) else ''
    _FLAG_CACHE[name] = resolved
    return resolved


def _normalize_quality(raw_quality):
    q = (raw_quality or 'sd').strip().lower()
    if '4k' in q or '2160' in q or 'uhd' in q:
        return '4k'
    if '1080' in q or 'fhd' in q:
        return '1080p'
    if '720' in q:
        return '720p'
    return 'sd'


def _normalize_provider(item):
    raw = (item.get('debrid') or item.get('cache_provider') or item.get('provider') or 'orac').strip()
    low = raw.lower()
    if bool(item.get('is_local')) or low in ('local', 'orac_local', 'folders', 'orac local'):
        return ('local', 'ORAC LOCAL', 'folder')
    for key, label, icon_name, tokens in PROVIDER_DEFS:
        for tok in tokens:
            if len(tok) > 2 and tok in low:
                return (key, label, icon_name)
            if re.search(rf'(?<![a-z0-9]){re.escape(tok)}(?![a-z0-9])', low):
                return (key, label, icon_name)
    fallback_label = raw.upper() if raw else 'ORAC'
    return ('orac', fallback_label, 'orac')


def _extract_media_badges(item, quality_key, quality_colors):
    haystack = ' '.join(
        str(item.get(k) or '')
        for k in ('name', 'display_name', 'extraInfo', 'video_codec', 'audio_codec')
    ).lower()

    q_color = (quality_colors or DEFAULT_QUALITY_COLORS).get(
        quality_key, DEFAULT_QUALITY_COLORS.get(quality_key, 'FF38BDF8')
    )
    badges = [(f'res_{quality_key}', q_color)]

    # Dynamic range
    has_dv = bool(_RE_DV.search(haystack))
    has_hdr10p = bool(_RE_HDR10P.search(haystack))
    has_hdr = has_hdr10p or bool(_RE_HDR.search(haystack))
    if has_dv and has_hdr:
        badges.append(('hdr_dv_hdr', 'FFC084FC'))
    elif has_dv:
        badges.append(('hdr_dv', 'FFC084FC'))
    elif has_hdr10p:
        badges.append(('hdr_hdr10plus', 'FFFBBF24'))
    elif has_hdr:
        badges.append(('hdr_hdr', 'FFFBBF24'))

    # Mastering / source
    secondary_source = None
    if _RE_REMUX.search(haystack):
        badges.append(('src_remux', 'FFFB7185'))
    elif _RE_BLURAY.search(haystack):
        badges.append(('src_bluray', 'FF93C5FD'))
    elif _RE_WEBDL.search(haystack):
        badges.append(('src_webdl', 'FF94A3B8'))

    if _RE_IMAX.search(haystack):
        secondary_source = ('src_imax', 'FF60A5FA')
    elif _RE_3D.search(haystack):
        secondary_source = ('src_3d', 'FF34D399')

    # Video codec
    if _RE_AV1.search(haystack):
        badges.append(('vcodec_av1', 'FF2DD4BF'))
    elif _RE_HEVC.search(haystack):
        badges.append(('vcodec_hevc', 'FFCBD5E1'))
    elif _RE_H264.search(haystack):
        badges.append(('vcodec_h264', 'FF94A3B8'))
    elif _RE_VP9.search(haystack):
        badges.append(('vcodec_vp9', 'FF94A3B8'))

    # Audio codec + Atmos
    has_atmos = bool(_RE_ATMOS.search(haystack))
    if _RE_TRUEHD.search(haystack):
        badges.append(('acodec_truehd', 'FF34D399'))
    elif _RE_DTSX.search(haystack):
        badges.append(('acodec_dtsx', 'FF34D399'))
    elif _RE_DTSHD.search(haystack):
        badges.append(('acodec_dtshd', 'FF34D399'))
    elif _RE_DTS.search(haystack):
        badges.append(('acodec_dts', 'FF7DD3FC'))
    elif _RE_DDPLUS.search(haystack):
        badges.append(('acodec_ddplus', 'FF7DD3FC'))
    elif _RE_DD.search(haystack):
        badges.append(('acodec_dd', 'FF94A3B8'))
    elif _RE_FLAC.search(haystack):
        badges.append(('acodec_flac', 'FF34D399'))
    elif _RE_OPUS.search(haystack):
        badges.append(('acodec_opus', 'FF94A3B8'))
    elif _RE_AAC.search(haystack):
        badges.append(('acodec_aac', 'FF94A3B8'))

    if has_atmos:
        badges.append(('acodec_atmos', 'FF22D3EE'))

    # Audio channels
    if _RE_CH71.search(haystack):
        badges.append(('ch_7_1', 'FF34D399'))
    elif _RE_CH51.search(haystack):
        badges.append(('ch_5_1', 'FFCBD5E1'))
    elif _RE_CH20.search(haystack):
        badges.append(('ch_2_0', 'FF94A3B8'))

    if secondary_source and len(badges) < 7:
        badges.append(secondary_source)

    # Extra concise tags for metadata strip
    extra_tags = []
    if _RE_10BIT.search(haystack):
        extra_tags.append('10BIT')
    if _RE_HYBRID.search(haystack):
        extra_tags.append('HYBRID')
    if _RE_MULTI.search(haystack):
        extra_tags.append('MULTI')
    if _RE_PACK.search(haystack):
        extra_tags.append('PACK')

    # Deduplicate preserving order, max 7
    seen = set()
    unique_badges = []
    for icon_key, color_hex in badges:
        if icon_key not in seen:
            seen.add(icon_key)
            unique_badges.append((icon_key, color_hex))
        if len(unique_badges) >= 7:
            break

    return unique_badges, extra_tags


def _extract_filter_tags(badges, extra_tags, quality_key):
    tags = {f'res_{quality_key}'}
    for icon_key, _ in badges:
        if icon_key.startswith('res_'):
            tags.add(icon_key)
        elif icon_key == 'hdr_dv_hdr':
            tags.update(('dv', 'hdr'))
        elif icon_key == 'hdr_dv':
            tags.add('dv')
        elif icon_key == 'hdr_hdr10plus':
            tags.update(('hdr10+', 'hdr'))
        elif icon_key == 'hdr_hdr':
            tags.add('hdr')
        elif icon_key.startswith(('src_', 'vcodec_', 'acodec_')):
            tags.add(icon_key.split('_', 1)[1])
        elif icon_key == 'ch_7_1':
            tags.add('7.1')
        elif icon_key == 'ch_5_1':
            tags.add('5.1')
        elif icon_key == 'ch_2_0':
            tags.add('2.0')
    for extra_tag in extra_tags:
        tags.add(extra_tag.lower())
    return sorted(tags)


class SourcesResults(BaseDialog):
    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename)
        self.window_format = kwargs.get('window_format', 'widelist')
        self.window_id = 2002 if self.window_format == 'widelist' else 2000
        self.filter_window_id = 2100
        self.results = kwargs.get('results', [])
        self.meta = kwargs.get('meta', {})
        self.scrape_duration = kwargs.get('scrape_duration', 0.0)
        self.selected = (None, None)
        self.item_list = []
        self.filter_list = []
        self.filter_applied = False
        self.active_filter_label = ''
        self.quality_summary = ''
        self._hl_cfg = source_highlight_settings()
        self._build_items()
        self._build_filter_items()
        self._set_properties()

    def onInit(self):
        poster = self.meta.get('poster') or EMPTY_POSTER
        try:
            self.setProperty('poster', poster)
        except Exception:
            pass
        self.add_items(self.window_id, self.item_list)
        self.add_items(self.filter_window_id, self.filter_list)
        self.setFocusId(self.window_id)

    def run(self):
        self.doModal()
        self.clearProperties()
        return self.selected

    @staticmethod
    def _compute_quality_summary(items):
        counts = {'4k': 0, '1080p': 0, '720p': 0, 'sd': 0}
        for li in items:
            q = li.getProperty('quality').lower()
            if q in counts:
                counts[q] += 1
        parts = [f'{k.upper()}: {counts[k]}' for k in ('4k', '1080p', '720p', 'sd') if counts[k] > 0]
        return '   \u2022   '.join(parts)

    def _build_items(self):
        hl_cfg = self._hl_cfg

        for count, item in enumerate(self.results, 1):
            li = self.make_listitem()
            quality_key = _normalize_quality(item.get('quality'))
            quality_icon = get_icon(QUALITY_ICONS.get(quality_key, 'flag_sd'))

            provider_key, provider_label, provider_icon_name = _normalize_provider(item)
            provider_icon = get_icon(provider_icon_name)

            name = (item.get('display_name') or item.get('name') or 'Unknown').upper()
            extra = (item.get('extraInfo') or 'N/A').rstrip('| ')

            is_local = provider_key == 'local'
            is_uncached = 'Uncached' in (item.get('cache_provider') or '')
            is_direct = bool(item.get('direct')) or provider_key == 'easynews'

            if is_uncached:
                cache_flag = 'UNCACHED'
                highlight = 'FF7C8594'
            else:
                if is_local:
                    cache_flag = 'LOCAL'
                elif is_direct:
                    cache_flag = 'DIRECT'
                else:
                    cache_flag = 'CACHED'

                if hl_cfg['mode'] == 'quality':
                    highlight = hl_cfg['qualities'].get(quality_key, 'FF38BDF8')
                else:
                    highlight = hl_cfg['providers'].get(provider_key, 'FF38BDF8')

            size_label = item.get('size_label')
            if not size_label:
                try:
                    size_val = float(item.get('size') or 0)
                    size_label = f'{size_val:.2f} GB' if size_val > 0 else 'N/A'
                except (ValueError, TypeError):
                    size_label = 'N/A'

            badges, extra_tags = _extract_media_badges(item, quality_key, hl_cfg['qualities'])
            filter_tags = _extract_filter_tags(badges, extra_tags, quality_key)

            site_raw = (item.get('provider') or '').strip()
            if is_local:
                site_label = 'LOCAL FILE'
            elif site_raw and site_raw.lower() not in ('orac', 'orac_local'):
                site_label = site_raw.upper()
            elif item.get('scrape_provider') == 'external' and is_direct:
                site_label = 'USENET'
            else:
                site_label = 'ORAC'

            meta_parts = [site_label] if site_label else []
            meta_parts.extend(extra_tags)
            meta_line = '  \u2022  '.join(meta_parts)

            props = {
                'name': name,
                'source_site': site_label,
                'provider': provider_label,
                'provider_icon': provider_icon,
                'quality': quality_key.upper(),
                'quality_icon': quality_icon,
                'count': f'{count:02d}.',
                'size_label': size_label,
                'extraInfo': extra,
                'meta_line': meta_line,
                'filter_tags': ' '.join(filter_tags),
                'search_blob': f'{name} {extra} {meta_line} {provider_label} {quality_key}'.upper(),
                'source_type': cache_flag,
                'highlight': highlight,
                'highlight_dim': f'24{highlight[2:]}' if len(highlight) == 8 else highlight,
                'hash': item.get('hash', 'N/A'),
                'source': json.dumps(item),
            }

            for idx in range(7):
                slot = idx + 1
                if idx < len(badges):
                    icon_key, color_hex = badges[idx]
                    props[f'badge_{slot}_icon'] = _get_flag_icon(icon_key)
                    props[f'badge_{slot}_color'] = color_hex
                else:
                    props[f'badge_{slot}_icon'] = ''
                    props[f'badge_{slot}_color'] = ''

            li.setProperties(props)
            self.item_list.append(li)

        self.quality_summary = self._compute_quality_summary(self.item_list)

    def _build_filter_items(self):
        rows = []
        if self.filter_applied:
            rows.append(('Clear Filter (Show All)', str(len(self.item_list)), 'clear', 'clear', 'FFF87171'))

        quality_counts = {}
        provider_counts = {}
        has_uncached = False
        cached_count = 0

        for li in self.item_list:
            q = li.getProperty('quality')
            if q:
                quality_counts[q] = quality_counts.get(q, 0) + 1
            p = li.getProperty('provider')
            if p:
                provider_counts[p] = provider_counts.get(p, 0) + 1
            if li.getProperty('source_type') == 'UNCACHED':
                has_uncached = True
            else:
                cached_count += 1

        sorted_qualities = sorted(
            quality_counts,
            key=lambda q: (QUALITY_ORDER.index(q) if q in QUALITY_ORDER else 999, q),
        )
        for q in sorted_qualities:
            color = self._hl_cfg['qualities'].get(q.lower(), 'FF38BDF8')
            rows.append((f'Show [B]{q}[/B] Only', str(quality_counts[q]), 'quality', q, color))

        sorted_providers = sorted(
            provider_counts,
            key=lambda p: (PROVIDER_ORDER.index(p) if p in PROVIDER_ORDER else 999, p),
        )
        for p in sorted_providers:
            pkey = PROVIDER_LABEL_TO_KEY.get(p, '')
            color = self._hl_cfg['providers'].get(pkey, 'FF38BDF8')
            rows.append((f'Show [B]{p}[/B] Only', str(provider_counts[p]), 'provider', p, color))

        if has_uncached and cached_count > 0:
            rows.append(('Show [B]Cached[/B] Only', str(cached_count), 'cached', 'cached', 'FF4ADE80'))

        rows.append(('Filter by [B]Video / Audio Info[/B]...', '', 'special', 'info', 'FF22D3EE'))
        rows.append(('Filter by [B]Title Keyword[/B]...', '', 'special', 'title', 'FFFACC15'))

        filter_items = []
        for label, count_label, ftype, fval, fcolor in rows:
            li = self.make_listitem()
            li.setProperties({
                'label': label,
                'count_label': count_label,
                'filter_type': ftype,
                'filter_value': fval,
                'filter_color': fcolor,
            })
            filter_items.append(li)
        self.filter_list = filter_items

    def _refresh_filter_list(self):
        self._build_filter_items()
        self.reset_control(self.filter_window_id)
        self.add_items(self.filter_window_id, self.filter_list)

    def _filter_by_quality(self, value):
        return [li for li in self.item_list if li.getProperty('quality') == value]

    def _filter_by_provider(self, value):
        return [li for li in self.item_list if li.getProperty('provider') == value]

    def _filter_by_info_tags(self, selected_tags):
        return [li for li in self.item_list if all(t in li.getProperty('filter_tags').split() for t in selected_tags)]

    def _filter_by_keywords(self, raw_keywords):
        terms = [t.strip().upper() for t in (raw_keywords or '').split(',') if t.strip()]
        if not terms:
            return []
        return [li for li in self.item_list if all(term in li.getProperty('search_blob') for term in terms)]

    def _apply_filter(self, filtered_list, description):
        self.filter_applied = True
        self.active_filter_label = description
        self.reset_control(self.window_id)
        self.add_items(self.window_id, filtered_list)
        self._refresh_filter_list()
        self.setProperty('total_results', str(len(filtered_list)))
        self.setProperty('quality_summary', self._compute_quality_summary(filtered_list))
        self.setProperty('filter_applied', 'true')
        self.setProperty('filter_info', f'  \u2022  [B]{description}[/B] (BACK)')
        self.set_focus_id(self.window_id)

    def _clear_filter(self):
        self.filter_applied = False
        self.active_filter_label = ''
        self.reset_control(self.window_id)
        self.add_items(self.window_id, self.item_list)
        self._refresh_filter_list()
        self.setProperty('total_results', str(len(self.item_list)))
        self.setProperty('quality_summary', self._compute_quality_summary(self.item_list))
        self.setProperty('filter_applied', 'false')
        self.setProperty('filter_info', '')
        self.set_focus_id(self.window_id)

    def _handle_filter_action(self, action):
        if action == self.right_action or action in self.closing_actions:
            try:
                self.select_item(self.filter_window_id, 0)
            except Exception:
                pass
            self.set_focus_id(self.window_id)
            return

        if action not in self.selection_actions:
            return

        chosen = self.get_listitem(self.filter_window_id)
        if not chosen:
            return

        ftype = chosen.getProperty('filter_type')
        fval = chosen.getProperty('filter_value')

        if ftype == 'clear':
            self._clear_filter()
            return

        filtered = []
        desc = ''
        if ftype == 'quality':
            filtered = self._filter_by_quality(fval)
            desc = f'{fval} ONLY'
        elif ftype == 'provider':
            filtered = self._filter_by_provider(fval)
            desc = f'{fval} ONLY'
        elif ftype == 'cached':
            filtered = [li for li in self.item_list if li.getProperty('source_type') != 'UNCACHED']
            desc = 'CACHED ONLY'
        elif ftype == 'special' and fval == 'title':
            keywords = dialog_input('Filter by Title Keywords (comma separated)')
            if not keywords or not keywords.strip():
                return
            filtered = self._filter_by_keywords(keywords)
            terms = [t.strip().upper() for t in keywords.split(',') if t.strip()]
            desc = 'KEYWORD: ' + ' + '.join(terms)
        elif ftype == 'special' and fval == 'info':
            tag_counts = {}
            for li in self.item_list:
                for t in li.getProperty('filter_tags').split():
                    tag_counts[t] = tag_counts.get(t, 0) + 1
            available = [(k, lbl, tag_counts[k]) for k, lbl in INFO_FILTER_DEFS if tag_counts.get(k, 0) > 0]
            if not available:
                dialog_ok('Liberator 2', 'No video/audio definitions detected to filter.')
                return
            options = [f'{lbl}  ({cnt})' for _, lbl, cnt in available]
            indices = dialog_multiselect('Filter by Video / Audio Info', options)
            if not indices:
                return
            selected_tags = [available[i][0] for i in indices]
            selected_labels = [available[i][1].split(' (', 1)[0].upper() for i in indices]
            filtered = self._filter_by_info_tags(selected_tags)
            desc = ' + '.join(selected_labels)

        if not filtered:
            dialog_ok('Liberator 2', 'No matching sources found.')
            return

        self._apply_filter(filtered, desc)

    def _set_properties(self):
        self.setProperty('window_format', self.window_format)
        self.setProperty('fanart', self.meta.get('fanart') or FANART_PATH)
        self.setProperty('clearlogo', self.meta.get('clearlogo') or '')
        self.setProperty('title', self.meta.get('title') or '')
        self.setProperty('total_results', str(len(self.item_list)))
        self.setProperty('filters_ignored', f'({self.scrape_duration:.2f}s)')
        self.setProperty('quality_summary', self.quality_summary)
        self.setProperty('filter_applied', 'false')
        self.setProperty('filter_info', '')

    def onAction(self, action):
        in_filter = self.get_visibility(f'Control.HasFocus({self.filter_window_id})')
        if not in_filter:
            try:
                in_filter = self.getFocusId() == self.filter_window_id
            except Exception:
                in_filter = False
        if in_filter:
            self._handle_filter_action(action)
            return

        if action in self.closing_actions:
            if self.filter_applied:
                self._clear_filter()
                return
            self.selected = (None, None)
            self.close()
        elif action in self.selection_actions:
            chosen = self.get_listitem(self.window_id)
            if chosen:
                self.selected = ('play', json.loads(chosen.getProperty('source')))
            self.close()


class SourcesPlayback(BaseDialog):
    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename)
        self.meta = kwargs.get('meta', {})
        self.setProperty('window_mode', 'scraper')
        self.setProperty('enable_busy_spinner', 'true')
        self.setProperty('title', self.meta.get('title', ''))
        self.setProperty('fanart', self.meta.get('fanart') or FANART_PATH)
        self.setProperty('clearlogo', self.meta.get('clearlogo', ''))
        self.setProperty('year', str(self.meta.get('year', '')))
        self.setProperty('poster', self.meta.get('poster') or EMPTY_POSTER)
        self.setProperty('genre', ', '.join(self.meta.get('genres', [])) if isinstance(self.meta.get('genres'), list) else '')
        self.setProperty('plot', self.meta.get('overview', ''))
        self.setProperty('results_4k', '0')
        self.setProperty('results_1080p', '0')
        self.setProperty('results_720p', '0')
        self.setProperty('results_sd', '0')
        self.setProperty('results_total', '0')
        self.setProperty('percent', '0')

    def set_text(self, text):
        self.setProperty('text', text)
        try:
            self.getControl(2001).setText(text)
        except Exception:
            pass
