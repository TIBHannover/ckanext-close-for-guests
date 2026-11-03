import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.common import asbool, g
from flask import jsonify, redirect
from flask_login import current_user


REQUIRE_LOGIN_CONFIG = 'ckanext.close_for_guests.require_login_for_all'
REGISTRATION_MODE_CONFIG = 'ckanext.close_for_guests.registration_mode'
REGISTRATION_MODE_REQUEST_ACCESS = 'request_access'
REGISTRATION_MODE_DEFAULT = 'default'
AUTH_ENDPOINTS = frozenset({
    'user.login', 'user.logged_in', 'user.logout', 'user.logged_out',
    'user.logged_out_page', 'user.request_reset', 'user.perform_reset',
})


def is_user_login():
    try:
        return bool(current_user.is_authenticated)
    except RuntimeError:
        return False




def excluded_path():
    # These pages must render CKAN's own content for anonymous users.  The
    # registration view performs its user_create authorization check before
    # rendering, so this does not enable registration by itself.
    return (
        toolkit.request.path.startswith('/user/reset')
        or (
            toolkit.request.endpoint == 'user.register'
            and registration_mode() == REGISTRATION_MODE_DEFAULT
        )
    )


def registration_mode():
    """Return the configured login/registration workflow.

    The historical request-access screen remains the fallback for deployments
    that have not selected a mode yet.
    """
    configured = str(toolkit.config.get(
        REGISTRATION_MODE_CONFIG, REGISTRATION_MODE_REQUEST_ACCESS
    )).strip().lower()
    if configured == REGISTRATION_MODE_DEFAULT:
        return REGISTRATION_MODE_DEFAULT
    return REGISTRATION_MODE_REQUEST_ACCESS


def uses_request_access():
    return registration_mode() == REGISTRATION_MODE_REQUEST_ACCESS




def get_login_action():
    came_from = toolkit.request.args.get('came_from')
    if not came_from or not came_from.startswith('/') or came_from.startswith('//'):
        came_from = toolkit.url_for('home.index')
    return toolkit.url_for('user.login', came_from=came_from)


def require_login_for_all():
    """Return whether the opt-in, server-side guest gate is enabled."""
    return asbool(toolkit.config.get(REQUIRE_LOGIN_CONFIG, False))


def _is_authenticated_request():
    """Use CKAN's already-resolved session-cookie or API-token identity."""
    return bool(getattr(g, 'user', None) and getattr(g, 'userobj', None))


def _is_authentication_endpoint():
    endpoint = toolkit.request.endpoint
    if endpoint in AUTH_ENDPOINTS or endpoint == 'static':
        return True
    if endpoint == 'user.register':
        return registration_mode() == REGISTRATION_MODE_DEFAULT

    # repoze.who consumes these routes outside Flask in production. Custom
    # handler paths must also remain reachable to establish/clear a session.
    path = toolkit.request.path.rstrip('/') or '/'
    configured_paths = {
        str(toolkit.config.get(key, '')).split('?', 1)[0].rstrip('/')
        for key in (
            'ckan.login_handler_path', 'ckan.logout_handler_path',
            'ckan.post_login_url', 'ckan.post_logout_url',
        )
        if toolkit.config.get(key)
    }
    return path in configured_paths


def enforce_login_for_all():
    """Block every anonymous CKAN route except authentication and assets."""
    # Request-access deployments must never expose CKAN self-registration,
    # even if create_user_via_web was enabled accidentally.  Authenticated
    # sysadmins still use the same CKAN route to create managed accounts.
    if (
        toolkit.request.endpoint == 'user.register'
        and uses_request_access()
        and not _is_authenticated_request()
    ):
        return redirect(toolkit.url_for('user.login'), code=302)

    if not require_login_for_all():
        return None
    if _is_authenticated_request() or _is_authentication_endpoint():
        return None

    if toolkit.request.path == '/api' or toolkit.request.path.startswith('/api/'):
        response = jsonify({
            'success': False,
            'error': {
                '__type': 'Authorization Error',
                'message': 'Authentication required',
            },
        })
        response.status_code = 401
        response.headers['WWW-Authenticate'] = 'Bearer'
        return response

    came_from = toolkit.request.script_root + toolkit.request.full_path
    if came_from.endswith('?'):
        came_from = came_from[:-1]
    return redirect(
        toolkit.url_for('user.login', came_from=came_from), code=302
    )


def close_for_guests_theme():
    """Return the project theme used by the guest login page."""
    project_id = str(
        toolkit.config.get('ckanext.crc.project.id') or ''
    ).strip()
    if project_id in {'1153', '1368'}:
        return 'sfb{}'.format(project_id)

    configured_plugins = toolkit.config.get('ckan.plugins', [])
    if isinstance(configured_plugins, str):
        configured_plugins = configured_plugins.split()

    if 'crc1153_layout' in configured_plugins:
        return 'sfb1153'
    if 'sfb_layout' in configured_plugins:
        return 'sfb1368'

    return 'default'


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
    plugins.implements(plugins.IMiddleware)

    
    
    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('public/statics', 'ckanext-close-for-guests')

    # IMiddleware

    def make_middleware(self, app, config):
        # CKAN's identity resolver was registered first, so g.user/g.userobj
        # contain the normal session or API-token identity at this point.
        app.before_request(enforce_login_for_all)
        return app

    def make_error_log_middleware(self, app, config):
        """Keep CKAN's error-log middleware stack unchanged."""
        return app
        

    #ITemplateHelpers

    def get_helpers(self):
        return {'is_user_login': is_user_login,
            'is_excluded': excluded_path,
            'get_login_action': get_login_action,
            'require_login_for_all': require_login_for_all,
            'close_for_guests_registration_mode': registration_mode,
            'close_for_guests_uses_request_access': uses_request_access,
            'close_for_guests_theme': close_for_guests_theme,
            'does_have_organization_helper': does_have_organization_helper
        }
    


    
    
