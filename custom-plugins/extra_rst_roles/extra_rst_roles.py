#!/usr/bin/env python
# -*- coding: utf-8 -*-

from docutils.parsers.rst import roles


def html_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
  """A role to create inline code that is highlighted using the Python lexer."""
  options.update({'classes': ['inline-code'], 'language': 'html'})
  return roles.code_role(name, rawtext, text, lineno, inliner, options=options)


def python_role(name, rawtext, text, lineno, inliner, options={}, content=[]):
  """A role to create inline code that is highlighted using the Python lexer."""
  options.update({'classes': ['inline-code'], 'language': 'python'})
  return roles.code_role(name, rawtext, text, lineno, inliner, options=options)


def register():
  roles.register_local_role('html', html_role)
  roles.register_local_role('py', python_role)
