# -*- coding: utf-8 -*-
from datetime import datetime
from threading import Thread
from core.kodi import (
    EMPTY_POSTER,
    FANART_PATH,
    dialog_input,
    dialog_select,
    get_icon,
    hide_busy_dialog,
    logger,
    notification,
    show_busy_dialog,
)
from orac.client import OracClientError, get_orac_client
from windows.base import BaseDialog
from windows.extras import ShowTextMedia, open_extras

TMDB_IMG = 'https://image.tmdb.org/t/p/%s%s'
GENDER_MAP = {1: 'Female', 2: 'Male'}
ROLES_EXCLUDE = {'himself', 'herself', 'self', 'narrator', 'voice', 'voice (voice)'}
TV_GENRES_EXCLUDE = {10763, 10764, 10767}
MOVIES_ID = 2050
TVSHOWS_ID = 2051
DIRECTOR_ID = 2053
SEPARATOR = '[B]  •  [/B]'


def _calculate_age(birthday, deathday=''):
    if not birthday:
        return ''
    try:
        born = datetime.strptime(birthday[:10], '%Y-%m-%d')
        ref = datetime.strptime(deathday[:10], '%Y-%m-%d') if deathday else datetime.today()
        age = ref.year - born.year - ((ref.month, ref.day) < (born.month, born.day))
        return f'{age}yo' if age >= 0 else ''
    except ValueError:
        return ''


def _sort_by_release(items, date_key):
    with_date = [i for i in items if i.get(date_key)]
    without_date = [i for i in items if not i.get(date_key)]
    with_date.sort(key=lambda x: x.get(date_key, ''), reverse=True)
    return with_date + without_date


class People(BaseDialog):
    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename)
        self.person = kwargs.get('person') or {}
        self.control_id = None
        self.deferred_action = None
        self.movie_data = []
        self.tvshow_data = []
        self.director_data = []
        self._prepare_credits()
        self._set_properties()

    def _prepare_credits(self):
        credits_data = self.person.get('combined_credits') or {}
        cast = credits_data.get('cast') or []
        crew = credits_data.get('crew') or []
        self.movie_data = [
            i for i in cast
            if i.get('media_type') == 'movie'
            and 99 not in (i.get('genre_ids') or [])
            and (i.get('character') or '').lower() not in ROLES_EXCLUDE
        ]
        self.tvshow_data = [
            i for i in cast
            if i.get('media_type') == 'tv'
            and not any(g in TV_GENRES_EXCLUDE for g in (i.get('genre_ids') or []))
            and (i.get('character') or '').lower() not in ROLES_EXCLUDE
        ]
        self.director_data = [
            i for i in crew
            if (i.get('job') or '').lower() == 'director' and i.get('media_type') == 'movie'
        ]

    def _set_properties(self):
        fallback = get_icon('genre_family')
        profile = self.person.get('profile_path')
        image = (TMDB_IMG % ('h632', profile)) if profile else fallback
        self.person_image = image

        birthday = self.person.get('birthday') or ''
        deathday = self.person.get('deathday') or ''
        self.person_gender = GENDER_MAP.get(self.person.get('gender'), '')
        self.person_age = _calculate_age(birthday, deathday)
        self.person_birthday = birthday
        self.person_deathday = deathday
        self.person_biography = self.person.get('biography') or ''

        self.setProperty('name', self.person.get('name') or '')
        self.setProperty('id', str(self.person.get('id') or ''))
        self.setProperty('image', image)
        self.setProperty('fanart', FANART_PATH)
        self.setProperty('gender', self.person_gender)
        self.setProperty('place_of_birth', self.person.get('place_of_birth') or '')
        self.setProperty('biography', self.person_biography)
        self.setProperty('birthday', birthday)
        self.setProperty('deathday', deathday)
        self.setProperty('age', self.person_age)
        self.setProperty('enable_scrollbars', 'true')
        self.setProperty('easynews_authorized', 'false')

    def onInit(self):
        bday = self.person_birthday
        if bday and self.person_deathday:
            bday = f'{bday}  [B]-[/B]  {self.person_deathday}'
        infoline = SEPARATOR.join([x for x in (self.person_gender, self.person_age, bday) if x])
        self.set_label(2001, infoline)

        Thread(target=self._populate_credit_list, args=(MOVIES_ID, 'movie', self.movie_data, 'release_date'), daemon=True).start()
        Thread(target=self._populate_credit_list, args=(TVSHOWS_ID, 'tvshow', self.tvshow_data, 'first_air_date'), daemon=True).start()
        Thread(target=self._populate_credit_list, args=(DIRECTOR_ID, 'director', self.director_data, 'release_date'), daemon=True).start()
        self.set_focus_id(50 if self.person_biography else MOVIES_ID)

    def _populate_credit_list(self, control_id, prop_key, raw_items, date_key):
        if not raw_items:
            return
        name_key = 'name' if prop_key == 'tvshow' else 'title'
        sorted_items = _sort_by_release(raw_items, date_key)
        seen = set()
        listitems = []
        for entry in sorted_items:
            tmdb_id = entry.get('id')
            if not tmdb_id or tmdb_id in seen:
                continue
            seen.add(tmdb_id)
            poster = entry.get('poster_path')
            thumb = (TMDB_IMG % ('w780', poster)) if poster else EMPTY_POSTER
            raw_date = str(entry.get(date_key) or '')
            year = raw_date.split('-')[0] if raw_date else 'N/A'
            try:
                rating = f"{float(entry.get('vote_average') or 0):.1f}"
            except (ValueError, TypeError):
                rating = '0.0'
            li = self.make_listitem()
            li.setProperties({
                'name': entry.get(name_key) or '',
                'release_date': year,
                'vote_average': rating,
                'thumbnail': thumb,
                'tmdb_id': str(tmdb_id),
            })
            listitems.append(li)
        if listitems:
            self.setProperty(f'more_from_{prop_key}.number', f'x{len(listitems)}')
            self.add_items(control_id, listitems)

    def run(self):
        self.doModal()
        self.clearProperties()
        return self.deferred_action

    def onClick(self, control_id):
        self.control_id = None
        if control_id == 50:
            ShowTextMedia(
                'textviewer_media.xml',
                text=self.person_biography or 'No biography available.',
                poster=self.person_image,
            ).run()
        elif control_id in (10, 11, 12, 13):
            notification('Use Biography or select a title below')
        else:
            self.control_id = control_id

    def onAction(self, action):
        if action in self.closing_actions:
            self.close()
            return
        if action in self.selection_actions and self.control_id in (MOVIES_ID, TVSHOWS_ID, DIRECTOR_ID):
            li = self.get_listitem(self.control_id)
            if li and li.getProperty('tmdb_id'):
                mtype = 'tvshow' if self.control_id == TVSHOWS_ID else 'movie'
                self.deferred_action = {'media_type': mtype, 'tmdb_id': li.getProperty('tmdb_id')}
                self.close()


def _resolve_person_id(client, query, reference_tmdb_id=''):
    data = client.search_person(query)
    results = (data or {}).get('results') or []
    if not results:
        return None
    if len(results) > 1 and reference_tmdb_id:
        for person in results:
            known_for = person.get('known_for') or []
            if any(str(k.get('id')) == str(reference_tmdb_id) for k in known_for):
                return person.get('id')
    if len(results) == 1:
        return results[0].get('id')
    labels = [f"{p.get('name', 'Unknown')} ({p.get('known_for_department', '')})" for p in results[:15]]
    idx = dialog_select('Select Person', labels)
    if idx < 0:
        return None
    return results[idx].get('id')


def open_person(handle, params):
    person_id = params.get('actor_id')
    query = params.get('key_id') or params.get('query') or ''
    ref_tmdb = params.get('reference_tmdb_id', '')

    show_busy_dialog()
    try:
        client = get_orac_client()
        if not person_id and query:
            person_id = _resolve_person_id(client, query, reference_tmdb_id=ref_tmdb)
        person_data = client.get_person_details(person_id) if person_id else None
    except OracClientError as exc:
        hide_busy_dialog()
        logger('People', f'Orac error loading person: {exc}')
        notification(f'Failed to load person: {exc}')
        return
    hide_busy_dialog()

    if not person_data:
        notification('Person details not found')
        return

    chosen = People('people.xml', person=person_data).run()
    if chosen:
        open_extras(-1, chosen)


def search_people(handle, params):
    query = params.get('query') or dialog_input('Search People').strip()
    if not query:
        return
    open_person(handle, {'key_id': query})
