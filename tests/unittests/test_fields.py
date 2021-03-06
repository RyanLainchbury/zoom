# -*- coding: utf-8 -*-

"""
    test the fields module
"""

import unittest
import logging

from zoom.fields import *
from zoom.tools import unisafe

logger = logging.getLogger('zoom.fields')


class TextTests(object):

    def setUp(self, field_type):
        self.field_type = field_type
        self.show_css_class = self.css_class = self.field_type.css_class
        self.basic_text = 'test text'
        self.encoded_text = 'A “special character” & quote test.'
        self.edit_template = '{widget}'
        self.display_template = '{text}'

    def compare(self, expected, got):
        def strify(text):
            if type(text) is str:
                return text.encode('utf8')
            return text
        logger.debug('expected:\n%s\n', strify(expected))
        logger.debug('.....got:\n%s\n', strify(got))
        self.assertEqual(strify(expected), strify(got))

    def test_widget(self):
        f = self.field_type('Field1')
        f.initialize({'field1': self.basic_text})
        t = self.widget_template.format(self=self, text=self.basic_text)
        self.compare(t, f.widget())

    def test_widget_with_unicode(self):
        f = self.field_type('Field1')
        f.initialize({'field1': self.encoded_text})
        t = self.widget_template.format(self=self, text=htmlquote(self.encoded_text))
        self.compare(t, f.widget())

    def test_display_value(self):
        f = self.field_type('Field1')
        f.initialize({'field1': self.basic_text})
        t = self.display_template.format(self=self, text=self.basic_text)
        self.compare(t, f.display_value())

    def test_display_value_with_unicode(self):
        f = self.field_type('Field1')
        f.initialize({'field1': self.encoded_text})
        t = self.display_template.format(self=self, text=htmlquote(self.encoded_text))
        self.compare(t, f.display_value())


class TestMemoField(unittest.TestCase, TextTests):

    def setUp(self, *a, **k):
        TextTests.setUp(self, MemoField)
        self.show_css_class = 'textarea'
        self.widget_template = (
            '<textarea class="{self.css_class}" cols="60" id="field1" '
            'name="field1" rows="6" size="10">{text}</textarea>'
        )


class TestMarkdownField(unittest.TestCase, TextTests):

    def setUp(self, *a, **k):
        TextTests.setUp(self, MarkdownField)
        self.show_css_class = 'textarea'
        self.display_template = '<p>{text}</p>'
        self.widget_template = (
            '<textarea class="{self.css_class}" cols="60" id="field1" '
            'name="field1" rows="6" '
            'size="10">{text}</textarea>'
        )
        self.widget_template = (
            '<textarea class="{self.css_class}" cols="60" id="field1" '
            'name="field1" rows="6" size="10">{text}</textarea>'
        )


class TestEditField(unittest.TestCase, TextTests):

    def setUp(self, *a, **k):
        TextTests.setUp(self, EditField)
        self.show_css_class = 'textarea'
        self.widget_template = (
            '<textarea class="{self.css_class}" height="6" '
            'id="field1" name="field1" size="10">{text}</textarea>'
        )


class TestTextField(unittest.TestCase, TextTests):

    def setUp(self, *a, **k):
        TextTests.setUp(self, TextField)
        self.widget_template = (
            '<input class="{self.css_class}" id="field1" '
            'maxlength="40" name="field1" size="40" '
            'type="text" value="{text}" />'
        )
