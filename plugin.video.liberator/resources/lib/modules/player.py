# -*- coding: utf-8 -*-
import json
from threading import Thread
from apis.trakt_api import make_trakt_slug
from caches.settings_cache import get_setting
from modules import kodi_utils as ku, settings as st, watched_status as ws

# import 
logger = ku.logger

set_property, clear_property, get_visibility, hide_busy_dialog, xbmc_actor = ku.set_property, ku.clear_property, ku.get_visibility, ku.hide_busy_dialog, ku.xbmc_actor
xbmc_player, execute_builtin, sleep = ku.xbmc_player, ku.execute_builtin, ku.sleep
make_listitem, volume_checker, get_infolabel, xbmc_monitor = ku.make_listitem, ku.volume_checker, ku.get_infolabel, ku.xbmc_monitor
close_all_dialog, notification, poster_empty, fanart_empty = ku.close_all_dialog, ku.notification, ku.empty_poster, ku.get_addon_fanart()
mark_movie, mark_episode = ws.mark_movie, ws.mark_episode
total_time_errors = ('0.0', '', 0.0, None)
set_resume, set_watched = 5, 90
video_fullscreen_check = 'Window.IsActive(fullscreenvideo)'

import sys
import xbmcplugin
import xbmcgui

class LiberatorPlayer(xbmc_player):
    def __init__ (self):
        xbmc_player.__init__(self)
        self.orac_meta = None

    def run(self, url=None, obj=None):
        hide_busy_dialog()
        self.clear_playback_properties()
        if not url: return self.run_error()
        try: return self.play_video(url, obj)
        except: return self.run_error()

    def play_video(self, url, obj):
        logger("orac", "running play_video")

        self.set_constants(url, obj)
        volume_checker()
#        logger("orac", "Testing make_listing")
#        testing_results = self.make_listing()
#        logger("orac", "make_listing came back with results:")
        
        listitem = self.make_listing()
        # Use setResolvedUrl to let Kodi handle playback if possible
        played_via_resolve = False
        try:
            # Check if we have a valid handle and this is a plugin call that expects resolution
            handle = int(sys.argv[1])
            if handle > 0:
                xbmcplugin.setResolvedUrl(handle, True, listitem)
                played_via_resolve = True
        except:
            pass

        if not played_via_resolve:
            self.play(self.url, listitem)

        if not self.is_generic:
            self.check_playback_start()
            if self.playback_successful: self.monitor()
            else:
                self.sources_object.playback_successful = self.playback_successful
                self.sources_object.cancel_all_playback = self.cancel_all_playback
                if self.cancel_all_playback: self.kill_dialog()
                self.stop()
            try: del self.kodi_monitor
            except: pass

    def check_playback_start(self):
        resolve_percent = 0
        while self.playback_successful is None:
            hide_busy_dialog()
            if not self.sources_object.progress_dialog: 
                self.playback_successful = True
            elif self.sources_object.progress_dialog.skip_resolved(): 
                self.playback_successful = False
            elif self.sources_object.progress_dialog.iscanceled():
                self.cancel_all_playback, self.playback_successful = True, False
            elif self.kodi_monitor.abortRequested():
                self.cancel_all_playback, self.playback_successful = True, False
            elif resolve_percent >= 100: 
                self.playback_successful = False
            elif get_visibility('Window.IsTopMost(okdialog)'):
                logger("orac", "check_playback_start: okdialog detected")
                execute_builtin('SendClick(okdialog, 11)')
                self.playback_successful = False
            elif self.isPlayingVideo():
                try:
                    total_time = self.getTotalTime()
                    fullscreen = get_visibility(video_fullscreen_check)
                    if total_time not in total_time_errors:
                        logger("orac", f"check_playback_start: Success! total_time={total_time}, fullscreen={fullscreen}")
                        self.playback_successful = True
                    else:
                        # Log periodically while playing but waiting for total_time to populate
                        if int(resolve_percent * 10) % 50 == 0:
                            logger("orac", f"check_playback_start: isPlayingVideo=True, total_time={total_time}, fullscreen={fullscreen}")
                except Exception as e: 
                    logger("orac", f"check_playback_start: error in isPlayingVideo check: {e}")
                    pass
            resolve_percent = round(resolve_percent + 26.0/100, 1)
            self.sources_object.progress_dialog.update_resolver(percent=resolve_percent)
            sleep(50)

    def playback_close_dialogs(self):
        self.sources_object.playback_successful = True
        self.kill_dialog()
        sleep(200)
        close_all_dialog()

    def monitor(self):
        try:
            ensure_dialog_dead, total_check_time = False, 0
            self.last_progress_point = 0
            if self.media_type == 'episode':
                play_random_continual = self.sources_object.random_continual
                play_random = self.sources_object.random
                disable_autoplay_next_episode = self.sources_object.disable_autoplay_next_episode
                if disable_autoplay_next_episode: notification('Scrape with Custom Values - Autoplay Next Episode Cancelled', 4500)
                if any((play_random_continual, play_random, disable_autoplay_next_episode)): self.autoplay_nextep, self.autoscrape_nextep = False, False
                else: self.autoplay_nextep, self.autoscrape_nextep = self.sources_object.autoplay_nextep, self.sources_object.autoscrape_nextep
            else: play_random_continual, self.autoplay_nextep, self.autoscrape_nextep = False, False, False
            while total_check_time <= 30 and not get_visibility(video_fullscreen_check):
                sleep(100)
                total_check_time += 0.10
            hide_busy_dialog()
            sleep(1000)
            while self.isPlayingVideo():
                try:
                    try: self.total_time, self.curr_time = self.getTotalTime(), self.getTime()
                    except: sleep(250); continue
                    if not ensure_dialog_dead:
                        ensure_dialog_dead = True
                        self.playback_close_dialogs()
                    sleep(1000)
                    self.current_point = round(float(self.curr_time/self.total_time * 100), 1)
                    # Check if progress has advanced by 5%
                    if (self.media_type == 'episode' or self.media_type == 'movie') and self.current_point >= self.last_progress_point + 5:
                        self.last_progress_point = int(self.current_point // 5) * 5
                        if not self.media_marked: self.media_watched_marker()

                    if self.current_point >= set_watched:
                        if play_random_continual: self.run_random_continual(); break
                        if not self.media_marked: self.media_watched_marker()
                    elif self.autoplay_nextep or self.autoscrape_nextep:
                        if not self.nextep_info_gathered: self.info_next_ep()
                        if round(self.total_time - self.curr_time) <= self.start_prep: self.run_next_ep(); break
                except: pass
            hide_busy_dialog()
            if not self.media_marked: self.media_watched_marker()
            self.clear_playback_properties()
            self.clear_playing_item()
        except:
            hide_busy_dialog()
            self.sources_object.playback_successful = False
            self.sources_object.cancel_all_playback = True
            return self.kill_dialog()

    def make_listing(self):
        listitem = make_listitem()
        listitem.setPath(self.url)
        listitem.setContentLookup(False)
        logger("orac", " In make_listing")
        try:
            if self.is_generic:
                info_tag = listitem.getVideoInfoTag()
                info_tag.setMediaType('video')
                info_tag.setFilenameAndPath(self.url)
                return listitem

                # Find which meta to use
            if self.sources_object.media_type == 'movie':
                logger("orac", "In make_listing - movie")
                self.orac_movie_meta = self.sources_object.orac_movie_meta
                self.media_type = 'movie'
                self.tmdb_id, self.imdb_id, self.tvdb_id = self.orac_movie_meta.get('tmdb_id', ''), self.orac_movie_meta.get('imdb_id', ''), None
                self.title, self.year = self.orac_movie_meta.get('title', ''), str(self.orac_movie_meta.get('year', ''))
                self.episode = self.orac_movie_meta.get('episode', '')
                self.season = self.orac_movie_meta.get('season', '')
                poster = self.orac_movie_meta.get('poster') or poster_empty
                fanart = self.orac_movie_meta.get('fanart') or fanart_empty
                clearlogo = self.orac_movie_meta.get('clearlogo') or ''
                duration = (self.orac_movie_meta.get('runtime', 0)) * 60
                plot = self.orac_movie_meta.get('overview', '')
                genre = self.orac_movie_meta.get('genre', [])
                rating = self.orac_movie_meta.get('rating', 0.0)
                premiered = self.orac_movie_meta.get('premiered', '')
                studio = self.orac_movie_meta.get('studio', '') or []
                if isinstance(studio, str): studio = [studio]
                else: studio = list(studio)
                tagline = self.orac_movie_meta.get('tagline', '')
                country = self.orac_movie_meta.get('country', '') or []
                if isinstance(country, str): country = [country]
                else: country = list(country)

                logger("orac", f"Movie Meta: title={self.title}, year={self.year}, tmdb_id={self.tmdb_id}")

                listitem.setLabel(self.title)
                listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'clearlogo': clearlogo})
                info_tag = listitem.getVideoInfoTag()
                info_tag.setMediaType('movie'), info_tag.setTitle(self.title), info_tag.setOriginalTitle(self.orac_movie_meta.get('original_title')), info_tag.setPlot(plot)
                try: info_tag.setYear(int(self.year))
                except: pass
                info_tag.setRating(rating)
                info_tag.setDuration(duration), info_tag.setCountries(country), info_tag.setPremiered(premiered)
                info_tag.setTagLine(tagline), info_tag.setStudios(studio), info_tag.setIMDBNumber(self.imdb_id), info_tag.setGenres(genre)
                info_tag.setUniqueIDs({'imdb': self.imdb_id, 'tmdb': str(self.tmdb_id)})
                self.set_playback_properties()
                logger("orac", "Using Orac movie metadata")
                return listitem

            # Episode
            if self.sources_object.media_type == 'episode':
                logger("orac", "In make_listing - episode")
                self.orac_episode_meta = self.sources_object.orac_episode_meta
                self.media_type = 'episode'
                self.tmdb_id, self.imdb_id, self.tvdb_id = self.orac_episode_meta.get('tmdb_id', ''), self.orac_episode_meta.get('imdb_id', ''), self.orac_episode_meta.get('tvdb_id', 0)
                self.title, self.year = self.orac_episode_meta.get('title', ''), str(self.orac_episode_meta.get('year', ''))
                self.episode = self.orac_episode_meta.get('episode', '')
                self.season = self.orac_episode_meta.get('season', '')
                poster = self.orac_episode_meta.get('poster') or poster_empty
                fanart = self.orac_episode_meta.get('fanart') or fanart_empty
                clearlogo = self.orac_episode_meta.get('clearlogo') or ''
                duration = (self.orac_episode_meta.get('runtime', 0)) * 60
                plot = self.orac_episode_meta.get('overview', '')
                genre = self.orac_episode_meta.get('genre', [])
                rating = self.orac_episode_meta.get('rating', 0.0)
                premiered = self.orac_episode_meta.get('premiered', '')
                studio = self.orac_episode_meta.get('network', '') or []
                if isinstance(studio, str): studio = [studio]
                else: studio = list(studio)
                tagline = self.orac_episode_meta.get('tagline', '')
                country = self.orac_episode_meta.get('country', '') or []
                if isinstance(country, str): country = [country]
                else: country = list(country)
                
                logger("orac", f"Episode Meta: title={self.title}, year={self.year}, season={self.season}, episode={self.episode}, tmdb_id={self.tmdb_id}")
                
                listitem.setLabel(self.title)
                listitem.setArt({'poster': poster, 'fanart': fanart, 'icon': poster, 'clearlogo': clearlogo})
                info_tag = listitem.getVideoInfoTag()
                info_tag.setMediaType('episode'), info_tag.setTitle(self.title), info_tag.setOriginalTitle(self.orac_episode_meta.get('original_title')), info_tag.setPlot(plot)
                info_tag.setTvShowTitle(self.orac_episode_meta.get('tvshowtitle', '')), info_tag.setSeason(self.season or 0), info_tag.setEpisode(self.episode or 0)
                try: info_tag.setYear(int(self.year))
                except: pass
                info_tag.setRating(rating)
                info_tag.setDuration(duration), info_tag.setCountries(country), info_tag.setPremiered(premiered)
                info_tag.setTagLine(tagline), info_tag.setStudios(studio), info_tag.setIMDBNumber(self.imdb_id), info_tag.setGenres(genre)
                info_tag.setUniqueIDs({'imdb': self.imdb_id, 'tmdb': str(self.tmdb_id)})
                self.set_playback_properties()
                logger("orac", "Using Orac episode metadata")
                return listitem
        except Exception as e:
            import traceback
            logger("orac", f"Error in make_listing trace: {traceback.format_exc()}")
            return listitem

# Unknown media type
        logger("orac", "In make_listing - unknown media type")
        info_tag = listitem.getVideoInfoTag()
        info_tag.setMediaType('video')
        info_tag.setFilenameAndPath(self.url)
        return listitem


    def media_watched_marker(self, force_watched=False):
        logger("orac", "In media_watched_marker")
        if self.media_marked and not force_watched: return
        try:
            if self.current_point >= set_watched or force_watched:
                watched_params = {'action': 'mark_as_watched', 'tmdb_id': self.tmdb_id, 'title': self.title, 'year': self.year, 'season': self.season, 'episode': self.episode,
                                    'tvdb_id': self.tvdb_id, 'from_playback': 'true',
                                    'media_type': self.media_type}
                self.media_marked = True
                if self.media_type == 'episode':
                    result = mark_episode(watched_params)
                else:
                    result = mark_movie(watched_params)
            else:
                progress_params = {'media_type': self.media_type, 'tmdb_id': self.tmdb_id, 'curr_time': self.curr_time, 'total_time': self.total_time,
                                    'title': self.title, 'season': self.season, 'episode': self.episode, 'from_playback': 'true'}
                if self.media_type == 'episode':
                    result = mark_episode(progress_params)
                else:
                    result = mark_movie(progress_params)


        except Exception as e:
            logger("orac", f"Error in media_watched_marker: {e}")
            return False


    def run_media_progress(self, function, params):
        try: function(params)
        except: pass

    def run_next_ep(self):
        from modules.episode_tools import EpisodeTools
        if not self.media_marked: self.media_watched_marker(force_watched=True)
        EpisodeTools(self.meta, self.nextep_settings).auto_nextep()

    def run_random_continual(self):
        from modules.episode_tools import EpisodeTools
        if not self.media_marked: self.media_watched_marker(force_watched=True)
        EpisodeTools(self.meta).play_random_continual(False)



    def info_next_ep(self):
        self.nextep_info_gathered = True
        try:
            play_type = 'autoplay_nextep' if self.autoplay_nextep else 'autoscrape_nextep'
            nextep_settings = auto_nextep_settings(play_type)
            final_chapter = self.final_chapter() if nextep_settings['use_chapters'] else None
            percentage = 100 - final_chapter if final_chapter else nextep_settings['window_percentage']
            window_time = round((percentage/100) * self.total_time)
            use_window = nextep_settings['alert_method'] == 0
            default_action = nextep_settings['default_action']
            self.start_prep = nextep_settings['scraper_time'] + window_time
            self.nextep_settings = {'use_window': use_window, 'window_time': window_time, 'default_action': default_action, 'play_type': play_type}
        except: pass

    def final_chapter(self):
        try:
            final_chapter = float(get_infolabel('Player.Chapters').split(',')[-1])
            if final_chapter >= 90: return final_chapter
        except: pass
        return None

    def kill_dialog(self):
        try: self.sources_object._kill_progress_dialog()
        except: close_all_dialog()

    def set_constants(self, url, obj):
        self.url = url
        self.sources_object = obj
        self.is_generic = self.sources_object == 'video'
        if not self.is_generic:
            if self.sources_object.media_type == 'movie':
                self.orac_meta = self.sources_object.orac_movie_meta
                self.meta_get = self.orac_meta.get
            else:
                self.orac_meta = self.sources_object.orac_episode_meta
                self.meta_get = self.orac_meta.get
            self.kodi_monitor, self.playback_percent = xbmc_monitor(), self.sources_object.playback_percent or 0.0

            self.playing_filename = self.sources_object.playing_filename
            logger("orac", f"Playing filename set to: {self.playing_filename}")
            self.media_marked, self.nextep_info_gathered = False, False
            self.playback_successful, self.cancel_all_playback = None, False
            self.playing_item = self.sources_object.playing_item
            logger("orac", f"Playing item set to: {self.playing_item}")

    def set_playback_properties(self):
        try:
            trakt_ids = {'tmdb': self.tmdb_id, 'imdb': self.imdb_id, 'slug': make_trakt_slug(self.title)}
            if self.media_type == 'episode': trakt_ids['tvdb'] = self.tvdb_id
            set_property('script.trakt.ids', json.dumps(trakt_ids))
            if self.playing_filename: set_property('subs.player_filename', self.playing_filename)
        except: pass

    def clear_playback_properties(self):
        clear_property('liberator.window_stack')
        clear_property('script.trakt.ids')
        clear_property('subs.player_filename')

    def clear_playing_item(self):
        if self.playing_item['cache_provider'] == 'Offcloud':
            if self.playing_item.get('direct_debrid_link', False): return
            if store_resolved_to_cloud('Offcloud', 'package' in self.playing_item): return
            from apis.offcloud_api import OffcloudAPI
            OffcloudAPI().clear_played_torrent(self.playing_item)

    def run_error(self):
        try: self.sources_object.playback_successful = False
        except: pass
        self.clear_playback_properties()
        notification('Playback Failed', 3500)
        return False
