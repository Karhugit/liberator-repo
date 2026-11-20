# -*- coding: utf-8 -*-
import xbmc
from windows.base import BaseDialog

BUTTON_ACTIONS = {10: 'close', 11: 'play', 12: 'cancel'}


class NextEpisode(BaseDialog):
    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename)
        self.meta = kwargs.get('meta', {})
        self.selected = kwargs.get('default_action', 'cancel')
        self.closed = False
        self._set_properties()

    def _set_properties(self):
        self.setProperty('thumb', self.meta.get('ep_thumb') or self.meta.get('fanart') or '')
        self.setProperty('clearlogo', self.meta.get('clearlogo') or '')
        label = '%s[B] | [/B]%02dx%02d[B] | [/B]%s' % (
            self.meta.get('title', ''),
            int(self.meta.get('season', 1)),
            int(self.meta.get('episode', 1)),
            self.meta.get('ep_name', ''),
        )
        self.setProperty('episode_label', label)
        self.setProperty('episode_status.highlight', '')
        self.setProperty('episode_status.flag', '')

    def onInit(self):
        self.setFocusId(11)
        player = xbmc.Player()
        while player.isPlaying() and not self.closed:
            self.sleep(500)
        if not self.closed:
            self.close()

    def run(self):
        self.doModal()
        self.clearProperties()
        return self.selected

    def onAction(self, action):
        if action in self.closing_actions:
            self.selected = 'close'
            self.closed = True
            self.close()

    def onClick(self, control_id):
        self.selected = BUTTON_ACTIONS.get(control_id, 'cancel')
        self.closed = True
        self.close()
