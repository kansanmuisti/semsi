semsi
=====

semsi is a toolbox and a web-based service for semantic similarity analysis.
It provides facilities for retrieving a list of similar documents and
for suggesting relevant topic words.

Currently it only supports the Finnish language. We also provide a service
for transforming Finnish words into their basic forms
([lemmatisation](http://en.wikipedia.org/wiki/Lemmatisation)). We use
the sukija package inside [Voikko](http://voikko.sourceforge.net/) for the
vocabulary and morphology rules.

We use [Flask](http://flask.pocoo.org/) as our web framework.

Installation
------------

It's easiest to run semsi in a virtualenv. The package `virtualenvwrapper`
provides a nice set of scripts to manage virtualenvs.

    mkvirtualenv semsi
    pip install -r requirements.txt

To install the Finnish vocabulary and morphological rules:

    wget http://www.kansanmuisti.fi/storage/sukija-v1.tar.bz2
    tar -C lexicon -xvjf sukija-v1.tar.bz2

You might want to run semsi with [gunicorn](http://gunicorn.org/):

    pip install gunicorn
    gunicorn semsi:app

Et voilà! You may now run `./stem-client.py` to test your brand new
Finnish stemming service.
