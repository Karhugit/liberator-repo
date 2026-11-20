# -*- coding: utf-8 -*-
import xbmc
import xbmcgui
from core.kodi import ADDON_PATH

CLOSING_ACTIONS = (
    xbmcgui.ACTION_PARENT_DIR,
    xbmcgui.ACTION_PREVIOUS_MENU,
    xbmcgui.ACTION_STOP,
    xbmcgui.ACTION_NAV_BACK,
)
SELECTION_ACTIONS = (xbmcgui.ACTION_SELECT_ITEM, xbmcgui.ACTION_MOUSE_LEFT_CLICK)
CONTEXT_ACTIONS = (xbmcgui.ACTION_CONTEXT_MENU, xbmcgui.ACTION_MOUSE_RIGHT_CLICK)
INFO_ACTION = xbmcgui.ACTION_SHOW_INFO
LEFT_ACTION = xbmcgui.ACTION_MOVE_LEFT
RIGHT_ACTION = xbmcgui.ACTION_MOVE_RIGHT


class BaseDialog(xbmcgui.WindowXMLDialog):
    def __new__(cls, xml_filename, *args, **kwargs):
        return super().__new__(cls, xml_filename, ADDON_PATH, 'Default', '1080i')

    def __init__(self, xml_filename, *args, **kwargs):
        super().__init__(xml_filename, ADDON_PATH, 'Default', '1080i')
        self.closing_actions = CLOSING_ACTIONS
        self.selection_actions = SELECTION_ACTIONS
        self.context_actions = CONTEXT_ACTIONS
        self.info_action = INFO_ACTION
        self.left_action = LEFT_ACTION
        self.right_action = RIGHT_ACTION
        self.selected = None

    def make_listitem(self):
        return xbmcgui.ListItem(offscreen=True)

    def add_items(self, control_id, items):
        self.getControl(control_id).addItems(items)

    def reset_control(self, control_id):
        self.getControl(control_id).reset()

    def get_listitem(self, control_id):
        return self.getControl(control_id).getSelectedItem()

    def select_item(self, control_id, index):
        self.getControl(control_id).selectItem(index)

    def get_position(self, control_id):
        try:
            return self.getControl(control_id).getSelectedPosition()
        except Exception:
            return 0

    def set_image(self, control_id, image_path):
        try:
            self.getControl(control_id).setImage(image_path or '')
        except Exception:
            pass

    def set_label(self, control_id, text):
        try:
            self.getControl(control_id).setLabel(str(text or ''))
        except Exception:
            pass

    def set_text(self, control_id, text):
        try:
            self.getControl(control_id).setText(str(text or ''))
        except Exception:
            pass

    def set_focus_id(self, control_id):
        try:
            self.setFocusId(control_id)
        except Exception:
            pass

    def get_visibility(self, condition):
        return bool(xbmc.getCondVisibility(condition))

    def sleep(self, ms):
        xbmc.sleep(ms)
