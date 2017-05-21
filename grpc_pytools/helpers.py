# -*- coding: utf-8 -*-

import itertools
import json
import re
from collections import OrderedDict


def slice_every(iterable, n, padding=False, padding_item=None):
    """Return a list with at most `n` items each time from the `iterable`."""
    iterable = iter(iterable)
    while True:
        piece = list(itertools.islice(iterable, n))
        if not piece:
            return
        padding_len = n - len(piece)
        if padding_len and padding:
            piece.extend([padding_item] * padding_len)
        yield piece


def underscore(word):
    """Make an underscored, lowercase form from the expression
    in the string.

    Borrowed from https://github.com/jpvanhal/inflection/blob/master/inflection.py
    """
    word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
    word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
    word = word.replace("-", "_")
    return word.lower()

    def has_enum_types(self):
        return bool(self.proto_ast['enums'])


def load_proto_ast(proto_ast_file):
    with open(proto_ast_file, 'r') as f:
        proto_ast = json.load(f)
    maps = dict(
        enums=OrderedDict([
            (enum['path'] + '.' + enum['name'], enum)
            for enum in proto_ast['enums']
        ]),
        messages=OrderedDict([
            (message['path'] + '.' + message['name'], message)
            for message in proto_ast['messages']
        ]),
    )
    return proto_ast, maps


def split_module_name(module_name):
    if '.' in module_name:
        path, name = module_name.rsplit('.', 1)
    else:
        path, name = '', module_name
    return path, name


def get_camel_case_full_name(proto_type):
    return ''.join(
        proto_type['path'].split('.')[2:] + [proto_type['name']]
    )
