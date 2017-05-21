# -*- coding: utf-8 -*-

"""Generate marshmallow schemas for all gRPC messages defined in the xx_pb2.py file.

Usage:
    $ python -m grpc_pytools.marshmallow -h

Example:
    $ python -m grpc_pytools.marshmallow --proto-ast-file=/path/to/xx_ast.json --pb2-module-name=python.path.to.xx_pb2
"""

import argparse
import sys

from . import helpers


TYPES_GRPC_TO_MARSHMALLOW = {
    'TYPE_UNKNOWN': '',
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
    'TYPE_BYTES': 'String',
    'TYPE_UINT32': 'Integer',
    'TYPE_ENUM': 'Integer',
    'TYPE_SFIXED32': 'Integer',
    'TYPE_SFIXED64': 'Integer',
    'TYPE_SINT32': 'Integer',
    'TYPE_SINT64': 'Integer',
}


class Generator(object):

    writer = sys.stdout

    def __init__(self, proto_ast_file, pb2_module_name):
        self.proto_ast, self.ast_maps = helpers.load_proto_ast(proto_ast_file)
        self.pb2_path, self.pb2_name = helpers.split_module_name(
            pb2_module_name)

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
        for message in self.proto_ast['messages']:
            self.writer.write(
                '\n{name} = {pb2_name}.{name}'.format(
                    name=message['name'],
                    pb2_name=self.pb2_name
                )
            )

    def write_marshmallow_shemas(self):
        for message in self.proto_ast['messages']:
            self.writer.write(
                '\n\n\nclass {name}Schema(Schema):\n'.format(
                    name=message['name']
                )
            )
            for field in message['fields']:
                type = TYPES_GRPC_TO_MARSHMALLOW[field['type']]
                label = field['label']
                fixed = 'fields.' + type
                if type == 'Nested':
                    nested_type = self.ast_maps['messages'][field['type_name']]
                    params = ["'{}Schema'".format(nested_type['name'])]
                    if label == 'LABEL_REQUIRED':
                        params.append('required=True')
                    elif label == 'LABEL_REPEATED':
                        params.append('many=True')
                    value = '{fixed}({params})'.format(
                        fixed=fixed,
                        params=', '.join(params)
                    )
                else:
                    if label == 'LABEL_REQUIRED':
                        value = fixed + '(many=True)'
                    elif label == 'LABEL_REPEATED':
                        value = 'fields.List({fixed}())'.format(fixed=fixed)
                    else:
                        value = fixed + '()'
                self.writer.write(
                    '    {name} = {value}\n'.format(
                        name=field['name'],
                        value=value
                    )
                )
            self.writer.write(
                '\n    @post_load\n'
                '    def make_{underscored_name}(self, data):\n'
                '        return {name}(**data)'.format(
                    name=message['name'],
                    underscored_name=helpers.underscore(message['name'])
                )
            )

    def generate(self):
        self.write_module_header()
        self.write_message_types()
        self.write_marshmallow_shemas()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proto-ast-file', required=True,
                        help='The path of the AST-like JSON file.')
    parser.add_argument('--pb2-module-name', required=True,
                        help='The name of the generated `xx_pb2.py` '
                             'module with the full Python path.')
    args = parser.parse_args()
    generator = Generator(args.proto_ast_file, args.pb2_module_name)
    generator.generate()


if __name__ == '__main__':
    main()
