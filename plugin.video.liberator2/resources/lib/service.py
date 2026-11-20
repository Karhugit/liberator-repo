# -*- coding: utf-8 -*-
import json
import xbmc
from core.kodi import clear_property, get_property, logger
from core.settings import get_bool, get_int
from orac.client import OracClientError, get_orac_client
from playback.player import PLAYBACK_META_PROP
from playback.sources import play as start_next_episode_play
from windows.next_episode import NextEpisode


class LiberatorPlayer(xbmc.Player):
    def __init__(self):
        super().__init__()
        self.meta = None
        self.total_time = 0.0
        self.current_time = 0.0
        self.nextep_prompted = False
        self.marked_watched = False

    def onAVStarted(self):
        raw = get_property(PLAYBACK_META_PROP)
        if not raw:
            self.meta = None
            return
        try:
            self.meta = json.loads(raw)
        except ValueError:
            self.meta = None
            return

        clear_property(PLAYBACK_META_PROP)
        self.total_time = self.getTotalTime()
        self.current_time = 0.0
        self.nextep_prompted = False
        self.marked_watched = False
        logger('PlayerService', f'Playback started: {self.meta.get("title")}')

        resume = float(self.meta.get('resume_point') or 0)
        if 0 < resume < 95 and self.total_time > 0:
            seek_sec = (resume / 100.0) * self.total_time
            if seek_sec > 10:
                self.seekTime(seek_sec)

    def poll_progress(self):
        if not self.meta or not self.isPlayingVideo():
            return
        try:
            self.current_time = self.getTime()
            if self.total_time <= 0:
                self.total_time = self.getTotalTime()
            if self.total_time <= 0:
                return

            remaining = self.total_time - self.current_time
            pct = (self.current_time / self.total_time) * 100.0

            if pct >= 90.0 and not self.marked_watched:
                self._sync_watched(100.0)
                self.marked_watched = True

            if (
                self.meta.get('media_type') == 'episode'
                and self.meta.get('next_episode')
                and not self.nextep_prompted
                and get_bool('nextep.auto_prompt', True)
                and 0 < remaining <= get_int('nextep.prompt_seconds', 30)
            ):
                self.nextep_prompted = True
                self._prompt_next_episode()
        except Exception as exc:
            logger('PlayerService', f'poll_progress error: {exc}')

    def _prompt_next_episode(self):
        next_ep = self.meta.get('next_episode')
        if not next_ep:
            return
        action = NextEpisode('next_episode.xml', meta=next_ep).run()
        if action == 'play':
            self.stop()
            start_next_episode_play(-1, {
                'media_type': 'episode',
                'tmdb_id': str(next_ep['tmdb_id']),
                'season': str(next_ep['season']),
                'episode': str(next_ep['episode']),
                'title': next_ep['title'],
                'direct_play': 'true',
            })

    def onPlayBackStopped(self):
        self._on_playback_finish()

    def onPlayBackEnded(self):
        self._on_playback_finish()

    def _on_playback_finish(self):
        if not self.meta:
            return
        try:
            if not self.marked_watched and self.total_time > 0 and self.current_time > 10:
                pct = round((max(0.0, self.current_time - 5.0) / self.total_time) * 100.0, 1)
                if pct >= 95.0:
                    pct = 100.0
                self._sync_watched(pct)
        finally:
            self.meta = None

    def _sync_watched(self, percent):
        if not self.meta:
            return
        req = {
            'type': self.meta.get('media_type', 'movie'),
            'tmdb_id': int(self.meta['tmdb_id']),
            'percent_watched': percent,
        }
        if req['type'] == 'episode':
            req['season'] = int(self.meta['season'])
            req['episode'] = int(self.meta['episode'])
        if self.meta.get('anilist_id'):
            req['anilist_id'] = str(self.meta['anilist_id'])
        if self.meta.get('absolute_episode'):
            req['absolute_episode'] = str(self.meta['absolute_episode'])
        try:
            get_orac_client().mark_watched(req)
            logger('PlayerService', f'Synced watched={percent}% to Orac: {req}')
        except OracClientError as exc:
            logger('PlayerService', f'Failed to sync watched status: {exc}')


class LiberatorService(xbmc.Monitor):
    def run(self):
        logger('Service', 'Liberator 2 service started')
        player = LiberatorPlayer()
        while not self.abortRequested():
            if player.isPlayingVideo():
                player.poll_progress()
            if self.waitForAbort(1):
                break
        logger('Service', 'Liberator 2 service stopped')


if __name__ == '__main__':
    LiberatorService().run()
