"""
Tests for plugin.py.

Tests are written using the pytest library (https://docs.pytest.org), and you
should read the testing guidelines in the CKAN docs:
https://docs.ckan.org/en/2.9/contributing/testing.html

To write tests for your extension you should install the pytest-ckan package:

    pip install pytest-ckan

This will allow you to use CKAN specific fixtures on your tests.

For instance, if your test involves database access you can use `clean_db` to
reset the database:

    import pytest

    from ckan.tests import factories

    @pytest.mark.usefixtures("clean_db")
    def test_some_action():

        dataset = factories.Dataset()

        # ...

For functional tests that involve requests to the application, you can use the
`app` fixture:

    from ckan.plugins import toolkit

    def test_some_endpoint(app):

        url = toolkit.url_for('myblueprint.some_endpoint')

        response = app.get(url)

        assert response.status_code == 200


To temporary patch the CKAN configuration for the duration of a test you can use:

    import pytest

    @pytest.mark.ckan_config("ckanext.myext.some_key", "some_value")
    def test_some_action():
        pass
"""
import html
import re
from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest

from ckan.plugins import toolkit
from ckan.tests import factories
import ckanext.close_for_guests.plugin as plugin

@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_guest_home_renders_login_form(app):
    response = app.get(toolkit.url_for("home.index"))

    assert response.status_code == 200
    assert 'id="field-login"' in response.body
    assert 'close-for-guests-page--default' in response.body


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({"ckanext.crc.project.id": "1153"}, "sfb1153"),
        ({"ckanext.crc.project.id": "1368"}, "sfb1368"),
        ({"ckan.plugins": "close_for_guests crc1153_layout"}, "sfb1153"),
        ({"ckan.plugins": ["close_for_guests", "sfb_layout"]}, "sfb1368"),
        ({}, "default"),
    ],
)
def test_close_for_guests_theme(monkeypatch, config, expected):
    monkeypatch.setattr(toolkit, "config", config)

    assert plugin.close_for_guests_theme() == expected


@pytest.mark.parametrize(
    ("configured", "expected"),
    [
        (None, "request_access"),
        ("request_access", "request_access"),
        ("default", "default"),
        ("legacy_sfb", "legacy_sfb"),
        ("unexpected", "request_access"),
    ],
)
def test_registration_mode_is_explicit_and_backwards_compatible(
    monkeypatch, configured, expected
):
    config = {}
    if configured is not None:
        config[plugin.REGISTRATION_MODE_CONFIG] = configured
    monkeypatch.setattr(toolkit, "config", config)

    assert plugin.registration_mode() == expected


def test_excluded_path_uses_request_path(app):
    with app.flask_app.test_request_context("/?next=/user/reset"):
        assert plugin.excluded_path() is False

    with app.flask_app.test_request_context("/user/reset"):
        assert plugin.excluded_path() is True
def test_organization_check_uses_current_user_action(monkeypatch):
    user = SimpleNamespace(
        id="user-id", name="user-name", is_authenticated=True
    )
    captured = {}

    def organization_list_for_user(context, data_dict):
        captured["context"] = context
        captured["data_dict"] = data_dict
        return [{"id": "org-id"}]

    monkeypatch.setattr(plugin, "current_user", user)
    monkeypatch.setattr(
        toolkit,
        "get_action",
        lambda action: organization_list_for_user
        if action == "organization_list_for_user"
        else None,
    )

    assert plugin.does_have_organization_helper() is True
    assert captured == {
        "context": {"user": "user-name"},
        "data_dict": {"id": "user-id"},
    }


def test_organization_check_rejects_guests(monkeypatch):
    monkeypatch.setattr(
        plugin,
        "current_user",
        SimpleNamespace(is_authenticated=False),
    )

    assert plugin.does_have_organization_helper() is False
    assert plugin.does_have_organization({}, {}) == {"success": False}


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_strict_mode_redirects_anonymous_home_to_login(app):
    response = app.get("/", follow_redirects=False)
    assert response.status_code == 302
    location = urlparse(response.location)
    assert location.path == "/user/login"
    assert parse_qs(location.query)["came_from"] == ["/"]


def test_strict_redirect_preserves_url_prefix(app, monkeypatch):
    monkeypatch.setitem(toolkit.config, plugin.REQUIRE_LOGIN_CONFIG, True)
    with app.flask_app.test_request_context(
        "/dataset/example", base_url="http://localhost/trr375/"
    ):
        monkeypatch.setattr(plugin, "_is_authenticated_request", lambda: False)
        monkeypatch.setattr(plugin, "_is_authentication_endpoint", lambda: False)
        response = plugin.enforce_login_for_all()

    assert response.status_code == 302
    location = urlparse(response.location)
    assert location.path == "/trr375/user/login"
    assert parse_qs(location.query)["came_from"] == [
        "/trr375/dataset/example"
    ]


def test_missing_legacy_handler_settings_are_not_read_with_config_get(
    app, monkeypatch
):
    legacy_keys = {
        "ckan.login_handler_path",
        "ckan.logout_handler_path",
        "ckan.post_login_url",
        "ckan.post_logout_url",
    }

    class ConfigWithoutLegacySettings(dict):
        def get(self, key, default=None):
            assert key not in legacy_keys
            return super().get(key, default)

    monkeypatch.setattr(
        toolkit, "config", ConfigWithoutLegacySettings()
    )
    with app.flask_app.test_request_context("/dataset/example"):
        assert plugin._is_authentication_endpoint() is False


def test_configured_legacy_login_handler_remains_accessible(app, monkeypatch):
    monkeypatch.setattr(
        toolkit,
        "config",
        {"ckan.login_handler_path": "/custom-login?came_from=/"},
    )
    with app.flask_app.test_request_context("/custom-login"):
        assert plugin._is_authentication_endpoint() is True


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize("extension", ["txt", "zip", "py", "pdf"])
def test_strict_mode_blocks_anonymous_direct_downloads(app, extension):
    path = "/dataset/public/resource/id/download/file.{}".format(extension)
    response = app.get(path, follow_redirects=False)
    assert response.status_code == 302
    location = urlparse(response.location)
    assert location.path == "/user/login"
    assert parse_qs(location.query)["came_from"] == [path]


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize(
    "path",
    ["/dataset/public", "/dataset/public/resource/id", "/dataset/public/resource/id/view/view-id"],
)
def test_strict_mode_blocks_anonymous_dataset_routes(app, path):
    response = app.get(path, follow_redirects=False)
    assert response.status_code == 302
    assert parse_qs(urlparse(response.location).query)["came_from"] == [path]


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_strict_mode_returns_401_for_anonymous_api(app):
    response = app.get("/api/3/action/package_show?id=public")
    assert response.status_code == 401
    assert response.json["success"] is False
    assert response.json["error"]["message"] == "Authentication required"
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize("path", ["/user/login", "/user/reset", "/user/logged_out_redirect"])
def test_strict_mode_keeps_authentication_pages_accessible(app, path):
    assert app.get(path).status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_strict_mode_does_not_redirect_ckan_webassets(app):
    response = app.get(
        "/webassets/asset-that-does-not-exist.css",
        follow_redirects=False,
    )

    assert response.status_code == 404
    assert response.location is None


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "default")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_strict_mode_allows_explicitly_enabled_self_registration(app):
    response = app.get("/user/register", follow_redirects=False)

    assert response.status_code == 200
    assert 'id="user-register-form"' in response.body


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "default")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", False)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_strict_mode_leaves_disabled_self_registration_forbidden(app):
    response = app.get("/user/register", follow_redirects=False)

    assert response.status_code == 403
    assert response.location is None


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "request_access")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_strict_mode_allows_sysadmin_user_creation_form(app):
    sysadmin = factories.Sysadmin()
    response = app.get(
        "/user/register",
        extra_environ={"REMOTE_USER": sysadmin["name"]},
        follow_redirects=False,
    )

    assert response.status_code == 200
    assert 'id="user-register-form"' in response.body


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "request_access")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_request_access_mode_hides_public_registration_even_if_ckan_allows_it(app):
    login = app.get("/user/login")

    assert "Request Access" in login.body
    assert 'href="#"' in login.body
    assert "showInfoText(); return false" in login.body
    assert "Create an Account" not in login.body
    assert 'href="/user/register"' not in login.body
    assert (
        login.body.index("Request Access")
        < login.body.index("Forgot your password?")
        < login.body.rindex("Login")
    )

    response = app.get("/user/register", follow_redirects=False)
    assert response.status_code == 302
    assert urlparse(response.location).path == "/user/login"


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "default")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize("project_id", ["1153", "1368"])
def test_crc_default_mode_uses_standard_ckan_registration_ui(
    app, monkeypatch, project_id
):
    monkeypatch.setitem(toolkit.config, "ckanext.crc.project.id", project_id)
    login = app.get("/user/login")

    assert "Create an Account" in login.body
    assert 'href="/user/register"' in login.body
    assert "Request Access" not in login.body
    assert app.get("/user/register").status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "legacy_sfb")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize("project_id", ["1153", "1368"])
def test_legacy_sfb_mode_restores_v114_login_and_registration(
    app, monkeypatch, project_id
):
    monkeypatch.setitem(toolkit.config, "ckanext.crc.project.id", project_id)

    login = app.get("/user/login")
    assert "Username or Email" in login.body
    assert 'id="field-password"' in login.body
    assert 'id="field-remember"' in login.body
    assert '<form action="' in login.body
    assert '<form action=""' not in login.body
    assert "Request Access" not in login.body
    assert "Create an Account" not in login.body
    assert "Forgot your password?" not in login.body

    registration = app.get("/user/register")
    assert registration.status_code == 200
    assert 'id="user-register-form"' in registration.body
    assert app.get("/user/reset").status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "legacy_sfb")
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_legacy_sfb_mode_does_not_enable_strict_api_gate(app):
    response = app.get("/api/3/action/status_show")

    assert response.status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "legacy_sfb")
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_legacy_sfb_login_form_authenticates_with_ckan_handler(app):
    password = "LegacyLoginPassword123"
    user = factories.User(password=password)
    login_page = app.get("/user/login")
    action_match = re.search(r'<form action="([^"]+)"', login_page.body)
    assert action_match is not None
    action = html.unescape(action_match.group(1))

    response = app.post(
        action,
        data={
            "login": user["name"],
            "password": password,
            "remember": "63072000",
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    me = app.get("/user/me", follow_redirects=False)
    assert me.status_code == 302
    assert "/user/login" not in me.location


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins", "clean_db")
@pytest.mark.parametrize("registration_mode", ["default", "legacy_sfb"])
def test_registration_mode_can_create_user_when_ckan_allows_self_registration(
    app, monkeypatch, registration_mode
):
    monkeypatch.setitem(
        toolkit.config, plugin.REGISTRATION_MODE_CONFIG, registration_mode
    )
    username = "{}-registered-user".format(registration_mode.replace("_", "-"))
    response = app.post(
        "/user/register",
        data={
            "save": "",
            "name": username,
            "fullname": "Self Registered User",
            "email": "self-register@example.test",
            "password1": "TestPassword123",
            "password2": "TestPassword123",
        },
        follow_redirects=False,
    )

    assert response.status_code in (200, 302)
    created = toolkit.get_action("user_show")(
        {"ignore_auth": True}, {"id": username}
    )
    assert created["name"] == username


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config(plugin.REGISTRATION_MODE_CONFIG, "request_access")
@pytest.mark.ckan_config("ckan.auth.create_user_via_web", True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_request_access_mode_sysadmin_can_create_managed_user(app):
    sysadmin = factories.Sysadmin()
    token = factories.APIToken(user=sysadmin["id"])["token"]
    headers = {"Authorization": token}
    form = app.get("/user/register", headers=headers)
    assert form.status_code == 200

    response = app.post(
        "/user/register",
        data={
            "save": "",
            "name": "admin-created-user",
            "fullname": "Admin Created User",
            "email": "admin-created@example.test",
            "password1": "TestPassword123",
            "password2": "TestPassword123",
        },
        headers=headers,
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert "/user/admin-created-user" in response.location
    created = toolkit.get_action("user_show")(
        {"ignore_auth": True}, {"id": "admin-created-user"}
    )
    assert created["name"] == "admin-created-user"


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_strict_mode_allows_authenticated_public_dataset(app):
    user = factories.User()
    dataset = factories.Dataset(private=False)
    environ = {"REMOTE_USER": user["name"]}
    assert app.get(
        "/", extra_environ=environ, follow_redirects=False
    ).status_code == 200
    url = toolkit.url_for("dataset.read", id=dataset["name"])
    assert app.get(
        url, extra_environ=environ, follow_redirects=False
    ).status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_strict_mode_preserves_private_dataset_authorization(app):
    owner = factories.User()
    outsider = factories.User()
    organization = factories.Organization(
        users=[{"name": owner["name"], "capacity": "admin"}]
    )
    dataset = factories.Dataset(
        user=owner, owner_org=organization["id"], private=True
    )
    url = toolkit.url_for("dataset.read", id=dataset["name"])
    assert app.get(
        url,
        extra_environ={"REMOTE_USER": owner["name"]},
        follow_redirects=False,
    ).status_code == 200
    assert app.get(
        url,
        extra_environ={"REMOTE_USER": outsider["name"]},
        follow_redirects=False,
    ).status_code in (403, 404)
