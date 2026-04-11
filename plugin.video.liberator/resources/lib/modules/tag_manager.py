"""
Tag Manager Module
Handles tag-related dialogs and user interactions for the Liberator addon.
"""

import xbmcgui
import json
from modules.kodi_utils import select_dialog
from modules import kodi_utils
from apis.orac_api import OracClient

logger = kodi_utils.logger


def get_orac_client():
    """Get configured Orac client instance."""
    from caches.settings_cache import get_setting
    orac_address = get_setting('orac_address') or '127.0.0.1'
    return OracClient(f"http://{orac_address}:5555")


def normalize_tag_name(tag_name):
    """
    Normalize tag name: lowercase and convert spaces to hyphens.
    Matches server-side normalization.
    """
    if not tag_name:
        return ""
    return tag_name.lower().strip().replace(" ", "-")


def create_tag_dialog():
    """
    Shows an input dialog for creating a new tag.
    Returns the normalized tag name or None if cancelled.
    """
    keyboard = xbmcgui.Dialog().input('Enter tag name', type=xbmcgui.INPUT_ALPHANUM)
    if keyboard:
        normalized = normalize_tag_name(keyboard)
        if normalized:
            return normalized
        else:
            xbmcgui.Dialog().ok('Invalid Tag', 'Tag name cannot be empty')
            return None
    return None


def add_tag_menu(media_type, tmdb_id):
    """
    Shows a dialog with existing tags + 'Create New Tag' option.
    Allows user to select an existing tag or create a new one to add to the item.
    
    Args:
        media_type: 'movie' or 'tvshow'
        tmdb_id: TMDB ID of the item
    """
    try:
        client = get_orac_client()
        
        # Get all existing tags
        try:
            response = client.get_all_tags()
            all_tags = response.get('tags', []) if response.get('success') else []
        except Exception as e:
            logger('tag_manager', f'Error fetching tags: {e}')
            all_tags = []
        
        # Get tags already on this item
        try:
            response = client.get_tags_for_item(media_type, tmdb_id)
            current_tags = set(response.get('tags', [])) if response.get('success') else set()
        except Exception as e:
            logger('tag_manager', f'Error fetching item tags: {e}')
            current_tags = set()
        
        # Filter out tags already on the item
        available_tags = [tag for tag in all_tags if tag not in current_tags]
        
        # Build menu options
        menu_items = available_tags + ['[B]Create New Tag[/B]']
        
        # Show selection dialog using the correct signature
        list_items = [{'line1': item} for item in menu_items]
        kwargs = {'items': json.dumps(list_items), 'heading': 'Add Tag'}
        choice = select_dialog(menu_items, **kwargs)
        
        if choice is None:
            return  # User cancelled
        
        if choice == '[B]Create New Tag[/B]':
            # User selected "Create New Tag"
            tag_name = create_tag_dialog()
            if not tag_name:
                return
        else:
            # User selected an existing tag
            tag_name = choice
        
        # Add the tag via API
        try:
            response = client.add_tag_to_item(media_type, tmdb_id, tag_name)
            if response.get('success'):
                xbmcgui.Dialog().notification('Tag Added', f'Added tag: {tag_name}', xbmcgui.NOTIFICATION_INFO, 3000)
            else:
                error_msg = response.get('error', 'Unknown error')
                xbmcgui.Dialog().notification('Error', f'Failed to add tag: {error_msg}', xbmcgui.NOTIFICATION_ERROR, 5000)
        except Exception as e:
            logger('tag_manager', f'Error adding tag: {e}')
            xbmcgui.Dialog().notification('Error', f'Failed to add tag: {str(e)}', xbmcgui.NOTIFICATION_ERROR, 5000)
            
    except Exception as e:
        logger('tag_manager', f'Unexpected error in add_tag_menu: {e}')
        xbmcgui.Dialog().notification('Error', 'An error occurred', xbmcgui.NOTIFICATION_ERROR, 5000)


def remove_tag_menu(media_type, tmdb_id):
    """
    Shows a dialog with current tags for the item.
    Allows user to select a tag to remove.
    
    Args:
        media_type: 'movie' or 'tvshow'
        tmdb_id: TMDB ID of the item
    """
    try:
        client = get_orac_client()
        
        # Get tags for this item
        try:
            response = client.get_tags_for_item(media_type, tmdb_id)
            current_tags = response.get('tags', []) if response.get('success') else []
        except Exception as e:
            logger('tag_manager', f'Error fetching item tags: {e}')
            xbmcgui.Dialog().notification('Error', 'Failed to fetch tags', xbmcgui.NOTIFICATION_ERROR, 5000)
            return
        
        if not current_tags:
            xbmcgui.Dialog().ok('No Tags', 'This item has no tags to remove')
            return
        
        # Show selection dialog using the correct signature
        list_items = [{'line1': tag} for tag in current_tags]
        kwargs = {'items': json.dumps(list_items), 'heading': 'Remove Tag'}
        choice = select_dialog(current_tags, **kwargs)
        
        if choice is None:
            return  # User cancelled
        
        tag_name = choice
        
        # Remove the tag via API
        try:
            response = client.remove_tag_from_item(media_type, tmdb_id, tag_name)
            if response.get('success'):
                xbmcgui.Dialog().notification('Tag Removed', f'Removed tag: {tag_name}', xbmcgui.NOTIFICATION_INFO, 3000)
            else:
                error_msg = response.get('error', 'Unknown error')
                xbmcgui.Dialog().notification('Error', f'Failed to remove tag: {error_msg}', xbmcgui.NOTIFICATION_ERROR, 5000)
        except Exception as e:
            logger('tag_manager', f'Error removing tag: {e}')
            xbmcgui.Dialog().notification('Error', f'Failed to remove tag: {str(e)}', xbmcgui.NOTIFICATION_ERROR, 5000)
            
    except Exception as e:
        logger('tag_manager', f'Unexpected error in remove_tag_menu: {e}')
        xbmcgui.Dialog().notification('Error', 'An error occurred', xbmcgui.NOTIFICATION_ERROR, 5000)
