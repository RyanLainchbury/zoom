"""
    zoom.component

    Components encapsulate all of the parts that are required to make a
    component appear on a page.  This can include HTML, CSS and Javascript
    parts and associated libraries.

    Components parts are assembled in the way that kind of part
    needs to be treated.  For example HTML parts are simply joined
    together in order and returned.  CSS parts on the other hand are
    joined together but any duplicate parts are ignored.

    When a caller supplies JS or CSS as part of the component being assembled
    these extra parts are submitted to the system to be included in thier
    proper place within a response (typically a page template).

    The Component object is currently experimental and is intended to be used
    in future releases.
"""

import logging
import threading

from zoom.utils import OrderedSet, pp

# TODO: rename this to context (or system?)
composition = threading.local()


class Component(object):
    """component of a page response

    >>> c = Component()
    >>> c
    <Component: {'html': []}>

    >>> c += 'test'
    >>> c
    <Component: {'html': ['test']}>

    >>> c += dict(css='mycss')
    >>> c
    <Component: {'css': OrderedSet(['mycss']), 'html': ['test']}>

    >>> c += dict(css='mycss')
    >>> c
    <Component: {'css': OrderedSet(['mycss']), 'html': ['test']}>

    >>> c += 'test2'
    >>> sorted(c.parts.items())
    [('css', OrderedSet(['mycss'])), ('html', ['test', 'test2'])]

    >>> Component() + 'test1' + 'test2'
    <Component: {'html': ['test1', 'test2']}>

    >>> Component() + 'test1' + dict(css='mycss')
    <Component: {'css': OrderedSet(['mycss']), 'html': ['test1']}>

    >>> Component('test1', Component('test2'))
    <Component: {'html': ['test1', 'test2']}>

    >>> Component(
    ...    Component('test1', css='css1'),
    ...    Component('test2', Component('test3', css='css3')),
    ... )
    <Component: {'css': OrderedSet(['css1', 'css3']), 'html': ['test1', 'test2', 'test3']}>

    >>> Component((Component('test1', css='css1'), Component('test2', css='css2')))
    <Component: {'css': OrderedSet(['css1', 'css2']), 'html': ['test1', 'test2']}>

    >>> Component(Component('test1', css='css1'), Component('test2', css='css2'))
    <Component: {'css': OrderedSet(['css1', 'css2']), 'html': ['test1', 'test2']}>

    >>> composition.parts = Component()
    >>> c = Component(Component('test1', css='css1'), Component('test2', css='css2'))
    >>> c.render()
    'test1test2'

    >>> page2 = \\
    ...    Component() + \\
    ...    '<h1>Title</h1>' + \\
    ...    dict(css='mycss') + \\
    ...    dict(js='myjs') + \\
    ...    'page body goes here'
    >>> t = (
    ...    "<Component: {'css': OrderedSet(['mycss']), "
    ...    "'html': ['<h1>Title</h1>', 'page body goes here'], "
    ...    "'js': OrderedSet(['myjs'])}>"
    ... )
    >>> #print(repr(page2) + '\\n' + t)
    >>> repr(page2) == t
    True
    """
    # pylint: disable=too-few-public-methods

    def __init__(self, *args, **kwargs):
        """construct a Component

        >>> Component()
        <Component: {'html': []}>

        >>> Component('body')
        <Component: {'html': ['body']}>

        >>> Component('body', css='css1')
        <Component: {'css': OrderedSet(['css1']), 'html': ['body']}>

        >>> t = Component('body', css='css1', js='js1')
        >>> repr(t) == (
        ...     "<Component: {"
        ...     "'css': OrderedSet(['css1']), "
        ...     "'html': ['body'], "
        ...     "'js': OrderedSet(['js1'])"
        ...     "}>"
        ... )
        True
        """

        def is_iterable(obj):
            """Returns True if object is an iterable but not a string"""
            return hasattr(obj, '__iter__') and not isinstance(obj, str)

        def flatten(items):
            """Returns list of items with sublists incorporated into list"""
            items_as_iterables = list(is_iterable(i) and i or (i,) for i in items)
            return [i for j in items_as_iterables for i in j]

        self.parts = {
            'html': [],
        }
        for arg in flatten(args):
            self += arg
        self += kwargs

    def __iadd__(self, other):
        """add something to a component

        >>> page = Component('<h1>Title</h1>')
        >>> page += dict(css='mycss')
        >>> page += 'page body goes here'
        >>> page += dict(js='myjs')
        >>> result = (
        ...     "<Component: {"
        ...     "'css': OrderedSet(['mycss']), "
        ...     "'html': ['<h1>Title</h1>', 'page body goes here'], "
        ...     "'js': OrderedSet(['myjs'])"
        ...     "}>"
        ... )
        >>> #print(page)
        >>> #print(result)
        >>> result == repr(page)
        True

        >>> page = Component('test')
        >>> page += dict(html='text')
        >>> page
        <Component: {'html': ['test', 'text']}>

        """
        def rendered(obj):
            """call the render method if necessary"""
            if not isinstance(obj, Component) and hasattr(obj, 'render'):
                return obj.render()
            return obj

        other = rendered(other)

        if isinstance(other, str):
            self.parts['html'].append(other)
        elif isinstance(other, dict):
            for key, value in other.items():
                part = self.parts.setdefault(key, OrderedSet())
                if key == 'html':
                    if isinstance(value, list):
                        part.extend(value)
                    else:
                        part.append(value)
                else:
                    if isinstance(value, list):
                        part |= value
                    else:
                        part |= [value]
        elif isinstance(other, Component):
            for key, value in other.parts.items():
                part = self.parts.setdefault(key, OrderedSet())
                if key == 'html':
                    part.extend(value)
                else:
                    part |= value
        return self

    def __add__(self, other):
        """add a component to something else

        >>> (Component() + 'test1' + dict(css='mycss')) + 'test2'
        <Component: {'css': OrderedSet(['mycss']), 'html': ['test1', 'test2']}>

        >>> Component() + 'test1' + dict(css='mycss') + dict(css='css2')
        <Component: {'css': OrderedSet(['mycss', 'css2']), 'html': ['test1']}>
        """
        result = Component()
        result += self
        result += other
        return result

    def __repr__(self):
        return '<Component: {{{}}}>'.format(
            ', '.join(
                '{!r}: {!r}'.format(i, j)
                for i, j in sorted(self.parts.items())
            )
        )

    def render(self):
        """renders the component"""
        composition.parts += self
        return ''.join(self.parts['html'])

    def __str__(self):
        return self.render()


component = Component


def compose(*args, **kwargs):
    """Compose a response - DEPRECATED"""
    composition.parts += component(**kwargs)
    return ''.join(args)


def handler(request, handler, *rest):
    """Component handler"""

    pop = request.session.__dict__.pop

    composition.parts = Component(
        success=pop('system_successes', []),
        warning=pop('system_warnings', []),
        error=pop('system_errors', []),
    )

    result = handler(request, *rest)

    logger = logging.getLogger(__name__)
    logger.debug('component middleware')

    # TODO: clean this up, use a single alerts list with an alert type value
    success_alerts = composition.parts.parts.get('success')
    if success_alerts:
        if not hasattr(request.session, 'system_successes'):
            request.session.system_successes = []
        request.session.system_successes = list(success_alerts)

    warning_alerts = composition.parts.parts.get('warning')
    if warning_alerts:
        if not hasattr(request.session, 'system_warnings'):
            request.session.system_warnings = []
        request.session.system_warnings = list(warning_alerts)

    error_alerts = composition.parts.parts.get('error')
    if error_alerts:
        if not hasattr(request.session, 'system_errors'):
            request.session.system_errors = []
        request.session.system_errors = list(error_alerts)

    return result

# def component(*args, **kwargs):
#     """assemble parts of a component
#
#     >>> system.setup()
#     >>> system.css
#     OrderedSet()
#
#     >>> component('test', css='mycss')
#     'test'
#     >>> system.css
#     OrderedSet(['mycss'])
#
#     >>> component(100, css='mycss')
#     '100'
#
#     >>> component(css='mycss', html='test')
#     'test'
#     >>> system.css
#     OrderedSet(['mycss'])
#
#     >>> component('test', html='more', css='mycss')
#     'testmore'
#     >>> system.css
#     OrderedSet(['mycss'])
#
#     >>> component('test', 'two', css=['mycss','css2'], js='myjs')
#     'testtwo'
#     >>> system.css
#     OrderedSet(['mycss', 'css2'])
#     >>> system.js
#     OrderedSet(['myjs'])
#
#     >>> component('test', js='js2')
#     'test'
#     >>> system.js
#     OrderedSet(['myjs', 'js2'])
#
#     >>> component(['test1'], ('test2',), 'test3')
#     'test1test2test3'
#
#     >>> from mvc import DynamicView
#     >>> class MyThing(DynamicView):
#     ...     def __str__(self):
#     ...         return self.model
#     >>> hasattr(MyThing('test'), '__iter__')
#     False
#     >>> component(['test1'], ('test2',), 'test3', MyThing('test4'))
#     'test1test2test3test4'
#     >>> component(MyThing('test4'))
#     'test4'
#     >>> component(MyThing('test4'), MyThing('test5'))
#     'test4test5'
#     >>> component((MyThing('test4'), MyThing('test5')))
#     'test4test5'
#     >>> args = (MyThing('test4'), MyThing('test5'))
#     >>> component(args)
#     'test4test5'
#     >>> component(*list(args))
#     'test4test5'
#
#     >>> system.setup()
#     >>> component('test', js=[])
#     'test'
#     >>> system.js
#     OrderedSet()
#     """
#     def is_iterable(item):
#         return hasattr(item, '__iter__')
#
#     def as_iterable(item):
#         return not is_iterable(item) and (item,) or item
#
#     def flatten(items):
#         items_as_iterables = list(is_iterable(i) and i or (i,) for i in items)
#         return [i for j in items_as_iterables for i in j]
#
#     parts = {
#         'html': flatten(args),
#     }
#     for key, value in kwargs.items():
#         part = parts.setdefault(key, OrderedSet())
#         if key == 'html':
#             part.extend(as_iterable(value))
#         else:
#             part |= OrderedSet(as_iterable(value))
#     for key in ['css', 'js', 'styles', 'libs', 'head', 'tail']:
#         part = getattr(system, key)
#         part |= parts.get(key, [])
#     return ''.join(map(str, parts['html']))
