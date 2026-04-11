from caches.base_cache import connect_database, database, get_timestamp
from caches.main_cache import main_cache, cache_object
from modules import kodi_utils, settings, metadata
from modules.utils import get_datetime, adjust_premiered_date, sort_for_article
from modules.thread_manager import make_thread_list
from apis.orac_api import _get_data_via_ipc
logger = kodi_utils.logger

watched_indicators_function, lists_sort_order, date_offset, nextep_method = settings.watched_indicators, settings.lists_sort_order, settings.date_offset, settings.nextep_method
sleep, progressDialogBG, get_video_database_path = kodi_utils.sleep, kodi_utils.progressDialogBG, kodi_utils.get_video_database_path
notification, kodi_refresh, tmdb_api_key, mpaa_region = kodi_utils.notification, kodi_utils.kodi_refresh, settings.tmdb_api_key, settings.mpaa_region
tv_progress_location = settings.tv_progress_location
progress_db_string, indicators_dict = 'liberator_hidden_progress_items', {0: 'watched_db', 1: 'trakt_db'}
finished_show_check = ('Ended', 'Canceled')

def get_database(watched_indicators=None):
    return connect_database(indicators_dict[watched_indicators or watched_indicators_function()])

def get_last_played_value(watched_indicators):
    if watched_indicators == 0: return datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    else: return datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.000Z')

def make_batch_insert(action, media_type, media_id, season, episode, last_played, title):
    if action == 'mark_as_watched': return (media_type, media_id, season, episode, last_played, title)
    else: return (media_type, media_id, season, episode)

def refresh_container(refresh=True):
    if refresh: kodi_refresh()

def active_tvshows_information(status_type):
    def _process(item):
        media_id = item['media_id']
#        meta = metadata.tvshow_meta('tmdb_id', media_id, api_key, mpaa_region_value, get_datetime())
        watched_status = get_watched_status_tvshow(watched_info[media_id], meta.get('total_aired_eps'))[0]
        airing_status = meta.get('status', '')
        if status_type == 'watched':
            if watched_status == 1:
                if not include_other and airing_status not in finished_show_check: return
                results_append(item)
        else:
            if watched_status == 0: results_append(item)
            elif include_other and airing_status not in finished_show_check: results_append(item)
    results = []
    results_append = results.append
    watched_indicators = watched_indicators_function()
    watched_info = watched_info_tvshow()
    api_key, mpaa_region_value = tmdb_api_key(), mpaa_region()
    data = [v for k, v in watched_info.items()]
    progress_location = tv_progress_location()
    if status_type == 'watched': include_other = progress_location in (0, 2)
    else: include_other = progress_location in (1, 2)
    make_thread_list(_process, data)
    return results

def watched_info_movie(watched_db=None):
    if not watched_db: watched_db = get_database()
    try:
        watched_info = watched_db.execute('SELECT media_id, title, last_played FROM watched WHERE db_type = ?', ('movie',)).fetchall()
        return dict([(i[0], {'media_id': i[0], 'title': i[1], 'last_played': i[2]}) for i in watched_info])
    except: return {}

def get_watched_status_movie(watched_info, media_id):
    if not watched_info: return 0
    try:
        watched = 1 if media_id in watched_info else 0
        return watched
    except: return 0



def watched_info_tvshow(watched_db=None):
    if not watched_db: watched_db = get_database()
    try:
        data = watched_db.execute('SELECT media_id, season, episode, title, MAX(last_played), COUNT(*) AS COUNTER FROM watched WHERE db_type = ? GROUP BY media_id',
                                ('episode',)).fetchall()
        return dict([(i[0], {'media_id': i[0], 'season': i[1], 'episode': i[2], 'title': i[3], 'last_played': i[4], 'total_played': i[5]}) for i in data])
    except: return {}

def get_watched_status_tvshow(watched_info, aired_eps):
    if not watched_info: return 0, 0, aired_eps
    try:
        watched = min(watched_info['total_played'], aired_eps)
        unwatched = aired_eps - watched
        if watched >= aired_eps: playcount = 1
        else: playcount = 0
        return playcount, watched, unwatched
    except: return 0, 0, aired_eps



def watched_info_season(media_id, watched_db=None):
    if not watched_db: watched_db = get_database()
    try: watched_info = dict(watched_db.execute('SELECT season, COUNT(*) AS COUNTER FROM watched WHERE db_type = ? AND media_id = ? GROUP BY media_id, season',
                            ('episode', str(media_id))).fetchall())
    except: watched_info = {}
    return watched_info

def get_watched_status_season(watched_info, aired_eps):
    if not watched_info: return 0, 0, aired_eps
    try:
        watched = min(watched_info, aired_eps)
        unwatched = aired_eps - watched
        if watched >= aired_eps: playcount = 1
        else: playcount = 0
        return playcount, watched, unwatched
    except: return 0, 0, aired_eps



def watched_info_episode(media_id, watched_db=None):
    if not watched_db: watched_db = get_database()
    try: watched_info = watched_db.execute('SELECT season, episode FROM watched WHERE db_type = ? AND media_id = ?', ('episode', str(media_id))).fetchall()
    except: watched_info = []
    return watched_info

def get_watched_status_episode(watched_info, season_episode):
    if season_episode in watched_info: return 1
    return 0





def mark_movie(params):
    action = params.get('action')
    tmdb_id = int(params.get('tmdb_id'))
    if action == 'mark_as_unwatched':
        resume_point = 0
    elif params.get('curr_time') is not None and params.get('total_time') is not None:
        curr_time, total_time = params.get('curr_time'), params.get('total_time')
        adjusted_current_time = float(curr_time) - 5
        resume_point = round(adjusted_current_time/float(total_time)*100,1)
        if resume_point >= 95: resume_point = 100
    else:
        resume_point = 100

    ipc_params = {'type': 'movie', 'tmdb_id': tmdb_id, 'percent_watched': resume_point}
    _get_data_via_ipc('mark_movie_watched', ipc_params)
    refresh_container()
    return

def mark_season(params):
    season = int(params.get('season'))
    if season == 0: return notification('Failed')
    action = params.get('action')
    if action == 'mark_as_unwatched':
        percent_watched = 0
    else:
        percent_watched = 100
    tmdb_id = int(params.get('tmdb_id'))
    ipc_params = {'type': 'season', 'tmdb_id': tmdb_id, 'season': season, 'percent_watched': percent_watched}
    _get_data_via_ipc('mark_season_watched', ipc_params)
    refresh_container()
    return

def mark_episode(params):
    # Just send to orac
    # Parameters are ?type=episode&tmdb_id=12345&season=1&episode=1
    season, episode, tmdb_id = int(params.get('season')), int(params.get('episode')), int(params.get('tmdb_id'))
    action = params.get('action')
    if action == 'mark_as_unwatched':
        resume_point = 0
    elif params.get('curr_time') is not None and params.get('total_time') is not None:
        curr_time, total_time = params.get('curr_time'), params.get('total_time')
        adjusted_current_time = float(curr_time) - 5
        resume_point = round(adjusted_current_time/float(total_time)*100,1)
        if resume_point >= 95: resume_point = 100
    else:
        resume_point = 100

    ipc_params = {'type': 'episode', 'tmdb_id': tmdb_id, 'season': season, 'episode': episode, 'percent_watched': resume_point}
    _get_data_via_ipc('mark_episode_watched', ipc_params)
    refresh_container()
    return


def mark_tvshow(params):
    action = params.get('action')
    if action == 'mark_as_unwatched':
        percent_watched = 0
    else:
        percent_watched = 100
    tmdb_id = int(params.get('tmdb_id'))
    ipc_params = {'type': 'tvshow', 'tmdb_id': tmdb_id, 'percent_watched': percent_watched}
    _get_data_via_ipc('mark_tvshow_watched', ipc_params)
    refresh_container()
    return

def drop_tvshow(params):
    tmdb_id = int(params.get('tmdb_id'))
    title = params.get('title', 'Unknown TV Show')
    if not kodi_utils.confirm_dialog(text=f"Are you sure you want to drop [B]{title}[/B]?"):
        return
    ipc_params = {'type': 'tvshow', 'tmdb_id': tmdb_id}
    _get_data_via_ipc('drop_tvshow', ipc_params)
    notification(f"Dropped {title}", 3000)
    refresh_container()
    return

def watched_status_mark(watched_indicators, media_type='', media_id='', action='', season='', episode='', title=''):
    try:
        last_played = get_last_played_value(watched_indicators)
        dbcon = get_database(watched_indicators)
        if action == 'mark_as_watched':
            dbcon.execute('INSERT OR REPLACE INTO watched VALUES (?, ?, ?, ?, ?, ?)', (media_type, media_id, season, episode, last_played, title))
        elif action == 'mark_as_unwatched':
            dbcon.execute('DELETE FROM watched WHERE (db_type = ? and media_id = ? and season = ? and episode = ?)', (media_type, media_id, season, episode))

        # if media_type == 'episode': clear_cache_watched_tvshow_status()
    except: notification('Error')

def batch_watched_status_mark(watched_indicators, insert_list, action):
    try:
        dbcon = get_database(watched_indicators)
        if action == 'mark_as_watched':
            dbcon.executemany('INSERT OR IGNORE INTO watched VALUES (?, ?, ?, ?, ?, ?)', insert_list)
        elif action == 'mark_as_unwatched':
            dbcon.executemany('DELETE FROM watched WHERE (db_type = ? and media_id = ? and season = ? and episode = ?)', insert_list)

        # clear_cache_watched_tvshow_status()
    except: notification('Error')

def get_next_episodes(nextep_content, ipc_params=None):
    logger("Liberator", f"get_next_episodes for content type: {nextep_content}")
    watched_db = get_database()
    if nextep_content == 0:
        data = watched_db.execute('''WITH cte AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY media_id ORDER BY season DESC, episode DESC) rn FROM watched WHERE db_type == ?)
                                    SELECT media_id, season, episode, title, last_played FROM cte WHERE rn = 1''', ('episode',)).fetchall()
    else:
        data = watched_db.execute('SELECT media_id, season, episode, title, MAX(last_played), COUNT(*) AS COUNTER FROM watched WHERE db_type = ? GROUP BY media_id',
                                ('episode',)).fetchall()
    data = [{'media_ids': {'tmdb': int(i[0])}, 'season': int(i[1]), 'episode': int(i[2]), 'title': i[3], 'last_played': i[4]} for i in data]
    data.sort(key=lambda x: (x['last_played']), reverse=True)
    return data
    
def get_next(season, episode, watched_info, season_data, nextep_content):
    logger("Liberator", f"get_next for season: {season} and episode: {episode} and content type: {nextep_content}")
    if episode == 0: episode = 1
    elif nextep_content == 0:
        try:
            episode_count = next((i['episode_count'] for i in season_data if i['season_number'] == season), None)
            season = season if episode < episode_count else season + 1
            episode = episode + 1 if episode < episode_count else 1
        except: pass
    else:
        try:
            next_episode = 0
            relevant_seasons = [i for i in season_data if i['season_number'] >= season]
            for item in relevant_seasons:
                episode_count, item_season = item['episode_count'], item['season_number']
                if season == item_season:
                    if episode >= episode_count:
                        item_season, next_episode = None, None
                        continue
                    episode_range = range(episode + 1, episode_count + 1)
                else: episode_range = range(1, episode_count + 1)
                next_episode = next((i for i in episode_range if not get_watched_status_episode(watched_info, (item_season, i))), None)
                if next_episode: break
            if not next_episode: season, episode = None, None
            season, episode = item_season, next_episode
        except: pass
    return season, episode



def get_watched_items(media_type, page_no):
    if media_type == 'tvshow': results = active_tvshows_information('watched')
    else: results = [v for k,v in watched_info_movie().items()]
    if lists_sort_order('watched') == 0: results = sort_for_article(results, 'title')
    else: results = sorted(results, key=lambda x: x['last_played'], reverse=True)
    return results

def get_recently_watched(media_type, short_list=1):
    watched_indicators = watched_indicators_function()
    if media_type == 'movie':
        data = sorted([v for k,v in watched_info_movie().items()], key=lambda x: x['last_played'], reverse=True)
        if short_list: data = data[:20]
    else:
        dbcon = get_database(watched_indicators)
        if short_list:
            data = dbcon.execute('SELECT media_id, season, episode, title, last_played FROM watched WHERE db_type = ? ORDER BY last_played DESC', ('episode',)).fetchall()
            data = [{'media_ids': {'tmdb': int(i[0])}, 'season': int(i[1]), 'episode': int(i[2]), 'title': i[3], 'last_played': i[4]}
                        for i in data][:20]
        else:
            seen = set()
            seen_add = seen.add
            data = dbcon.execute('SELECT media_id, season, episode, title, last_played FROM watched WHERE db_type = ?', ('episode',)).fetchall()
            data = sorted([{'media_ids': {'tmdb': int(i[0])}, 'season': int(i[1]), 'episode': int(i[2]), 'title': i[3], 'last_played': i[4]}
                        for i in sorted(data, key=lambda x: (x[4], x[0], x[1], x[2]), reverse=True) if not (i[0] in seen or seen_add(i[0]))],
                        key=lambda x: (x['last_played'], x['media_ids']['tmdb'], x['season'], x['episode']), reverse=True)
    return data
