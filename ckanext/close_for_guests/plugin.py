import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask_login import current_user


def is_user_login():
    try:
        return bool(current_user.is_authenticated)
    except RuntimeError:
        return False




def excluded_path():
    return toolkit.request.path.startswith('/user/reset')




def get_login_action():
    came_from = toolkit.request.args.get('came_from')
    if not came_from or not came_from.startswith('/') or came_from.startswith('//'):
        came_from = toolkit.url_for('home.index')
    return toolkit.url_for('user.login', came_from=came_from)


def _user_has_organization():
    if not is_user_login():
        return False

    organizations = toolkit.get_action('organization_list_for_user')(
        {'user': current_user.name}, {'id': current_user.id}
    )
    return bool(organizations)



def does_have_organization(context, data_dict=None):
    '''
        Prevent when the user does not have any organization. 
        Organizationless users should not be allowed to visit ckan entities.    
    '''

    return {'success': _user_has_organization()}



def does_have_organization_helper():
    '''
        The helper function for checking a user organization status.    
    '''

    return _user_has_organization()




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
    


    
    
