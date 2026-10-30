[![CI](https://github.com/TIBHannover/ckanext-close-for-guests/actions/workflows/test.yml/badge.svg)](https://github.com/TIBHannover/ckanext-close-for-guests/actions/workflows/test.yml)


# ckanext-close-for-guests

The extension for closing CKAN to guest users and show login page.

## Requirements


| CKAN version    | Compatible?   |
| --------------- | ------------- |
| earlier | not tested    |
| 2.9             | Yes   |
| 2.10            | Yes   |
| 2.11            | Yes   |



## Installation


To install ckanext-close-for-guests:

1. Activate your CKAN virtual environment, for example:

        . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

        git clone https://github.com/TIBHannover/ckanext-close-for-guests.git
        cd ckanext-close-for-guests
        pip install -e .
        pip install -r requirements.txt
        python setup.py develop

3. Add `close_for_guests` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

        sudo service apache2 reload

## Strict authentication mode

The historical template-only behavior remains the default. To require a
valid CKAN session or API token for every CKAN page, API action, preview, and
resource download, add this setting:

    ckanext.close_for_guests.require_login_for_all = true

In Docker environments using `ckanext-envvars`, the equivalent variable is:

    CKANEXT__CLOSE_FOR_GUESTS__REQUIRE_LOGIN_FOR_ALL=true

Browser requests are redirected to CKAN's login page with a local
`came_from` URL. Anonymous `/api` requests receive HTTP 401. Login, logout,
password-reset routes, and CKAN static assets remain public. Once a user is
authenticated, CKAN's standard authorization continues to decide whether
public and private datasets and their resources may be read.

Resource storage must not be mounted into a separately public Nginx/Apache
location. Downloads should continue to pass through CKAN's resource download
route so that both this login gate and CKAN's dataset authorization run.

