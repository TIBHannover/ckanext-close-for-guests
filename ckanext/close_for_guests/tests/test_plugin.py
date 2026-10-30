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
from types import SimpleNamespace

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
    response = app.get("/")
    assert response.status_code == 302
    assert response.location.endswith("/user/login?came_from=%2F")


def test_strict_redirect_preserves_url_prefix(app, monkeypatch):
    monkeypatch.setitem(toolkit.config, plugin.REQUIRE_LOGIN_CONFIG, True)
    with app.flask_app.test_request_context(
        "/dataset/example", environ_base={"SCRIPT_NAME": "/trr375"}
    ):
        monkeypatch.setattr(plugin, "_is_authenticated_request", lambda: False)
        monkeypatch.setattr(plugin, "_is_authentication_endpoint", lambda: False)
        response = plugin.enforce_login_for_all()

    assert response.status_code == 302
    assert "came_from=%2Ftrr375%2Fdataset%2Fexample" in response.location


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize("extension", ["txt", "zip", "py", "pdf"])
def test_strict_mode_blocks_anonymous_direct_downloads(app, extension):
    path = "/dataset/public/resource/id/download/file.{}".format(extension)
    response = app.get(path)
    assert response.status_code == 302
    assert "/user/login?came_from=" in response.location


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
@pytest.mark.parametrize(
    "path",
    ["/dataset/public", "/dataset/public/resource/id", "/dataset/public/resource/id/view/view-id"],
)
def test_strict_mode_blocks_anonymous_dataset_routes(app, path):
    assert app.get(path).status_code == 302


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
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_strict_mode_allows_authenticated_public_dataset(app):
    user = factories.User()
    dataset = factories.Dataset(private=False)
    headers = {"Authorization": user["apikey"]}
    assert app.get("/", headers=headers).status_code == 200
    url = toolkit.url_for("dataset.read", id=dataset["name"])
    assert app.get(url, headers=headers).status_code == 200


@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config(plugin.REQUIRE_LOGIN_CONFIG, True)
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins", "clean_db")
def test_strict_mode_preserves_private_dataset_authorization(app):
    owner = factories.User()
    outsider = factories.User()
    dataset = factories.Dataset(user=owner, private=True)
    url = toolkit.url_for("dataset.read", id=dataset["name"])
    assert app.get(url, headers={"Authorization": owner["apikey"]}).status_code == 200
    assert app.get(url, headers={"Authorization": outsider["apikey"]}).status_code == 403
