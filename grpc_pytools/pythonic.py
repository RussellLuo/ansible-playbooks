# -*- coding: utf-8 -*-

"""Generate more Pythonic services for all gRPC services defined in the .proto file.

Usage:
    $ python -m grpc_pytools.pythonic -h

Example:
    $ python -m grpc_pytools.pythonic --proto-ast-file=/path/to/xx_ast.json --pb2-module-name=python.path.to.xx_pb2
"""

import argparse
import sys

from . import helpers


class Generator(object):

    writer = sys.stdout

    def __init__(self, proto_ast_file, pb2_module_name, core_method_name,
                 unfold_method_args, rpc_method_args_size):
        self.proto_ast, self.ast_maps = helpers.load_proto_ast(proto_ast_file)
        self.core_method_name = core_method_name
        self.unfold_method_args = unfold_method_args
        self.rpc_method_args_size = rpc_method_args_size

        self.pb2_path, self.pb2_name = helpers.split_module_name(
            pb2_module_name)

    def has_enum_types(self):
        return bool(self.proto_ast['enums'])

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
            '{import_enum}'
            '\nimport grpc'
            '\n\n{import_pb2}'.format(
                import_enum='\nimport enum' if self.has_enum_types() else '',
                import_pb2=import_pb2
            )
        )

    def write_enum_types(self):
        for enum in self.proto_ast['enums']:
            values = '\n'.join(
                '    {name} = {number}'.format(**value)
                for value in enum['values']
            )
            self.writer.write(
                '\n\n\nclass {enum_name}(enum.Enum):\n'
                '{values}'.format(enum_name=enum['name'], values=values)
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

    def write_class_header(self, service_class_name):
        self.writer.write(
            '\n\n\nclass {}(object):\n'.format(service_class_name)
        )

    def write_class_constructor(self):
        self.writer.write(
            '\n    def __init__(self, target, timeout=10):'
            '\n        self.target = target'
            '\n        self.timeout = timeout\n'
        )

    def write_stub_property(self, stub_class_name):
        self.writer.write(
            '\n    @property\n'
            '    def stub(self):\n'
            '        channel = grpc.insecure_channel(self.target)\n'
            '        return {pb2_name}.{stub_class_name}(channel)\n'.format(
                pb2_name=self.pb2_name,
                stub_class_name=stub_class_name
            )
        )

    def write_core_method(self):
        self.writer.write(
            '\n    def {core_method_name}(self, rpc_name, req):\n'
            '        rpc = getattr(self.stub, rpc_name)\n'
            '        resp = rpc(req, self.timeout)\n'
            '        return resp\n'.format(
                core_method_name=self.core_method_name,
                pb2_name=self.pb2_name
            )
        )

    def write_folded_rpc_method(self, method_name, req_name):
        self.writer.write(
            "\n    def {underscored_method_name}(self, {req_name}):\n"
            "        resp = self.{core_method_name}('{method_name}', {req_name})\n"
            "        return resp\n".format(
                underscored_method_name=helpers.underscore(method_name),
                req_name=helpers.underscore(req_name),
                core_method_name=self.core_method_name,
                method_name=method_name
            )
        )

    def write_unfolded_rpc_method(self, method_name, req_name, req_param_names):
        indented_header = '    def {}('.format(helpers.underscore(method_name))

        full_params = ['self'] + req_param_names
        args_size = self.rpc_method_args_size or len(full_params)
        separator = ',\n' + len(indented_header) * ' '
        indented_params = separator.join(
            ', '.join(params)
            for params in helpers.slice_every(full_params, args_size)
        )

        indented_kwargs = ',\n'.join(
            '            {0}={0}'.format(param_name)
            for param_name in req_param_names
        )
        indented_body = (
            "        req = {req_name}(\n"
            "{indented_kwargs}\n"
            "        )\n"
            "        resp = self.{core_method_name}('{method_name}', req)\n"
            "        return resp\n".format(
                req_name=req_name,
                indented_kwargs=indented_kwargs,
                core_method_name=self.core_method_name,
                method_name=method_name
            )
        )
        self.writer.write(
            '\n{indented_header}'
            '{indented_params}):\n'
            '{indented_body}'.format(
                indented_header=indented_header,
                indented_params=indented_params,
                indented_body=indented_body
            )
        )

    def write_rpc_methods(self, methods):
        for method in methods:
            req_type = self.ast_maps['messages'][method['input_type']]
            if self.unfold_method_args:
                req_param_names = [
                    helpers.underscore(field['name'])
                    for field in req_type['fields']
                ]
                self.write_unfolded_rpc_method(method['name'], req_type['name'],
                                               req_param_names)
            else:
                self.write_folded_rpc_method(method['name'], req_type['name'])

    def write_service_class(self, service):
        self.write_class_header(service['name'] + 'Service')
        self.write_class_constructor()
        self.write_stub_property(service['name'] + 'Stub')
        self.write_core_method()
        self.write_rpc_methods(service['methods'])

    def generate(self):
        self.write_module_header()
        self.write_enum_types()
        self.write_message_types()
        for service in self.proto_ast['services']:
            self.write_service_class(service)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proto-ast-file', required=True,
                        help='The path of the AST-like JSON file.')
    parser.add_argument('--pb2-module-name', required=True,
                        help='The name of the generated `xx_pb2.py` '
                             'module with the full Python path.')
    parser.add_argument('--core-method-name', default='call_rpc',
                        help='The name of the core method that will be '
                             'used to call the actual rpc methods.')
    parser.add_argument('--unfold-method-args', action='store_true',
                        help='Whether or not to unfold the request '
                             'attributes as the arguments of each rpc method.')
    parser.add_argument('--rpc-method-args-size', type=int, default=0,
                        help='The number of arguments per line in the '
                             'definition of each rpc method.')
    args = parser.parse_args()
    generator = Generator(args.proto_ast_file,
                          args.pb2_module_name,
                          args.core_method_name,
                          args.unfold_method_args,
                          args.rpc_method_args_size)
    generator.generate()


if __name__ == '__main__':
    main()
