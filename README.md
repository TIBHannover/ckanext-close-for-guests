[![CI](https://github.com/TIBHannover/ckanext-close-for-guests/actions/workflows/test.yml/badge.svg)](https://github.com/TIBHannover/ckanext-close-for-guests/actions/workflows/test.yml)


# ckanext-close-for-guests

The extension for closing CKAN to guest users and show login page.

## Requirements


| CKAN version    | Compatible?   |
| --------------- | ------------- |
| earlier | not tested    |
| 2.9             | Yes   |



## Installation


To install ckanext-close-for-guests:

1. Activate your CKAN virtual environment, for example:

        . /usr/lib/ckan/default/bin/activate

2. Clone the source and install it on the virtualenv

        git clone https://github.com//ckanext-close-for-guests.git
        cd ckanext-close-for-guests
        pip install -e .
        pip install -r requirements.txt
        python setup.py develop

3. Add `close_for_guests` to the `ckan.plugins` setting in your CKAN
   config file (by default the config file is located at
   `/etc/ckan/default/ckan.ini`).

4. Restart CKAN. For example if you've deployed CKAN with Apache on Ubuntu:

        sudo service apache2 reload


