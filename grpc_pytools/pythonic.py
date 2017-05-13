# -*- coding: utf-8 -*-

"""Generate a more Pythonic service for the gRPC service defined in the xx_pb2.py file.

Example:
    $ python -mgrpc_tools.pythonic --pb2-module-name='python.path.xx_pb2'
"""

import argparse
import itertools
import re
import sys
from collections import OrderedDict
from importlib import import_module

import grpc


class Generator(object):

    writer = sys.stdout

    def __init__(self, pb2_module_name, service_name, core_method_name,
                 unfold_method_args, rpc_method_args_size):
        self.pb2_module_name = pb2_module_name
        self.core_method_name = core_method_name
        self.unfold_method_args = unfold_method_args
        self.rpc_method_args_size = rpc_method_args_size

        if '.' in self.pb2_module_name:
            self.pb2_path, self.pb2_name = self.pb2_module_name.rsplit('.', 1)
        else:
            self.pb2_path, self.pb2_name = '', self.pb2_module_name

        self.proto_package_name = self.pb2_name[:-len('_pb2')]
        self.service_name = service_name or self.camelize(self.proto_package_name)
        self.stub_class_name = self.service_name + 'Stub'

        self.pb2_module = import_module(self.pb2_module_name)
        self.sym_db_pool = self.pb2_module._sym_db.pool

    @staticmethod
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

    def has_enum_types(self):
        return any(name.startswith(self.proto_package_name)
                   for name in self.sym_db_pool._enum_descriptors)

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
        for name, enum in self.sym_db_pool._enum_descriptors.iteritems():
            if name.startswith(self.proto_package_name):
                values = '\n'.join(
                    '    {name} = {number}'.format(name=value.name,
                                                   number=value.number)
                    for value in enum.values
                )
                self.writer.write(
                    '\n\n\nclass {enum_name}(enum.Enum):\n'
                    '{values}'.format(enum_name=enum.name, values=values)
                )

    def write_message_types(self):
        self.writer.write('\n\n')
        for name, message in self.sym_db_pool._descriptors.iteritems():
            if name.startswith(self.proto_package_name):
                self.writer.write(
                    '\n{name} = {pb2_name}.{name}'.format(
                        name=message.name,
                        pb2_name=self.pb2_name
                    )
                )

    def write_class_header(self):
        self.writer.write(
            '\n\n\nclass {}Service(object):\n'.format(self.service_name)
        )

    def write_class_constructor(self):
        self.writer.write(
            '\n    def __init__(self, target, timeout=10):'
            '\n        self.target = target'
            '\n        self.timeout = timeout\n'
        )

    def write_stub_property(self):
        self.writer.write(
            '\n    @property\n'
            '    def stub(self):\n'
            '        channel = grpc.insecure_channel(self.target)\n'
            '        return {pb2_name}.{stub_class_name}(channel)\n'.format(
                pb2_name=self.pb2_name,
                stub_class_name=self.stub_class_name
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
                underscored_method_name=self.underscore(method_name),
                req_name=self.underscore(req_name),
                core_method_name=self.core_method_name,
                method_name=method_name
            )
        )

    def write_unfolded_rpc_method(self, method_name, req_name, req_param_names):
        indented_header = '    def {}('.format(self.underscore(method_name))

        full_params = ['self'] + req_param_names
        args_size = self.rpc_method_args_size or len(full_params)
        separator = ',\n' + len(indented_header) * ' '
        indented_params = separator.join(
            ', '.join(params)
            for params in self.slice_every(full_params, args_size)
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

    def write_rpc_methods(self):
        stub_class = getattr(self.pb2_module, self.stub_class_name)

        channel = grpc.insecure_channel('localhost')
        stub = stub_class(channel)
        stub_method_names = [
            attr
            for attr in dir(stub)
            if not attr.startswith('__')
        ]
        stub_method_names.sort()
        stub_methods = OrderedDict([
            (stub_method_name, getattr(stub, stub_method_name))
            for stub_method_name in stub_method_names
        ])

        for stub_method_name, stub_method in stub_methods.iteritems():
            req_class = stub_method._request_serializer.im_class
            req_name = req_class.__name__
            req_param_names = [
                self.underscore(field.name)
                for field in req_class.DESCRIPTOR.fields
            ]
            if self.unfold_method_args:
                self.write_unfolded_rpc_method(stub_method_name, req_name,
                                               req_param_names)
            else:
                self.write_folded_rpc_method(stub_method_name, req_name)

    def generate(self):
        self.write_module_header()
        self.write_enum_types()
        self.write_message_types()
        self.write_class_header()
        self.write_class_constructor()
        self.write_stub_property()
        self.write_core_method()
        self.write_rpc_methods()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pb2-module-name', required=True,
                        help='The name of the generated `xx_pdb2.py` '
                             'module with the full Python path.')
    parser.add_argument('--service-name',
                        help='The name of the gRPC service.')
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
    generator = Generator(args.pb2_module_name,
                          args.service_name,
                          args.core_method_name,
                          args.unfold_method_args,
                          args.rpc_method_args_size)
    generator.generate()


if __name__ == '__main__':
    main()
