import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
import ckan.lib.helpers as h
from flask_login import current_user, login_user


def is_user_login():
    try:
        return current_user.is_authenticated    
    except:
        return False




def excluded_path():
    path = toolkit.request.url
    if 'user/register' in path:
        return True
    if 'user/reset' in path:
        return True
    return False




def get_login_action():
    came_from = toolkit.request.args.get('came_from') or toolkit.url_for('home.index')
    return toolkit.url_for('user.login', came_from=came_from)



def does_have_organization(context, data_dict=None):
    '''
        Prevent when the user does not have any organization. 
        Organizationless users should not be allowed to visit ckan entities.    
    '''

    if not current_user.is_authenticated:
        return {'success': False}
    orgs = toolkit.get_action('organization_list')({}, {'all_fields':True, 'include_users': True})    
    for org in orgs:
        for user in org['users']:
            if is_user_login():
                if current_user.id == user['id']:
                    return {'success': True}    
    return {'success': False}



def does_have_organization_helper():
    '''
        The helper function for checking a user organization status.    
    '''

    if not current_user.is_authenticated:
        return False
    orgs = toolkit.get_action('organization_list')({}, {'all_fields':True, 'include_users': True})
    for org in orgs:
        for user in org['users']:
            if is_user_login():
                if current_user.id == user['id']:
                    return True    
    return False




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
            'get_login_action': get_login_action,
            'does_have_organization_helper': does_have_organization_helper
        }
    


    
    
