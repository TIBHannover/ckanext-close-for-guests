import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from flask import redirect
import ckan.lib.helpers as h


def is_user_login():
    if toolkit.g.user:
        return True
    return False



class CloseForGuestsPlugin(plugins.SingletonPlugin):
    plugins.implements(plugins.IConfigurer)
    plugins.implements(plugins.ITemplateHelpers)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        

    #ITemplateHelpers

    def get_helpers(self):
        return {'is_user_login': is_user_login
        }