# -*- coding: utf-8 -*-

"""Generate marshmallow schemas for all gRPC messages defined in the xx_pb2.py file.

Example:
    $ python -mgrpc_tools.marshmallow --pb2-module-name='python.path.xx_pb2'
"""

import argparse
import re
import sys
from collections import OrderedDict
from importlib import import_module


GRPC_TYPES_TO_MARSHMALLOW_TYPES = {
    'TYPE_DOUBLE': 'Float',
    'TYPE_FLOAT': 'Float',
    'TYPE_INT64': 'Integer',
    'TYPE_UINT64': 'Integer',
    'TYPE_INT32': 'Integer',
    'TYPE_FIXED64': 'Integer',
    'TYPE_FIXED32': 'Integer',
    'TYPE_BOOL': 'Boolean',
    'TYPE_STRING': 'String',
    'TYPE_GROUP': '',
    'TYPE_MESSAGE': 'Nested',
    'TYPE_BYTES': '',
    'TYPE_UINT32': 'Integer',
    'TYPE_ENUM': 'Integer',
    'TYPE_SFIXED32': 'Integer',
    'TYPE_SFIXED64': 'Integer',
    'TYPE_SINT32': 'Integer',
    'TYPE_SINT64': 'Integer',
}

GRPC_LABELS_MAP = {
    1: 'optional',
    2: 'required',
    3: 'repeated',
}


class Generator(object):

    writer = sys.stdout

    def __init__(self, pb2_module_name):
        self.pb2_module_name = pb2_module_name

        if '.' in self.pb2_module_name:
            self.pb2_path, self.pb2_name = self.pb2_module_name.rsplit('.', 1)
        else:
            self.pb2_path, self.pb2_name = '', self.pb2_module_name

        self.pb2_module = import_module(self.pb2_module_name)
        self.sym_db_pool = self.pb2_module._sym_db.pool

        proto_package_name = self.pb2_name[:-len('_pb2')]
        self.message_types = OrderedDict((
            (name, message)
            for name, message in self.sym_db_pool._descriptors.iteritems()
            if name.startswith(proto_package_name)
        ))

        any_message = self.message_types.itervalues().next()
        any_field = any_message.fields[0]
        self.grpc_type_nums_to_marshmallow_type_names = {
            getattr(any_field, name): GRPC_TYPES_TO_MARSHMALLOW_TYPES[name]
            for name in dir(any_field)
            if name.startswith('TYPE_')
        }

    @staticmethod
    def camelize(string, uppercase_first_letter=True):
        """Convert strings to CamelCase.

        Borrowed from https://github.com/jpvanhal/inflection/blob/master/inflection.py
        """
        if uppercase_first_letter:
            return re.sub(r"(?:^|_)(.)", lambda m: m.group(1).upper(), string)
        else:
            return string[0].lower() + Generator.camelize(string)[1:]

    @staticmethod
    def underscore(word):
        """Make an underscored, lowercase form from the expression
        in the string.

        Borrowed from https://github.com/jpvanhal/inflection/blob/master/inflection.py
        """
        word = re.sub(r"([A-Z]+)([A-Z][a-z])", r'\1_\2', word)
        word = re.sub(r"([a-z\d])([A-Z])", r'\1_\2', word)
        word = word.replace("-", "_")
        return word.lower()

    def write_module_header(self):
        if self.pb2_path:
            import_pb2 = 'from {pb2_path} import {pb2_name}'.format(
                pb2_path=self.pb2_path,
                pb2_name=self.pb2_name
            )
        else:
            import_pb2 = 'import {pb2_name}'.format(pb2_name=self.pb2_name)
        self.writer.write(
            '# -*- coding: utf-8 -*-\n'
            '\nfrom marshmallow import Schema, fields, post_load'
            '\n\n{import_pb2}'.format(import_pb2=import_pb2)
        )

    def write_message_types(self):
        self.writer.write('\n\n')
        for name, message in self.message_types.iteritems():
            self.writer.write(
                '\n{name} = {pb2_name}.{name}'.format(
                    name=message.name,
                    pb2_name=self.pb2_name
                )
            )

    def write_marshmallow_shemas(self):
        for name, message in self.message_types.iteritems():
            self.writer.write(
                '\n\n\nclass {name}Schema(Schema):\n'.format(
                    name=message.name
                )
            )
            for field in message.fields:
                type_ = self.grpc_type_nums_to_marshmallow_type_names[field.type]
                option = GRPC_LABELS_MAP[field.label]
                fixed = 'fields.' + type_
                if type_ == 'Nested':
                    params = ["'{}Schema'".format(field.message_type.name)]
                    if option == 'required':
                        params.append('required=True')
                    elif option == 'repeated':
                        params.append('many=True')
                    value = '{fixed}({params})'.format(
                        fixed=fixed,
                        params=', '.join(params)
                    )
                else:
                    if option == 'required':
                        value = fixed + '(many=True)'
                    elif option == 'repeated':
                        value = 'fields.List({fixed}())'.format(fixed=fixed)
                    else:
                        value = fixed + '()'
                self.writer.write(
                    '    {name} = {value}\n'.format(name=field.name, value=value)
                )
            self.writer.write(
                '\n    @post_load\n'
                '    def make_{underscored_name}(self, data):\n'
                '        return {name}(**data)'.format(
                    name=message.name,
                    underscored_name=self.underscore(message.name)
                )
            )

    def generate(self):
        self.write_module_header()
        self.write_message_types()
        self.write_marshmallow_shemas()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pb2-module-name', required=True,
                        help='The name of the generated `xx_pdb2.py` '
                             'module with the full Python path.')
    args = parser.parse_args()
    generator = Generator(args.pb2_module_name)
    generator.generate()


if __name__ == '__main__':
    main()
