from modules.kodi_utils import logger, build_url, make_listitem
from typing import Tuple

container_update = 'Container.Update(%s)'
run_plugin = 'RunPlugin(%s)'

class KodiInfoTagger:
    """Helper class for setting Kodi listitem and videotag data efficiently"""
    
    def __init__(self, poster_empty='', fanart_empty=''):
        self.poster_empty = poster_empty
        self.fanart_empty = fanart_empty
        
    def create_base_listitem(self, title):
        """Create a basic listitem with common setup"""
        listitem = make_listitem()
        listitem.setLabel(title)
        return listitem
        
    def set_art_from_meta(self, listitem, meta, media_type='tvshow', extra_data=None):
        """Set artwork from metadata"""
        extra_data = extra_data or {}

        if media_type == 'episode':
            # For episodes, the primary art is the parent show's, but the thumb is the episode's still.
            show_poster = extra_data.get('show_poster', self.poster_empty)
            show_fanart = extra_data.get('show_fanart', self.fanart_empty)
            show_clearlogo = extra_data.get('show_clearlogo', '')
            show_landscape = extra_data.get('show_landscape', show_fanart)
            
            # The 'thumb' for an episode is its specific still image.
            # Fallback to show landscape/fanart if no still is available.
            episode_thumb = meta.get('episode_thumbnail_path', '') or show_landscape

            art_dict = {
                'poster': show_poster, 'fanart': show_fanart, 'icon': episode_thumb, 'thumb': episode_thumb,
                'clearlogo': show_clearlogo, 'landscape': show_landscape, 'tvshow.poster': show_poster,
                'tvshow.fanart': show_fanart, 'tvshow.clearlogo': show_clearlogo, 'tvshow.landscape': show_landscape
            }
            listitem.setArt(art_dict)
            # The return values are not strictly necessary here but good for consistency.
            return show_poster, show_fanart, show_clearlogo, show_landscape, episode_thumb

        poster = meta.get('poster_path') or self.poster_empty
        fanart = meta.get('fanart_path') or self.fanart_empty
        clearlogo = meta.get('clearlogo_path', '')
        landscape = meta.get('landscape_path', '') or fanart
        thumb = poster or landscape or fanart
        
        art_dict = {
            'poster': poster,
            'fanart': fanart,
            'icon': landscape or poster,
            'clearlogo': clearlogo,
            'landscape': landscape,
            'thumb': thumb
        }
        
        # Add media-specific art
        if media_type == 'tvshow':
            art_dict.update({
                'tvshow.poster': poster,
                'tvshow.clearlogo': clearlogo
            })
        elif media_type == 'movie':
            art_dict.update({
                'movie.poster': poster,
                'movie.clearlogo': clearlogo
            })
        elif media_type == 'season':
            art_dict.update({
                'season.poster': poster,
                'tvshow.poster': extra_data.get('show_poster', poster),
                'tvshow.clearlogo': extra_data.get('show_clearlogo', clearlogo)
            })
        listitem.setArt(art_dict)
        return poster, fanart, clearlogo, landscape, thumb
        
    def set_video_info_tag(self, listitem, meta, media_type, extra_data=None):
        """Set video info tag based on media type and metadata"""
        info_tag = listitem.getVideoInfoTag(offscreen=True)
        extra_data = extra_data or {}
        
        # Common fields
        title = meta.get('title', '')
        year = meta.get('year') or meta.get('show_year', '2050')
        
        info_tag.setMediaType(media_type)
        info_tag.setTitle(title)
        info_tag.setOriginalTitle(meta.get('original_title', ''))
        info_tag.setYear(int(year))
        info_tag.setPlot(meta.get('overview', ''))
        info_tag.setTagLine(meta.get('tagline', ''))
        info_tag.setTrailer(meta.get('trailer', ''))
        info_tag.setRating(meta.get('rating', 0))
        info_tag.setVotes(meta.get('votes', 0))
        info_tag.setMpaa(meta.get('certification', ''))
        
        # Handle premiered/release date
        if media_type == 'tvshow':
            info_tag.setPremiered(meta.get('premiered', ''))
            info_tag.setTvShowTitle(title)
        else:
            info_tag.setPremiered(meta.get('release_date') or meta.get('air_date') or meta.get('premiered', ''))
            
        # Set IDs
        tmdb_id = meta.get('tmdb_id')
        imdb_id = meta.get('imdb_id', '')
        tvdb_id = meta.get('tvdb_id', 0)
        
        unique_ids = {'tmdb': str(tmdb_id)}
        if imdb_id:
            unique_ids['imdb'] = str(imdb_id)
            info_tag.setIMDBNumber(str(imdb_id))
        if tvdb_id:
            unique_ids['tvdb'] = str(tvdb_id)
            
        info_tag.setUniqueIDs(unique_ids)
        
        # Handle genres
        genres = meta.get('genres', [])
        if isinstance(genres, list):
            info_tag.setGenres(genres)
        else:
            info_tag.setGenres([genres] if genres else [])
            
        # Handle studios/networks
        studios = meta.get('network') or meta.get('studio', [])
        if studios:
            if isinstance(studios, list):
                info_tag.setStudios(studios)
            else:
                info_tag.setStudios([studios])
        else:
            info_tag.setStudios([])
            
        # Handle countries
        countries = meta.get('country', [])
        if not isinstance(countries, list):
            countries = [countries] if countries else []
        info_tag.setCountries(countries)
        
        # Media type specific fields
        if media_type == 'tvshow':
            self._set_tvshow_specific_info(info_tag, meta, extra_data)
        elif media_type == 'movie':
            self._set_movie_specific_info(info_tag, meta, extra_data)
        elif media_type == 'episode':
            self._set_episode_specific_info(info_tag, meta, extra_data)
        elif media_type == 'season':
            self._set_season_specific_info(info_tag, meta, extra_data)
            
    def _set_tvshow_specific_info(self, info_tag, meta, extra_data):
        """Set TV show specific info tag data"""
        info_tag.setTvShowStatus(meta.get('status', ''))
        
        # Set playcount from extra_data if provided
        if 'playcount' in extra_data:
            info_tag.setPlaycount(extra_data['playcount'])
            
    def _set_movie_specific_info(self, info_tag, meta, extra_data):
        """Set movie specific info tag data"""
        runtime = meta.get('runtime', 0)
        if runtime:
            try:
                info_tag.setDuration(int(runtime) * 60)  # Convert minutes to seconds
            except (ValueError, TypeError):
                pass
            
        if 'playcount' in extra_data:
            info_tag.setPlaycount(extra_data['playcount'])
            
    def _set_episode_specific_info(self, info_tag, meta, extra_data):
        """Set episode specific info tag data"""
        info_tag.setEpisode(meta.get('episode_number', 0))
        info_tag.setSeason(meta.get('season', 0))
        info_tag.setTvShowTitle(meta.get('tvshowtitle') or extra_data.get('show_title', ''))

        runtime = meta.get('runtime', 0)
        try:
            runtime = int(runtime)
        except (ValueError, TypeError):
            runtime = 0
            
        if runtime:
            info_tag.setDuration(runtime * 60)
            
        if 'playcount' in extra_data:
            info_tag.setPlaycount(extra_data['playcount'])
            

        # Set resume point if progress is available
        progress = extra_data.get('progress') or meta.get('percent_watched')
        
        # Only set resume point if not fully watched (playcount 1 means watched)
        # This prevents 100% watched items showing as "in progress"
        if progress and runtime and not extra_data.get('playcount'):
            try:
                progress = float(progress)
                total_time = runtime * 60
                resume_time = (progress / 100) * total_time
                info_tag.setResumePoint(resume_time, total_time)
            except (ValueError, TypeError):
                pass



        info_tag.setRating(meta.get('episode_rating', 0))

    def _set_season_specific_info(self, info_tag, meta, extra_data):
        """Set season specific info tag data"""
        info_tag.setSeason(meta.get('season', 0))
        info_tag.setTvShowTitle(extra_data.get('show_title', ''))
        
        if 'playcount' in extra_data:
            info_tag.setPlaycount(extra_data['playcount'])
            

class KodiListItemBuilder:
    """Template-based listitem builder for efficient widget creation"""
    
    def __init__(self, poster_empty='', fanart_empty='', widget_settings=None):
        self.infotagger = KodiInfoTagger(poster_empty, fanart_empty)
        self.widget_settings = widget_settings or {}
        
        # Pre-build common URL patterns
        self.url_templates = {
            'extras': 'mode=extras_menu_choice&tmdb_id={tmdb_id}&media_type={media_type}&is_external={is_external}&is_anime={is_anime}',
            'options': 'mode=options_menu_choice&content={media_type}&tmdb_id={tmdb_id}&poster={poster}&is_external={is_external}&is_anime={is_anime}',
            'more_like_this': 'mode=build_tvshow_list&action=imdb_more_like_this&key_id={imdb_id}&name=More Like This based on {title}&is_external={is_external}',
            'recommendations': 'mode=build_tvshow_list&action=tmdb_tv_recommendations&key_id={tmdb_id}&name=Recommended based on {title}',
#           'trakt_lists': 'mode=trakt.list.get_trakt_lists_with_media&media_type={media_type}&imdb_id={imdb_id}&category_name={title} In Trakt Lists',
#           'trakt_manager': 'mode=trakt_manager_choice&tmdb_id={tmdb_id}&imdb_id={imdb_id}&tvdb_id={tvdb_id}&media_type={media_type}&icon={poster}',
            'favorites': 'mode=favorites_choice&media_type={media_type}&tmdb_id={tmdb_id}&title={title}&is_anime={is_anime}',
        }
        


    def build_context_menu_tvshow(self, meta, extra_params):
        """Build context menu for TV shows - simplified version for batch processing"""
        try:
            cm = []
            cm_append = cm.append
            
            tmdb_id = meta.get('tmdb_id')
            poster = meta.get('poster_path') or self.infotagger.poster_empty

            browse_url = extra_params.get('browse_url')
            extras_url = extra_params.get('extras_url')

            if extra_params.get('open_extras'):
                # Main action is extras, so CM gets browse
                if browse_url:
                    cm_append(('[B]Browse[/B]', container_update % browse_url))
            else:
                # Main action is browse, so CM gets extras
                if extras_url:
                    cm_append(('[B]Extras[/B]', run_plugin % extras_url))

            # Orac Lists Manager
            trakt_mgr_params = build_url({'mode': 'orac.lists_manager_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow', 'icon': poster})
            cm_append(('[B]Orac Lists Manager[/B]', run_plugin % trakt_mgr_params))

            # Tag Manager
            add_tag_params = build_url({'mode': 'orac.tag_manager.add_tag', 'media_type': 'tvshow', 'tmdb_id': tmdb_id})
            cm_append(('[B]Add Tag[/B]', run_plugin % add_tag_params))
            remove_tag_params = build_url({'mode': 'orac.tag_manager.remove_tag', 'media_type': 'tvshow', 'tmdb_id': tmdb_id})
            cm_append(('[B]Remove Tag[/B]', run_plugin % remove_tag_params))

            # Watch status handling - this is critical for widget behavior
            total_unwatched = extra_params.get('total_unwatched_episodes', 0)
            watched_title = extra_params.get('watched_title', '')
            
            if total_unwatched > 0:
                watch_params = build_url({'mode': 'watched_status.mark_tvshow', 'action': 'mark_as_watched', 'tmdb_id': tmdb_id})
                cm_append(('[B]Mark Watched %s[/B]' % watched_title, run_plugin % watch_params))
            else:
                if extra_params.get('widget_hide_watched'):
                    return None  # Signal to skip this item
                unwatch_params = build_url({'mode': 'watched_status.mark_tvshow', 'action': 'mark_as_unwatched', 'tmdb_id': tmdb_id})
                cm_append(('[B]Mark Unwatched %s[/B]' % watched_title, run_plugin % unwatch_params))

            drop_params = build_url({'mode': 'watched_status.drop_tvshow', 'tmdb_id': tmdb_id, 'title': extra_params.get('show_title', meta.get('title', ''))})
            cm_append(('[B]Drop Show[/B]', run_plugin % drop_params))

            return cm
            
        except Exception as e:
            logger("Liberator", f"Error building context menu for {meta.get('title', 'Unknown')}: {str(e)}")
            return []  # Return empty context menu rather than failing
        
    def build_context_menu_movie(self, meta, url_params, extra_params):
        """Build context menu for movies"""
        cm = []
        cm_append = cm.append
        
        title = meta.get('title', '')
        tmdb_id = meta.get('tmdb_id')
        imdb_id = meta.get('imdb_id', '')
        poster = meta.get('poster_path') or self.infotagger.poster_empty
        
        # Format URL parameters
        url_params_formatted = {
            'tmdb_id': tmdb_id,
            'imdb_id': imdb_id,
            'title': title,
            'poster': poster,
            'media_type': 'movie',
            'is_external': extra_params.get('is_external', False),
            'is_anime': extra_params.get('is_anime', False)
        }
        
        # Build context menu items
        extras_params = build_url({
            'mode': 'extras_menu_choice',
            'tmdb_id': tmdb_id,
            'media_type': 'movie',
            'is_external': extra_params.get('is_external', False),
            'is_anime': extra_params.get('is_anime', False)
        })
        options_params = build_url({
            'mode': 'options_menu_choice',
            'content': 'movie',
            'tmdb_id': tmdb_id,
            'poster': poster,
            'is_external': extra_params.get('is_external', False),
            'is_anime': extra_params.get('is_anime', False)
        })
        
        if extra_params.get('open_extras'):
            cm_append(('[B]Browse[/B]', container_update % url_params))
            url_params = extras_params
        else:
            cm_append(('[B]Extras[/B]', run_plugin % extras_params))
            
        cm_append(('[B]Options[/B]', run_plugin % options_params))
        import json
        playback_options_params = build_url({'mode': 'playback_choice', 'media_type': 'movie', 'meta': json.dumps(meta)})
        cm_append(('[B]Playback Options[/B]', run_plugin % playback_options_params))
        
        # Movie recommendations
        rec_params = build_url({
            'mode': 'build_movie_list',
            'action': 'tmdb_movie_recommendations',
            'key_id': tmdb_id,
            'name': f'Recommended based on {title}'
        })
        cm_append(('[B]Browse Recommended[/B]', extra_params.get('window_command', '') % rec_params))
        
        # More like this (if IMDB ID available)
        if imdb_id:
            more_params = build_url({
                'mode': 'build_movie_list',
                'action': 'imdb_more_like_this',
                'key_id': imdb_id,
                'name': f'More Like This based on {title}',
                'is_external': extra_params.get('is_external', False)
            })
            cm_append(('[B]Browse More Like This[/B]', extra_params.get('window_command', '') % more_params))
            
            # Trakt lists
#            trakt_lists_params = build_url({'mode': 'trakt.list.get_trakt_lists_with_media', 'media_type': 'movie', 'imdb_id': imdb_id, 'category_name': f'{title} In Trakt Lists'})
#            cm_append(('[B]In Trakt Lists[/B]', extra_params.get('window_command', '') % trakt_lists_params))
        
        # Trakt manager (no tvdb_id for movies)
 #       trakt_mgr_params = build_url({'mode': 'trakt_manager_choice', 'tmdb_id': tmdb_id, 'imdb_id': imdb_id, 'media_type': 'movie', 'icon': poster})
 #       cm_append(('[B]Trakt Lists Manager[/B]', run_plugin % trakt_mgr_params))
        
        # Favorites
        fav_params = build_url({
            'mode': 'favorites_choice',
            'media_type': 'movie',
            'tmdb_id': tmdb_id,
            'title': title,
            'is_anime': extra_params.get('is_anime', False)
        })
        cm_append(('[B]Favorites Manager[/B]', run_plugin % fav_params))
        
        # Orac Lists Manager  
        orac_lists_params = build_url({'mode': 'orac.lists_manager_choice', 'tmdb_id': tmdb_id, 'media_type': 'movie', 'icon': poster})
        cm_append(('[B]Orac Lists Manager[/B]', run_plugin % orac_lists_params))

        # Tag Manager
        add_tag_params = build_url({'mode': 'orac.tag_manager.add_tag', 'media_type': 'movie', 'tmdb_id': tmdb_id})
        cm_append(('[B]Add Tag[/B]', run_plugin % add_tag_params))
        remove_tag_params = build_url({'mode': 'orac.tag_manager.remove_tag', 'media_type': 'movie', 'tmdb_id': tmdb_id})
        cm_append(('[B]Remove Tag[/B]', run_plugin % remove_tag_params))
        
        # Watch status items
        playcount = extra_params.get('playcount', 0)
        watched_title = extra_params.get('watched_title', '')
        
        if playcount == 0:
            watch_params = build_url({
                'mode': 'watched_status.mark_movie',
                'action': 'mark_as_watched',
                'title': title,
                'tmdb_id': tmdb_id
            })
            cm_append(('[B]Mark Watched %s[/B]' % watched_title, run_plugin % watch_params))
        else:
            if extra_params.get('widget_hide_watched'):
                return None  # Signal to skip this item
            unwatch_params = build_url({
                'mode': 'watched_status.mark_movie',
                'action': 'mark_as_unwatched',
                'title': title,
                'tmdb_id': tmdb_id
            })
            cm_append(('[B]Mark Unwatched %s[/B]' % watched_title, run_plugin % unwatch_params))
        
        # External/internal specific items
        if extra_params.get('is_external'):
            cm_append(('[B]Refresh Widgets[/B]', run_plugin % build_url({'mode': 'refresh_widgets'})))
            cm_append(('[B]Reload Widgets[/B]', run_plugin % build_url({'mode': 'kodi_refresh'})))
        else:
            cm_append(('[B]Exit Movie List[/B]', run_plugin % build_url({'mode': 'navigator.exit_media_menu'})))
            
        return cm

    def build_context_menu_episode(self, meta, url_params, extra_params):
        """Build context menu for episodes"""
        cm = []
        cm_append = cm.append
        
        title = meta.get('title', '') or meta.get('episode_title', '')
        show_title = extra_params.get('show_title') or meta.get('tvshowtitle') or meta.get('show_title', '')
        tmdb_id = meta.get('tmdb_id')
        show_tmdb_id = extra_params.get('show_tmdb_id', meta.get('show_tmdb_id'))
        imdb_id = meta.get('imdb_id', '') or extra_params.get('show_imdb_id', meta.get('show_imdb_id', ''))
        tvdb_id = extra_params.get('show_tvdb_id', meta.get('show_tvdb_id', 0))
        season_number = meta.get('season_number', meta.get('season', 1))
        episode_number = meta.get('episode_number', 1)
        poster = meta.get('still_path') or meta.get('show_poster_path', extra_params.get('show_poster', '')) or self.infotagger.poster_empty
        
        # Format URL parameters
        url_params_formatted = {
            'tmdb_id': show_tmdb_id or tmdb_id,
            'imdb_id': imdb_id,
            'tvdb_id': tvdb_id,
            'title': show_title,
            'poster': poster,
            'media_type': 'episode',
            'is_external': extra_params.get('is_external', False),
            'is_anime': extra_params.get('is_anime', False),
            'season_number': season_number,
            'episode_number': episode_number
        }
        
        # Episode specific extras
        extras_params = build_url({
            'mode': 'extras_menu_choice',
            'tmdb_id': url_params_formatted['tmdb_id'],
            'media_type': 'episode',
            'season': season_number,
            'episode': episode_number,
            'is_external': extra_params.get('is_external', False),
            'is_anime': extra_params.get('is_anime', False)
        })
        options_params = build_url({
            'mode': 'options_menu_choice',
            'content': 'episode',
            'tmdb_id': url_params_formatted['tmdb_id'],
            'season': season_number,
            'episode': episode_number,
            'is_external': extra_params.get('is_external', False)
        })
        
        cm_append(('[B]Extras[/B]', run_plugin % extras_params))
        cm_append(('[B]Options[/B]', run_plugin % options_params))
# remove metacache
# Pass playback_choice the items it needs to identify the episode
        import json
        playback_options_params = build_url({'mode': 'playback_choice', 'media_type': 'episode', 'meta': json.dumps(meta), 
                                            'season': season_number, 'episode': episode_number, 'episode_id': meta.get('episode_trakt_id')})
        cm_append(('[B]Playback Options[/B]', run_plugin % playback_options_params))
# Pass playback_choice the items it needs to identify the episode
        
        # Show-level options
        show_extras_params = build_url({
            'mode': 'extras_menu_choice',
            'tmdb_id': url_params_formatted['tmdb_id'],
            'media_type': 'tvshow',
            'is_external': extra_params.get('is_external', False),
            'is_anime': extra_params.get('is_anime', False)
        })
        cm_append(('[B]Show Extras[/B]', run_plugin % show_extras_params))
        
        # Browse season

        season_params = build_url({'mode': 'orac.build_episode_list', 'tmdb_id': url_params_formatted['tmdb_id'], 'season': season_number})
        cm_append(('[B]Browse Season {season_number}[/B]'.format(**url_params_formatted), container_update % season_params))
        
        # Browse all seasons
        seasons_params = build_url({'mode': 'orac.build_season_list', 'tmdb_id': url_params_formatted['tmdb_id']})
        cm_append(('[B]Browse All Seasons[/B]', container_update % seasons_params))
        
        # Trakt manager
#        if imdb_id:
#            trakt_mgr_params = build_url({
#                'mode': 'trakt_manager_choice',
#                'tmdb_id': url_params_formatted['tmdb_id'],
#                'imdb_id': imdb_id,
#                'tvdb_id': tvdb_id,
#                'media_type': 'episode',
#                'season': season_number,
#                'episode': episode_number,
#                'icon': poster
#            })
#            cm_append(('[B]Trakt Lists Manager[/B]', run_plugin % trakt_mgr_params))
        
        # Watch status
        playcount = extra_params.get('playcount', 0)
        watched_title = extra_params.get('watched_title', '')
        
        if playcount == 0:
            watch_params = build_url({
                'mode': 'watched_status.mark_episode',
                'action': 'mark_as_watched',
                'tmdb_id': show_tmdb_id or tmdb_id,
                'season': season_number,
                'episode': episode_number,
                'title': title
            })
            cm_append(('[B]Mark Watched %s[/B]' % watched_title, run_plugin % watch_params))
        else:
            unwatch_params = build_url({
                'mode': 'watched_status.mark_episode',
                'action': 'mark_as_unwatched',
                'tmdb_id': show_tmdb_id or tmdb_id,
                'season': season_number,
                'episode': episode_number,
                'title': title
            })
            cm_append(('[B]Mark Unwatched %s[/B]' % watched_title, run_plugin % unwatch_params))
        
        drop_params = build_url({'mode': 'watched_status.drop_tvshow', 'tmdb_id': show_tmdb_id or tmdb_id, 'title': show_title or 'Unknown Show'})
        cm_append(('[B]Drop Show[/B]', run_plugin % drop_params))
        
        # External/internal specific items
        if extra_params.get('is_external'):
            cm_append(('[B]Refresh Widgets[/B]', run_plugin % build_url({'mode': 'refresh_widgets'})))
            cm_append(('[B]Reload Widgets[/B]', run_plugin % build_url({'mode': 'kodi_refresh'})))
        else:
            cm_append(('[B]Exit Episode List[/B]', run_plugin % build_url({'mode': 'navigator.exit_media_menu'})))
            
        return cm

    def build_context_menu_season(self, meta, url_params, extra_params):
        """Build context menu for seasons"""
        cm = []
        cm_append = cm.append

        tmdb_id = extra_params.get('show_tmdb_id')
        show_title = extra_params.get('show_title') or meta.get('tvshowtitle') or meta.get('show_title', '')
        season_number = meta.get('season', 1)
        watched_title = extra_params.get('watched_title', '')
        is_external = extra_params.get('is_external', False)
        is_anime = extra_params.get('is_anime', False)

        extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow', 'is_external': is_external})
        options_params = build_url({'mode': 'options_menu_choice', 'content': 'season', 'tmdb_id': tmdb_id, 'season': season_number, 'is_external': is_external})
#        trakt_manager_params = build_url({'mode': 'trakt_manager_choice', 'tmdb_id': tmdb_id, 'media_type': 'season', 'season': season_number})
        favorites_params = build_url({'mode': 'favorites_choice', 'media_type': 'tvshow', 'tmdb_id': tmdb_id, 'title': show_title, 'is_anime': is_anime})

        cm_append(('[B]Extras[/B]', run_plugin % extras_params))
        cm_append(('[B]Options[/B]', run_plugin % options_params))

        playcount = extra_params.get('playcount', 0)
        if playcount == 1:
            unwatch_params = build_url({'mode': 'watched_status.mark_season', 'action': 'mark_as_unwatched', 'tmdb_id': tmdb_id, 'season': season_number, 'title': show_title})
            cm_append(('[B]Mark Unwatched %s[/B]' % watched_title, run_plugin % unwatch_params))
        else:
            watch_params = build_url({'mode': 'watched_status.mark_season', 'action': 'mark_as_watched', 'tmdb_id': tmdb_id, 'season': season_number, 'title': show_title})
            cm_append(('[B]Mark Watched %s[/B]' % watched_title, run_plugin % watch_params))

        drop_params = build_url({'mode': 'watched_status.drop_tvshow', 'tmdb_id': tmdb_id, 'title': show_title})
        cm_append(('[B]Drop Show[/B]', run_plugin % drop_params))

#        cm_append(('[B]Trakt Lists Manager[/B]', run_plugin % trakt_manager_params))
        cm_append(('[B]Add to Favorites[/B]', run_plugin % favorites_params))

        if is_external:
            cm_append(('[B]Refresh Widgets[/B]', run_plugin % build_url({'mode': 'refresh_widgets'})))
        else:
            cm_append(('[B]Exit TV Show[/B]', run_plugin % build_url({'mode': 'navigator.exit_media_menu'})))

        return cm

    def build_movie_listitem(self, meta, position, extra_params):
        """Build a complete movie listitem - simplified version"""
        try:
            # Basic movie data
            title = meta.get('title', '')
            year = meta.get('year', '')
            tmdb_id = meta.get('tmdb_id')
            imdb_id = meta.get('imdb_id', '')
            
            if not tmdb_id:
                return None
                
            # Watch status
            percent_watched = meta.get('watched', 0)
            if percent_watched >= 100:
                playcount = 1
            else:
                playcount = 0
            if playcount and extra_params.get('widget_hide_watched'):
                return None
            
            # Create listitem
            listitem = make_listitem()
            listitem.setLabel(title)
            
            # Set basic info
            info_tag = listitem.getVideoInfoTag()
            info_tag.setMediaType('movie')
            info_tag.setTitle(title)
            info_tag.setYear(int(year) if year else 2050)
            info_tag.setIMDBNumber(imdb_id)
            info_tag.setUniqueIDs({'imdb': imdb_id, 'tmdb': str(tmdb_id)})
            info_tag.setPlot(meta.get('overview', ''))
            info_tag.setTagLine(meta.get('tagline', ''))
            info_tag.setOriginalTitle(meta.get('original_title', title))
            info_tag.setPlaycount(1 if playcount else 0)
            
            # Runtime
            runtime = meta.get('runtime', 0)
            if runtime:
                try:
                    info_tag.setDuration(int(runtime) * 60)  # Convert minutes to seconds
                except (ValueError, TypeError):
                    pass
            
            # Rating and country
            rating = meta.get('rating') or meta.get('vote_average')
            if rating:
                try:
                    info_tag.setRating(float(rating))
                except (ValueError, TypeError):
                    pass
            if meta.get('country'):
                info_tag.setCountries([meta.get('country')])
            
            # Genres
            genres = meta.get('genres', [])
            if genres:
                info_tag.setGenres(genres)
            
            # Studios
            studio = meta.get('studio', [])
            if studio:
                info_tag.setStudios(studio)
            
            # Premiered date
            released = meta.get('released')
            if released:
                info_tag.setPremiered(released)
            
            # Artwork
            poster = meta.get('poster_path', poster_empty)
            fanart = meta.get('fanart_path', fanart_empty)
            landscape = meta.get('landscape_path', '')
            clearlogo = meta.get('clearlogo_path', '')
            thumb = poster or landscape or fanart
            
            listitem.setArt({
                'poster': poster,
                'fanart': fanart,
                'icon': poster,
                'clearlogo': clearlogo,
                'landscape': landscape,
                'thumb': thumb
            })
            
            # Build URLs
            play_params = build_url({
                'mode': 'playback.media', 
                'media_type': 'movie', 
                'tmdb_id': tmdb_id,
                'percent_watched': meta.get('watched', 0)
            })
            
            extras_params = build_url({
                'mode': 'extras_menu_choice', 
                'media_type': 'movie', 
                'tmdb_id': tmdb_id, 
                'is_external': extra_params.get('is_external', False)
            })
            
            # Determine main URL and is_folder status
            if extra_params.get('open_extras'):
                url_params = extras_params
                is_folder = False
            else:
                url_params = play_params
                is_folder = False
            
            # Build the full context menu
            cm_extra_params = {**extra_params, 'playcount': playcount}
            cm = self.build_context_menu_movie(meta, play_params, cm_extra_params)
            if cm is None: return None # Item should be hidden
            listitem.addContextMenuItems(cm)
            
            if percent_watched and percent_watched >= 90:
                listitem.setProperties({'watched': '1'})
            else:
                listitem.setProperties({'watched': '0'})
            
            listitem.setProperties({
                'liberator.extras_params': extras_params
#                'watched': '1' if playcount else '0'
            })
            
            return (url_params, listitem, False), position
            
        except Exception as e:
            logger("Liberator", f"Error building movie listitem for {meta.get('title', 'Unknown')}: {str(e)}")
            return None

    def build_tvshow_short_listitem(self, meta, position, extra_params):
        """Build a complete TV show listitem from simplified metadata."""
        try:
            title = meta.get('title', '')
            if not title:
                return None
            
            tmdb_id = meta.get('id') or meta.get('tmdb_id')
            if not tmdb_id:
                return None

            # Ensure year is a valid string before it's passed to set_video_info_tag
            year = meta.get('first_air_date', '')[:4] if meta.get('first_air_date') else ''
            if not year:
                meta['year'] = '2050' # Fallback year

            # For a short listitem, we assume it's unwatched unless data is provided.
            # We also don't have episode counts, so progress is not applicable.
            playcount = 0 
            logger("Liberator", f"Building short TV show listitem for: {title} (TMDB ID: {tmdb_id})")

            # Define browse and extras URLs
            extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow'})
            browse_params = build_url({'mode': 'orac.build_season_list', 'tmdb_id': tmdb_id})

            # Determine main URL and is_folder status
            if extra_params.get('open_extras', False):
                url_params = extras_params
                is_folder = False
            else:
                url_params = browse_params
                is_folder = True
            
            # Create listitem
            listitem = self.infotagger.create_base_listitem(title)
            
            # Set artwork
            self.infotagger.set_art_from_meta(listitem, meta, 'tvshow')
            
            # Set video info tag
            info_extra_data = {'playcount': playcount}
            self.infotagger.set_video_info_tag(listitem, meta, 'tvshow', info_extra_data)
            
            # Build a simplified context menu
            cm = []
            cm_append = cm.append
            if extra_params.get('open_extras', False):
                cm_append(('[B]Browse[/B]', container_update % browse_params))
            else:
                cm_append(('[B]Extras[/B]', run_plugin % extras_params))
            
            options_params = build_url({'mode': 'options_menu_choice', 'content': 'tvshow', 'tmdb_id': tmdb_id})
            cm_append(('[B]Options[/B]', run_plugin % options_params))
            listitem.addContextMenuItems(cm)
            
            # Set basic properties
            listitem.setProperties({
                'watchedepisodes': '0',
                'unwatchedepisodes': '0',
                'watchedprogress': '0',
                'totalepisodes': '0',
                'totalseasons': str(len(meta.get('seasons', [])))
            })
            
            return ((url_params, listitem, is_folder), position)

        except Exception as e:
            import traceback
            logger("Liberator", f"Failed to build short listitem for: {meta.get('title', 'Unknown Title')}")
            logger("Liberator", f"Error building short TV show listitem: {str(e)}")
            logger("Liberator", f"Traceback: {traceback.format_exc()}")
            return None

    def build_season_listitem(self, meta, position, extra_params):
        """Build a complete season listitem using templates"""
        try:
            show_title = extra_params.get('show_title', '')
            season_number = meta.get('season', 0)
            
            if season_number == 0:
                title = meta.get('name', 'Specials')
                season_special = True
            else:
                title = meta.get('name', f'Season {season_number}')
                season_special = False

            # Scan episodes to get watched data
            episodes_list = meta.get('episodes', [])
            episodes_this_season = len(episodes_list)
            
            current_date_str = extra_params.get('current_date_str', '2100-01-01')
            
            episodes_unaired = sum(1 for ep in episodes_list if ep.get('air_date', '') > current_date_str)
            episodes_watched = sum(1 for ep in episodes_list if ep.get('watched_at'))
            
            aired_eps = episodes_this_season - episodes_unaired
            unaired = aired_eps <= 0

            if unaired or season_special:
                progress, playcount, unwatched_eps = 0, 0, aired_eps
                if unaired and not season_special: title = f"[I]UNAIRED[/I] {title}"
            else:
                unwatched_eps = aired_eps - episodes_watched
                playcount = 1 if aired_eps > 0 and unwatched_eps == 0 else 0
                progress = int((episodes_watched / aired_eps) * 100) if aired_eps > 0 else 0

            if extra_params.get('widget_hide_watched') and playcount == 1:
                return None

            url_params = build_url({'mode': 'orac.build_episode_list', 'tmdb_id': extra_params.get('show_tmdb_id'), 'season': season_number})
            listitem = self.infotagger.create_base_listitem(title)

            # Set artwork
            season_art_meta = {
                'poster_path': meta.get('poster_path'),
                'fanart_path': extra_params.get('show_fanart', ''),
                'clearlogo_path': extra_params.get('show_clearlogo', ''),
                'landscape_path': extra_params.get('show_landscape', '')
            }
            art_extra_data = {'show_poster': extra_params.get('show_poster'), 'show_clearlogo': extra_params.get('show_clearlogo')}
            self.infotagger.set_art_from_meta(listitem, season_art_meta, 'season', art_extra_data)

            # Set video info tag
            info_extra_data = {'playcount': playcount, 'show_title': show_title}
            self.infotagger.set_video_info_tag(listitem, meta, 'season', info_extra_data)

            # Build context menu
            cm_extra_params = {**extra_params, 'playcount': playcount}
            cm = self.build_context_menu_season(meta, url_params, cm_extra_params)
            if cm is None: return None
            listitem.addContextMenuItems(cm)

            # Set properties for skin display
            visible_progress = '0' if progress == 100 else str(progress)
            listitem.setProperties({
                'watchedepisodes': str(episodes_watched),
                'unwatchedepisodes': str(unwatched_eps),
                'totalepisodes': str(aired_eps),
                'watchedprogress': visible_progress,
                'totalseasons': str(extra_params.get('total_seasons', ''))
            })

            return ((url_params, listitem, True), position)

        except Exception as e:
            import traceback
            logger("Liberator", f"Error building season listitem for S{season_number} of {show_title}: {str(e)}")
            logger("Liberator", f"Traceback: {traceback.format_exc()}")
            return None

    def build_episode_listitem(self, meta, position, extra_params):
        """Build a complete episode listitem using templates"""
        try:
            title = meta.get('episode_title', '')
            show_title = meta.get('show_title', '')
            tmdb_id = meta.get('tmdb_id')
            show_tmdb_id = meta.get('show_tmdb_id')
            season_number = meta.get('season', 1)
            episode_number = meta.get('episode_number', 1)

            # Get watch status
            playcount = 0
            percent_watched = meta.get('percent_watched', 0)
            
            # Only mark as fully watched if percentage is high enough
            if percent_watched >= 90:
                playcount = 1
                if extra_params.get('widget_hide_watched'):
                    return None

            # Build main URL - usually play episode
            url_params = build_url({
                'mode': 'playback.media',
                'media_type': 'episode', 
                'tmdb_id': show_tmdb_id or tmdb_id,
                'show_trakt_id': meta.get('show_trakt_id'),
                'season': season_number,
                'episode': episode_number,
                'percent_watched': meta.get('percent_watched', 0)
            })
            
            # Create listitem with formatted title
            display_format = extra_params.get('display_format', 0)
            str_season_zfill2, str_episode_zfill2 = str(season_number).zfill(2), str(episode_number).zfill(2)
            if display_format == 0:
                display_title = f"{show_title}: {str_season_zfill2}x{str_episode_zfill2} - {title}"
            elif display_format == 1:
                display_title = f"{str_season_zfill2}x{str_episode_zfill2} - {title}"
            else: # 2
                display_title = title
                
            listitem = self.infotagger.create_base_listitem(display_title)
            
            # Set artwork - prefer episode still, fallback to show art
            # The `meta` object now contains all necessary art paths.
            # `art_extra_data` will pass parent show art to `set_art_from_meta`.
            art_extra_data = {
                'show_poster': meta.get('show_poster_path', ''),
                'show_fanart': meta.get('show_fanart_path', ''),
                'show_clearlogo': meta.get('show_clearlogo_path', ''),
                'show_landscape': meta.get('show_landscape_path', '') or meta.get('show_fanart_path', '')
            }
            self.infotagger.set_art_from_meta(listitem, meta, 'episode', art_extra_data)
            
            # Set video info tag
            extra_data = {
                'playcount': playcount,
                'show_title': show_title,
                'progress': meta.get('progress') or meta.get('percent_watched')
            }
            self.infotagger.set_video_info_tag(listitem, meta, 'episode', extra_data)
            
            # Build context menu
            cm_extra_params = {
                **extra_params, 
                'playcount': playcount,
                'show_tmdb_id': show_tmdb_id, # Already contains meta fallback
                'show_imdb_id': meta.get('show_imdb_id'),
                'show_tvdb_id': meta.get('show_tvdb_id'),
                'show_title': show_title
            }
            cm = self.build_context_menu_episode(meta, url_params, cm_extra_params)
            if cm is None:  # Item should be hidden
                return None
                
            listitem.addContextMenuItems(cm)
            
            # Set episode-specific properties
            runtime = meta.get('runtime', 0)
            air_date = meta.get('air_date', '')
            progress = meta.get('percent_watched', 0)

            properties = {
                'runtime': str(runtime),
                'season': str(season_number),
                'episode': str(episode_number),
                'showtitle': show_title,
                'airdate': air_date,
                'episode_type': meta.get('episode_type', '')
            }
            if progress:
                properties['watchedprogress'] = str(int(progress))
            listitem.setProperties(properties)
            
            return ((url_params, listitem, extra_params.get('is_folder', False)), position)
            
        except Exception as e:
            import traceback
            title = meta.get('title', 'Unknown') if isinstance(meta, dict) else 'Unknown Item'
            logger("Liberator", f"Error building episode listitem for {title}: {str(e)}")
            logger("Liberator", f"Traceback: {traceback.format_exc()}")
            return None

    def build_tvshow_listitem(self, meta, position, extra_params):
        """Build a complete TV show listitem, ensuring URL and is_folder property are always in sync."""
        try:
            title = meta.get('title', '')
            if not title:
                logger("Liberator", f"No title found in metadata at position {position}")
                return None
                
            tmdb_id = meta.get('tmdb_id')
            if not tmdb_id:
                logger("Liberator", f"No TMDB ID found in metadata for '{title}'")
                return None
                
            # Get episode counts - handle different metadata formats
            total_episodes = (meta.get('total_episodes', 0) or 
                            meta.get('total_aired_eps', 0) or
                            meta.get('number_of_episodes', 0))
            
            total_watched_episodes = meta.get('total_watched_episodes', 0)
            total_unaired_episodes = meta.get('total_unaired_episodes', 0)
            total_seasons = meta.get('total_seasons', 1) or meta.get('number_of_seasons', 1)
            
            # Calculate progress and watch status
            total_aired_episodes = total_episodes - total_unaired_episodes if total_episodes else 0
            
            if total_episodes == total_unaired_episodes or total_aired_episodes == 0:
                progress, playcount, total_unwatched = 0, 0, total_episodes
            else:
                playcount = 1 if total_watched_episodes == total_aired_episodes else 0
                total_unwatched = max(0, total_aired_episodes - total_watched_episodes)
                
                if total_watched_episodes and total_aired_episodes > 0:
                    progress = int((total_watched_episodes / total_aired_episodes) * 100)
                else:
                    progress = 0
            
            # Check for explicit watched status (e.g. from internal indexes)
            # 100 = watched, 2 = status watched
            if meta.get('watched') == 100 or meta.get('watched_status') == 2:
                playcount = 1
                progress = 100
                total_unwatched = 0
                if total_aired_episodes > 0:
                    total_watched_episodes = total_aired_episodes

            visible_progress = '0' if progress == 100 else str(progress)
            
            # Check if item should be hidden
            if total_unwatched == 0 and extra_params.get('widget_hide_watched'):
                logger("Liberator", f"Hiding watched show: {title}")
                return None
            
            # Define both browse and extras URLs to determine the final action.
            extras_params = build_url({'mode': 'extras_menu_choice', 'tmdb_id': tmdb_id, 'media_type': 'tvshow'})
            if extra_params.get('all_episodes') and extra_params['all_episodes'] != 1 and total_seasons > 1:
                browse_params = build_url({'mode': 'orac.build_episode_list', 'tmdb_id': tmdb_id, 'season': 'all'})
            else:
                browse_params = build_url({'mode': 'orac.build_season_list', 'tmdb_id': tmdb_id})

            # SWAP the main URL and determine is_folder based on the 'open_extras' setting.
            # This is the key to fixing the double-execution bug.
            if extra_params.get('open_extras', False):
                url_params = extras_params
                is_folder = False # Extras menu is a dialog, not a folder.
            else:
                url_params = browse_params
                is_folder = True # Browsing seasons/episodes is a folder.
            
            # Create listitem
            listitem = self.infotagger.create_base_listitem(title)
            
            # Set artwork
            self.infotagger.set_art_from_meta(listitem, meta, 'tvshow')
            
            # Set video info tag
            extra_data = {'playcount': playcount}
            self.infotagger.set_video_info_tag(listitem, meta, 'tvshow', extra_data)
            
            # Build context menu
            cm_extra_params = {
                **extra_params,
                'browse_url': browse_params,
                'extras_url': extras_params,
                'total_unwatched_episodes': total_unwatched,
                'total_unaired_episodes': total_unaired_episodes,
                'progress': progress
            }
            
            try:
                cm = self.build_context_menu_tvshow(meta, cm_extra_params)
                if cm is None:  # Item should be hidden
                    logger("Liberator", f"Item {title} hidden due to context menu logic")
                    return None
                    
                listitem.addContextMenuItems(cm)
            except Exception as e:
                logger("Liberator", f"Error building context menu for {title}: {str(e)}")
                # Continue without context menu rather than failing entirely
            
            # Set properties
            try:
                listitem.setProperties({
                    'watchedepisodes': str(total_watched_episodes),
                    'unwatchedepisodes': str(total_unwatched),
                    'watchedprogress': visible_progress,
                    'totalepisodes': str(total_aired_episodes),
                    'totalseasons': str(total_seasons)
                })
            except Exception as e:
                logger("Liberator", f"Error setting properties for {title}: {str(e)}")
                # Continue without properties rather than failing entirely
            
#            logger("Liberator", f"Successfully created listitem for: {title} (progress: {progress}%)")
            return ((url_params, listitem, is_folder), position)
            
        except Exception as e:
            import traceback
            logger("Liberator", f"Error building TV show listitem at position {position}: {str(e)}")
            logger("Liberator", f"Metadata keys: {list(meta.keys()) if meta else 'None'}")
            return None


# Usage examples for your existing functions:

def orac_build_tvshow_content_optimized(self, position, meta):
    """Optimized version of your original function"""
    builder = KodiListItemBuilder(poster_empty, fanart_empty)
    
    extra_params = {
        'all_episodes': self.all_episodes,
        'open_extras': self.open_extras,
        'is_external': self.is_external,
        'is_anime': self.is_anime,
        'widget_hide_watched': self.widget_hide_watched,
        'watched_title': self.watched_title,
        'window_command': self.window_command,
        'is_folder': self.is_folder
    }
    
    result = builder.build_tvshow_listitem(meta, position, extra_params)
    if result:
        self.append(result)

def orac_build_movie_content_optimized(self, position, meta):
    """Optimized movie listitem builder"""
    builder = KodiListItemBuilder(poster_empty, fanart_empty)
    
    extra_params = {
        'open_extras': self.open_extras,
        'is_external': self.is_external,
        'is_anime': self.is_anime,
        'widget_hide_watched': self.widget_hide_watched,
        'watched_title': self.watched_title,
        'window_command': self.window_command,
        'is_folder': False,  # Movies usually aren't folders
        'direct_play': getattr(self, 'direct_play', False)
    }
    
    result = builder.build_movie_listitem(meta, position, extra_params)
    if result:
        self.append(result)

# Batch processing helper for performance
def build_content_batch(builder, metadata_list, content_type, extra_params_base):
    """Build multiple listitems in batch for better performance"""
#    logger("Liberator", f"Starting batch processing for {len(metadata_list)} {content_type} items")
    results = []
    
    for position, meta in metadata_list:
        try:
            # Merge any item-specific params with base params
            extra_params = {**extra_params_base}
            
            if content_type == 'tvshow':
                result = builder.build_tvshow_listitem(meta, position, extra_params)
            elif content_type == 'movie':
                result = builder.build_movie_listitem(meta, position, extra_params)
            elif content_type == 'tvshow_short':
                result = builder.build_tvshow_short_listitem(meta, position, extra_params)
            elif content_type == 'episode':
                result = builder.build_episode_listitem(meta, position, extra_params)
            elif content_type == 'season':
                result = builder.build_season_listitem(meta, position, extra_params)
            else:
                logger("Liberator", f"Unknown content type: {content_type}")
                continue
                
            if result:
                results.append(result)
                
        except Exception as e:
            # Log error and continue with next item
            logger("Liberator", f"Error processing {content_type} item at position {position}: {str(e)}")
            continue
    
#    logger("Liberator", f"Batch processing completed: {len(results)} items built from {len(metadata_list)} inputs")
    return results

def get_progress_status_tvshow(watched_episodes, total_episodes):
    """Calculate progress percentage for TV show"""
    if not total_episodes or total_episodes == 0:
        return 0
    progress = int((watched_episodes / total_episodes) * 100)
    return min(progress, 100)  # Cap at 100%

def get_watched_status_tvshow(watched_info, total_aired_eps):
    """Get watched status for a TV show"""
    if not watched_info or not total_aired_eps:
        return 0, 0, total_aired_eps
        
    # This depends on your watched_info structure
    # You'll need to adapt this to your actual data format
    total_watched = watched_info.get('watched_episodes', 0) if isinstance(watched_info, dict) else 0
    total_unwatched = total_aired_eps - total_watched
    playcount = 1 if total_watched == total_aired_eps else 0
        
    return playcount, total_watched, total_unwatched
