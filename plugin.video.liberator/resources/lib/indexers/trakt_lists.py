# -*- coding: utf-8 -*-
import sys
import json
import random
from threading import Thread
from apis import trakt_api
from apis import orac_api
from indexers.movies import Movies
from indexers.tvshows import TVShows
from indexers.seasons import single_seasons
from indexers.episodes import build_single_episode
from modules import kodi_utils
from modules.utils import paginate_list
from modules.settings import paginate, page_limit
# logger = kodi_utils.logger

add_dir, external, sleep, get_icon = kodi_utils.add_dir, kodi_utils.external, kodi_utils.sleep, kodi_utils.get_icon
trakt_icon, fanart, add_item, set_property = get_icon('trakt'), kodi_utils.get_addon_fanart(), kodi_utils.add_item, kodi_utils.set_property
set_content, set_sort_method, set_view_mode, end_directory = kodi_utils.set_content, kodi_utils.set_sort_method, kodi_utils.set_view_mode, kodi_utils.end_directory
make_listitem, build_url, add_items = kodi_utils.make_listitem, kodi_utils.build_url, kodi_utils.add_items
nextpage_landscape, get_property, clear_property, focus_index = kodi_utils.nextpage_landscape, kodi_utils.get_property, kodi_utils.clear_property, kodi_utils.focus_index
set_category, home, folder_path = kodi_utils.set_category, kodi_utils.home, kodi_utils.folder_path
get_orac_list_contents = orac_api.get_orac_list_contents

def get_trakt_lists(params):
    def _process():
        for item in lists:
            try:
                if list_type == 'liked_lists': item = item['list']
                cm = []
                cm_append = cm.append
                list_name, user, slug, item_count = item['name'], item['user'], item['slug'], item['item_count']
                list_name_upper = " ".join(w.capitalize() for w in list_name.split())
                mode = 'trakt.list.build_trakt_list'
                url_params = {'mode': mode, 'user': user, 'slug': slug, 'list_type': list_type, 'list_name': list_name}
                if randomize_contents: url_params['random'] = 'true'
                elif shuffle: url_params['shuffle'] = 'true'
                url = build_url(url_params)
                listitem = make_listitem()
                listitem.setLabel(display)
                listitem.setArt({'icon': trakt_icon, 'poster': trakt_icon, 'thumb': trakt_icon, 'fanart': fanart, 'banner': fanart})
                info_tag = listitem.getVideoInfoTag()
                info_tag.setPlot(' ')
                listitem.addContextMenuItems(cm)
                yield (url, listitem, True)
            except: pass
    handle = int(sys.argv[1])
    list_type, randomize_contents, shuffle = params['list_type'], params.get('random', 'false'), params.get('shuffle', 'false') == 'true'
    returning_to_list = False
    sort_method = 'label'

def build_trakt_list(params):
    def _process(function, _list, _type):
        if not _list['list']: return
        if _type in ('movies', 'tvshows'): item_list_extend(function(_list).worker())
        elif _type == 'seasons': item_list_extend(function(_list['list']))
        else: item_list_extend(function('episode.trakt_list', _list['list']))
    def _paginate_list(data, page_no, paginate_start):
        if use_result: total_pages = 1
        elif paginate_enabled:
            limit = page_limit(is_home)
            data, total_pages = paginate_list(data, page_no, limit, paginate_start)
            if is_home: paginate_start = limit
        else: total_pages = 1
        return data, total_pages, paginate_start
    handle, is_external, is_home, content, list_name = int(sys.argv[1]), external(), home(), 'movies', params.get('list_name')
    try:
        threads, item_list = [], []
        item_list_extend = item_list.extend
        user, slug, list_type = '', '', ''
        paginate_enabled = paginate(is_home)
        use_result = 'result' in params
        page_no, paginate_start = int(params.get('new_page', '1')), int(params.get('paginate_start', '0'))
        if page_no == 1 and not is_external: set_property('liberator.exit_params', folder_path())
        if use_result: result = params.get('result', [])
        else:
            user, slug, list_type = params.get('user'), params.get('slug'), params.get('list_type')
            with_auth = list_type == 'my_lists'
            item_type = params.get('item_type', 'null')
            result = get_orac_list_contents(list_type, user, slug, with_auth, item_type)
        process_list, total_pages, paginate_start = _paginate_list(result, page_no, paginate_start)
        all_movies = [i for i in process_list if i['type'] == 'movie']
        all_tvshows = [i for i in process_list if i['type'] == 'show']
        all_seasons = [i for i in process_list if i['type'] == 'season']
        all_episodes = [i for i in process_list if i['type'] == 'episode']
        movie_list = {'list': [(i['order'], i['media_ids']) for i in all_movies], 'id_type': 'trakt_dict', 'custom_order': 'true'}
        tvshow_list = {'list': [(i['order'], i['media_ids']) for i in all_tvshows], 'id_type': 'trakt_dict', 'custom_order': 'true'}
        season_list = {'list': all_seasons}
        episode_list = {'list': all_episodes}
        content = max([('movies', len(all_movies)), ('tvshows', len(all_tvshows)), ('seasons', len(all_seasons)), ('episodes', len(all_episodes))], key=lambda k: k[1])[0]
        for item in ((Movies, movie_list, 'movies'), (TVShows, tvshow_list, 'tvshows'),
                    (single_seasons, season_list, 'seasons'), (build_single_episode, episode_list, 'episodes')):
            threaded_object = Thread(target=_process, args=item)
            threaded_object.start()
            threads.append(threaded_object)
        [i.join() for i in threads]
        item_list.sort(key=lambda k: k[1])
        if use_result: return [i[0] for i in item_list]
        add_items(handle, [i[0] for i in item_list])
        if total_pages > page_no:
            new_page = str(page_no + 1)
            new_params = {'mode': 'trakt.list.build_trakt_list', 'list_type': list_type, 'list_name': list_name,
                            'user': user, 'slug': slug, 'paginate_start': paginate_start, 'new_page': new_page}
            add_dir(new_params, 'Next Page (%s) >>' % new_page, handle, 'nextpage', nextpage_landscape)
    except: pass
    set_content(handle, content)
    set_category(handle, list_name)
    end_directory(handle, cacheToDisc=False if is_external else True)
    if not is_external:
        if params.get('refreshed') == 'true': sleep(1000)
        set_view_mode('view.%s' % content, content, is_external)
