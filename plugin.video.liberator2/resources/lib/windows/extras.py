# -*- coding: utf-8 -*-
from datetime import datetime, timedelta
from threading import Thread
import xbmc
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    build_url,
    container_update,
    dialog_ok,
    get_icon,
    hide_busy_dialog,
    logger,
    notification,
    play_trailer,
    show_busy_dialog,
)
from core.settings import trakt_user
from orac.client import OracClientError, get_orac_client
from windows.base import BaseDialog

SEPARATOR = '[B]  •  [/B]'
CAST_ID = 2050
REVIEWS_ID = 2053
VIDEOS_ID = 2059
COLLECTION_ID = 2063
BUTTON_IDS = (10, 11, 12, 13, 14, 15, 16, 17, 50)
YOUTUBE_THUMB = 'https://img.youtube.com/vi/%s/0.jpg'


def _safe_int(val, default=0):
    try:
        return int(float(val)) if val is not None else default
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    try:
        return float(val) if val is not None else default
    except (ValueError, TypeError):
        return default


def _as_list(val):
    if isinstance(val, list):
        return [str(x) for x in val if x]
    if isinstance(val, str) and val.strip():
        return [s.strip() for s in val.split(',') if s.strip()]
    return []


class ShowTextMedia(BaseDialog):
    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename)
        self.text = kwargs.get('text') or ''
        self.position = kwargs.get('current_index')
        self.text_is_list = isinstance(self.text, list)
        self.len_text = len(self.text) if self.text_is_list else 0
        self.window_id = 2099
        self.setProperty('poster', kwargs.get('poster') or EMPTY_POSTER)

    def run(self):
        self.doModal()
        self.clearProperties()
        return self.position

    def onInit(self):
        self._update_text()
        self.set_focus_id(self.window_id)

    def onAction(self, action):
        if action in self.closing_actions:
            self.close()
        elif self.text_is_list and self.len_text > 1:
            if action == self.left_action:
                self._update_text('previous')
            elif action == self.right_action:
                self._update_text('next')

    def _update_text(self, direction=None):
        if self.text_is_list and self.len_text > 0:
            if self.position is None:
                self.position = 0
            if direction == 'previous':
                self.position = (self.position - 1) if self.position > 0 else (self.len_text - 1)
            elif direction == 'next':
                self.position = 0 if self.position >= (self.len_text - 1) else (self.position + 1)
            content = self.text[self.position]
            self.setProperty('previous_display', 'false' if self.position == 0 else 'true')
            self.setProperty('next_display', 'false' if self.position >= self.len_text - 1 else 'true')
        else:
            content = '\n\n'.join(self.text) if isinstance(self.text, list) else str(self.text)
            self.setProperty('previous_display', 'false')
            self.setProperty('next_display', 'false')
        self.set_text(2001, content)


class Extras(BaseDialog):
    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename)
        self.meta = kwargs.get('meta') or {}
        self.media_type = kwargs.get('media_type', 'movie')
        self.tmdb_id = str(self.meta.get('tmdb_id') or '')
        self.reviews = kwargs.get('reviews') or []
        self.control_id = None
        self.button_actions = {}
        self.deferred_action = None
        self.is_watched = self._compute_watched()
        self._set_properties()

    def _compute_watched(self):
        pct = _safe_float(self.meta.get('percent_watched') or self.meta.get('progress'))
        return bool(self.meta.get('watched')) or self.meta.get('watched_status') == 2 or pct >= 90

    def _duration_minutes(self):
        dur = _safe_int(self.meta.get('runtime') or self.meta.get('duration'))
        return dur // 60 if dur >= 600 else dur

    def _format_duration(self):
        mins = self._duration_minutes()
        if mins <= 0:
            return ''
        hours, rem = divmod(mins, 60)
        if hours and rem:
            return f'{hours}h {rem:02d}m'
        if hours:
            return f'{hours}h'
        return f'{rem}m'

    def _set_properties(self):
        title = self.meta.get('title') or self.meta.get('name') or ''
        year = str(self.meta.get('year') or '')
        plot = self.meta.get('tvshow_plot') or self.meta.get('overview') or self.meta.get('plot') or ''
        tagline = self.meta.get('tagline') or ''
        if tagline and plot:
            plot = f'[I]{tagline}[/I][CR][CR]{plot}'
        elif tagline:
            plot = f'[I]{tagline}[/I]'

        genres = _as_list(self.meta.get('genres') or self.meta.get('genre'))
        networks = _as_list(self.meta.get('studio') or self.meta.get('network'))

        self.setProperty('media_type', self.media_type)
        self.setProperty('title', title)
        self.setProperty('year', year)
        self.setProperty('plot', plot)
        self.setProperty('genre', ', '.join(genres))
        self.setProperty('network', ', '.join(networks))
        self.setProperty('plot_enabled', 'true')
        self.setProperty('enable_scrollbars', 'true')
        self.setProperty('display_extra_ratings', 'false')

        self._assign_buttons()

    def _assign_buttons(self):
        watch_label = 'Mark Unwatched' if self.is_watched else 'Mark Watched'
        if self.media_type == 'movie':
            mapping = {
                10: ('Play', 'play_movie'),
                11: ('Select Source', 'select_source'),
                12: ('Trailer', 'play_trailer'),
                13: ('Orac Lists', 'orac_lists'),
                14: ('Add Tag', 'add_tag'),
                15: ('Remove Tag', 'remove_tag'),
                16: (watch_label, 'toggle_watched'),
                17: ('Extra Info', 'extra_info'),
            }
        else:
            mapping = {
                10: ('Browse Seasons', 'browse_seasons'),
                11: ('All Episodes', 'all_episodes'),
                12: ('Trailer', 'play_trailer'),
                13: ('Orac Lists', 'orac_lists'),
                14: ('Add Tag', 'add_tag'),
                15: ('Remove Tag', 'remove_tag'),
                16: (watch_label, 'toggle_watched'),
                17: ('Extra Info', 'extra_info'),
            }
        for cid, (label, action_name) in mapping.items():
            self.setProperty(f'button{cid}.label', label)
            self.button_actions[cid] = action_name
        self.button_actions[50] = 'show_plot'

    def onInit(self):
        self._set_artwork()
        self._set_infolines()
        for loader in (self._load_cast, self._load_reviews, self._load_videos, self._load_collection):
            Thread(target=loader, daemon=True).start()
        self.set_focus_id(10)

    def _set_artwork(self):
        poster = self.meta.get('poster_path') or self.meta.get('poster') or EMPTY_POSTER
        fanart = self.meta.get('fanart_path') or self.meta.get('fanart') or FANART_PATH
        clearlogo = self.meta.get('clearlogo_path') or self.meta.get('clearlogo') or ''
        self.set_image(200, poster)
        self.set_image(202, fanart)
        if clearlogo:
            self.set_image(201, clearlogo)
        else:
            self.setProperty('clearlogo', 'false')

    def _set_infolines(self):
        year = str(self.meta.get('year') or '')
        rating_val = _safe_float(self.meta.get('rating'))
        rating = f'{rating_val:.1f}' if rating_val > 0 else ''
        cert = self.meta.get('certification') or self.meta.get('mpaa') or ''
        lang = self.meta.get('language') or self.meta.get('spoken_language') or ''
        dur = self._format_duration()
        status = (self.meta.get('status') or '').replace(' Series', '')
        line1 = SEPARATOR.join([x for x in (year, rating, cert, lang, dur, status) if x])
        self.set_label(2001, line1)

        if self.media_type == 'movie':
            pct = int(_safe_float(self.meta.get('percent_watched') or self.meta.get('progress')))
            if self.is_watched and pct == 0:
                pct = 100
            mins = self._duration_minutes()
            finish = 'No Finish Time'
            if mins > 0:
                rem = mins if pct in (0, 100) else ((100 - pct) / 100.0) * mins
                finish_dt = datetime.now() + timedelta(minutes=rem)
                verb = 'Finish Rewatching' if pct == 100 else 'Finish Watching'
                finish = f'{verb}: {finish_dt.strftime("%H:%M")}'
            line2 = SEPARATOR.join((f'{pct}% Watched', finish))
        else:
            seasons_count = self.meta.get('total_seasons') or len(self.meta.get('seasons', []))
            eps_count = self.meta.get('total_aired_eps') or self.meta.get('total_episodes') or ''
            parts = []
            if seasons_count:
                parts.append(f'Seasons: {seasons_count}')
            if eps_count:
                parts.append(f'Episodes: {eps_count}')
            last_ep = self.meta.get('last_episode_to_air')
            if isinstance(last_ep, dict) and last_ep.get('season_number') is not None:
                parts.append(f"Last Aired: S{int(last_ep['season_number']):02d}E{int(last_ep.get('episode_number', 0)):02d}")
            next_ep = self.meta.get('next_episode_to_air')
            if isinstance(next_ep, dict) and next_ep.get('season_number') is not None:
                parts.append(f"Next Aired: S{int(next_ep['season_number']):02d}E{int(next_ep.get('episode_number', 0)):02d}")
            line2 = SEPARATOR.join(parts)
        self.set_label(3001, line2)

    def _load_cast(self):
        cast = self.meta.get('cast') or []
        if not cast:
            return
        fallback = get_icon('genre_family')
        items = []
        for person in cast:
            if not isinstance(person, dict):
                continue
            name = person.get('name') or ''
            if not name:
                continue
            role = person.get('role') or person.get('character') or ''
            thumb = person.get('thumbnail') or ''
            if not thumb and person.get('profile_path'):
                thumb = f"https://image.tmdb.org/t/p/w185{person['profile_path']}"
            li = self.make_listitem()
            li.setProperties({
                'name': name,
                'role': role,
                'thumbnail': thumb or fallback,
            })
            items.append(li)
        if items:
            self.setProperty('cast.number', f'x{len(items)}')
            self.add_items(CAST_ID, items)

    def _load_reviews(self):
        if not self.reviews:
            return
        items = []
        for rev in self.reviews:
            li = self.make_listitem()
            li.setProperties({'text': str(rev), 'content_list': 'reviews'})
            items.append(li)
        self.setProperty('imdb_reviews.number', f'x{len(items)}')
        self.add_items(REVIEWS_ID, items)

    def _load_videos(self):
        trailers = self.meta.get('all_trailers') or []
        if not trailers:
            return
        items = []
        for tr in trailers:
            if not isinstance(tr, dict) or not tr.get('key'):
                continue
            key = tr['key']
            li = self.make_listitem()
            li.setProperties({
                'name': tr.get('name') or 'Trailer',
                'thumbnail': YOUTUBE_THUMB % key,
                'key_id': key,
            })
            items.append(li)
        if items:
            self.setProperty('youtube_videos.number', f'x{len(items)}')
            self.add_items(VIDEOS_ID, items)

    def _load_collection(self):
        col_info = self.meta.get('belongs_to_collection')
        if not isinstance(col_info, dict) or not col_info.get('id'):
            return
        try:
            resp = get_orac_client().get_collections() or {}
        except OracClientError:
            return
        col_list = resp.get('collections', []) if isinstance(resp, dict) else []
        match = next((c for c in col_list if str(c.get('id')) == str(col_info['id'])), None)
        if not match:
            return
        items = []
        for movie in match.get('movies') or []:
            tmdb_id = str(movie.get('tmdb_id') or '')
            if not tmdb_id:
                continue
            rel = str(movie.get('release_date') or '')
            year = rel.split('-')[0] if rel else 'N/A'
            li = self.make_listitem()
            li.setProperties({
                'name': movie.get('title') or '',
                'release_date': year,
                'vote_average': f"{_safe_float(movie.get('rating')):.1f}",
                'thumbnail': movie.get('poster_path') or EMPTY_POSTER,
                'tmdb_id': tmdb_id,
            })
            items.append(li)
        if items:
            self.setProperty('collection.number', f'x{len(items)}')
            self.add_items(COLLECTION_ID, items)

    def run(self):
        self.doModal()
        self.clearProperties()
        return self.deferred_action

    def onClick(self, control_id):
        self.control_id = None
        action_name = self.button_actions.get(control_id)
        if action_name:
            getattr(self, f'_btn_{action_name}')()
        else:
            self.control_id = control_id

    def onAction(self, action):
        if action in self.closing_actions:
            self.close()
            return
        if action == self.info_action and self.getFocusId() == COLLECTION_ID:
            li = self.get_listitem(COLLECTION_ID)
            if li and li.getProperty('tmdb_id'):
                self._show_collection_info(li.getProperty('tmdb_id'))
            return
        if action in self.selection_actions and self.control_id:
            self._handle_list_selection(self.control_id)

    def _show_collection_info(self, tmdb_id):
        show_busy_dialog()
        try:
            data = get_orac_client().get_movie_details({'tmdb_id': tmdb_id, 'user': trakt_user()}) or {}
        except OracClientError:
            data = {}
        hide_busy_dialog()
        if not data:
            return
        year = str(data.get('year') or '')
        rating = f"{_safe_float(data.get('rating')):.1f}" if _safe_float(data.get('rating')) > 0 else ''
        cert = data.get('certification') or ''
        header = SEPARATOR.join([x for x in (year, rating, cert) if x])
        overview = data.get('overview') or ''
        text = f'{header}[CR][CR]{overview}' if header else overview
        ShowTextMedia('textviewer_media.xml', text=text, poster=data.get('poster_path') or EMPTY_POSTER).run()

    def _handle_list_selection(self, cid):
        li = self.get_listitem(cid)
        if not li:
            return
        if cid == CAST_ID:
            person_name = li.getProperty('name')
            if person_name:
                self.deferred_action = ('person', {'key_id': person_name, 'reference_tmdb_id': self.tmdb_id})
                self.close()
        elif cid == REVIEWS_ID and self.reviews:
            pos = self.get_position(REVIEWS_ID)
            end_idx = ShowTextMedia(
                'textviewer_media.xml',
                text=self.reviews,
                poster=self.meta.get('poster_path') or EMPTY_POSTER,
                current_index=pos,
            ).run()
            if end_idx is not None:
                self.select_item(REVIEWS_ID, end_idx)
        elif cid == VIDEOS_ID:
            key = li.getProperty('key_id')
            if key:
                play_trailer(key)
        elif cid == COLLECTION_ID:
            col_tmdb = li.getProperty('tmdb_id')
            if col_tmdb:
                self.deferred_action = ('extras', {'media_type': 'movie', 'tmdb_id': col_tmdb})
                self.close()

    # --- Button Handlers ---
    def _btn_play_movie(self):
        self.deferred_action = ('play', {'media_type': 'movie', 'tmdb_id': self.tmdb_id, 'title': self.meta.get('title', '')})
        self.close()

    def _btn_select_source(self):
        self.deferred_action = ('play', {
            'media_type': 'movie', 'tmdb_id': self.tmdb_id, 'title': self.meta.get('title', ''), 'force_select': 'true'
        })
        self.close()

    def _btn_browse_seasons(self):
        self.deferred_action = ('container', {'mode': 'tv.seasons', 'tmdb_id': self.tmdb_id, 'title': self.meta.get('title', '')})
        self.close()

    def _btn_all_episodes(self):
        self.deferred_action = ('container', {'mode': 'tv.episodes', 'tmdb_id': self.tmdb_id, 'season': 'all', 'title': self.meta.get('title', '')})
        self.close()

    def _btn_play_trailer(self):
        trailer_url = self.meta.get('trailer') or ''
        if not trailer_url:
            trailers = self.meta.get('all_trailers') or []
            if trailers and isinstance(trailers[0], dict):
                trailer_url = trailers[0].get('key', '')
        play_trailer(trailer_url)

    def _btn_orac_lists(self):
        from views.lists import manager_choice
        manager_choice(-1, {'tmdb_id': self.tmdb_id, 'media_type': self.media_type})

    def _btn_add_tag(self):
        from views.tags import add_tag
        add_tag(-1, {'tmdb_id': self.tmdb_id, 'media_type': self.media_type})

    def _btn_remove_tag(self):
        from views.tags import remove_tag
        remove_tag(-1, {'tmdb_id': self.tmdb_id, 'media_type': self.media_type})

    def _btn_toggle_watched(self):
        action = 'mark_as_unwatched' if self.is_watched else 'mark_as_watched'
        pct = 0 if self.is_watched else 100
        try:
            get_orac_client().mark_watched({
                'type': 'movie' if self.media_type == 'movie' else 'tvshow',
                'tmdb_id': int(self.tmdb_id),
                'percent_watched': pct,
            })
            self.is_watched = not self.is_watched
            self.setProperty('button16.label', 'Mark Unwatched' if self.is_watched else 'Mark Watched')
            notification('Marked Unwatched' if action == 'mark_as_unwatched' else 'Marked Watched')
        except OracClientError as exc:
            notification(f'Failed to update watched status: {exc}')

    def _btn_extra_info(self):
        lines = []
        if self.meta.get('tagline'):
            lines.append(f"[B]Tagline:[/B] {self.meta['tagline']}")
        if self.meta.get('status'):
            lines.append(f"[B]Status:[/B] {self.meta['status']}")
        if self.meta.get('released') or self.meta.get('premiered'):
            lines.append(f"[B]Premiered:[/B] {self.meta.get('released') or self.meta.get('premiered')}")
        dur = self._format_duration()
        if dur:
            lines.append(f'[B]Runtime:[/B] {dur}')
        genres = _as_list(self.meta.get('genres') or self.meta.get('genre'))
        if genres:
            lines.append(f"[B]Genres:[/B] {', '.join(genres)}")
        studios = _as_list(self.meta.get('studio') or self.meta.get('network'))
        if studios:
            lines.append(f"[B]Studio/Network:[/B] {', '.join(studios)}")
        if self.meta.get('overview') or self.meta.get('plot'):
            lines.append(self.meta.get('overview') or self.meta.get('plot'))
        ShowTextMedia(
            'textviewer_media.xml',
            text='[CR][CR]'.join(lines) or 'No extra details available.',
            poster=self.meta.get('poster_path') or EMPTY_POSTER,
        ).run()

    def _btn_show_plot(self):
        plot = self.meta.get('tvshow_plot') or self.meta.get('overview') or self.meta.get('plot') or 'No plot available.'
        ShowTextMedia(
            'textviewer_media.xml',
            text=plot,
            poster=self.meta.get('poster_path') or EMPTY_POSTER,
        ).run()


def _execute_deferred(action):
    if not action:
        return
    kind, data = action
    if kind == 'play':
        from playback.sources import play
        play(-1, {**data, 'direct_play': 'true'})
    elif kind == 'container':
        container_update(build_url(data))
    elif kind == 'extras':
        open_extras(-1, data)
    elif kind == 'person':
        from windows.people import open_person
        open_person(-1, data)


def open_extras(handle, params):
    tmdb_id = params.get('tmdb_id')
    media_type = params.get('media_type', 'movie')
    if not tmdb_id:
        return
    content = 'movie' if media_type == 'movie' else 'tvshow'

    show_busy_dialog()
    try:
        client = get_orac_client()
        meta = (
            client.get_movie_details({'tmdb_id': tmdb_id, 'user': trakt_user()})
            if content == 'movie'
            else client.get_show_details({'tmdb_id': tmdb_id, 'user': trakt_user()})
        )
        reviews_resp = client.get_reviews({'tmdb_id': tmdb_id, 'media_type': content, 'max_reviews': '20'}) or {}
        reviews = reviews_resp.get('reviews', []) if reviews_resp.get('success') else []
    except OracClientError as exc:
        hide_busy_dialog()
        notification(f'Could not load extras: {exc}')
        return
    hide_busy_dialog()

    if not meta or not isinstance(meta, dict):
        notification('Could not load metadata')
        return

    deferred = Extras('extras.xml', meta=meta, media_type=content, reviews=reviews).run()
    _execute_deferred(deferred)
