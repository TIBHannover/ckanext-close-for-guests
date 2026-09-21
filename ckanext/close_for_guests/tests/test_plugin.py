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
import ckanext.close_for_guests.plugin as plugin

@pytest.mark.ckan_config("ckan.plugins", "close_for_guests")
@pytest.mark.ckan_config("SECRET_KEY", "test_secret")
@pytest.mark.usefixtures("with_plugins")
def test_guest_home_renders_login_form(app):
    response = app.get(toolkit.url_for("home.index"))

    assert response.status_code == 200
    assert 'id="field-login"' in response.body


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
