# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
# import os
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------
import sys
from os.path import dirname, join, abspath

from pygments.lexer import RegexLexer
from pygments.token import *

from sphinx.highlighting import lexers

project = 'graphene-django-cud'
copyright = '2019, Tormod Haugland'
author = 'Tormod Haugland'

# The full version, including alpha/beta/rc tags
release = '0.2.2'

# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
        "sphinx_rtd_theme"
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = 'sphinx_rtd_theme'

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

master_doc = 'index'

# Add custom graphql lexer

# -*- coding: utf-8 -*-
"""
    pygments.lexers.graphql
    ~~~~~~~~~~~~~~~~~~~~
    Lexers for GraphQL formats.
    :copyright: Copyright 2017 by Martin Zlámal.
    :license: BSD, see LICENSE for details.
"""


class GraphqlLexer(RegexLexer):
    """
    Lexer for GraphQL.
    """

    name = 'GraphQL'
    aliases = ['graphql', 'gql']
    filenames = ['*.graphql', '*.gql']
    mimetypes = ['application/graphql']

    tokens = {
        'root': [
            (r'#.*', Comment.Singline),
            (r'\.\.\.', Operator),
            (r'"([^\\"]|\\")*"', String.Double),
            (r'(-?0|-?[1-9][0-9]*)(\.[0-9]+[eE][+-]?[0-9]+|\.[0-9]+|[eE][+-]?[0-9]+)', Number.Float),
            (r'(-?0|-?[1-9][0-9]*)', Number.Integer),
            (r'\$+[_A-Za-z][_0-9A-Za-z]*', Name.Variable),
            (r'[_A-Za-z][_0-9A-Za-z]+\s?:', Text),
            (r'(type|query|fragment|mutation|@[a-z]+|on|true|false|null)\b', Keyword.Type),
            (r'[!$():=@\[\]{|}]+?', Punctuation),
            (r'[_A-Za-z][_0-9A-Za-z]*', Keyword),
            (r'(\s|,)', Text),
        ]
    }


lexers["graphql"] = GraphqlLexer()
