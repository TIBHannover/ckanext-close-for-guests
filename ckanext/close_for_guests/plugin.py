import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import redirect, make_response
import ckan.lib.helpers as h


def is_user_login():
    if toolkit.g.user:
        return True
    return False

def excluded_path():
    path = toolkit.request.url
    if 'user/register' in path:
        return True
    if 'user/reset' in path:
        return True
    return False

def get_login_action():
    ckan_root_path = toolkit.config.get('ckan.root_path')
    if  ckan_root_path and 'sfb1368/ckan' in ckan_root_path:
        return "/sfb1368/ckan/login_generic?came_from=/sfb1368/ckan/user/logged_in"
    elif ckan_root_path and 'sfb1153/ckan' in ckan_root_path:
        return "/sfb1153/ckan/login_generic?came_from=/sfb1153/ckan/user/logged_in"
    else:
        return "/login_generic?came_from=/user/logged_in"




class CloseForGuestsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)
    
    
    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('public/statics', 'ckanext-close-for-guests')
        

    #ITemplateHelpers

    def get_helpers(self):
        return {'is_user_login': is_user_login,
            'is_excluded': excluded_path,
            'get_login_action': get_login_action
        }
    
    
    