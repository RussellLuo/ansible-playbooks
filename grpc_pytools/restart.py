# -*- coding: utf-8 -*-

"""Generate simple RESTArt APIs for all gRPC methods defined in the xx_pb2.py file.

Example:
    $ python -mgrpc_pytools.restart --pb2-module-name='python.path.xx_pb2' --grpc-server='localhost:50051'
"""

import argparse
import re
import sys
from collections import OrderedDict
from importlib import import_module

import grpc


HEADER = '''# -*- coding: utf-8 -*-

from restart.api import RESTArt
from restart.exceptions import BadRequest, InternalServerError
from restart.parsers import JSONParser
from restart.renderers import JSONRenderer
from restart.resource import Resource

import schemas
import service

api = RESTArt()
service = service.{service_name}Service('{target}')


class GRPCMessageParser(JSONParser):
    """Deserialize JSON to gRPC message object."""

    def parse(self, stream, content_type, content_length, context=None):
        resource = context['resource']
        data = super(GRPCMessageParser, self).parse(
            stream, content_type, content_length, context)
        deserialized = resource.req_schema.load(data)
        if deserialized.errors:
            raise BadRequest(deserialized.errors)
        return deserialized.data


class GRPCMessageRenderer(JSONRenderer):
    """Serialize gRPC message object to JSON."""

    def render(self, data, context=None):
        resource = context['resource']
        serialized = resource.resp_schema.dumps(data)
        if serialized.errors:
            raise InternalServerError(serialized.errors)
        return super(GRPCMessageRenderer, self).render(
            serialized.data, context)


class GRPCResource(Resource):
    parser_classes = (GRPCMessageParser,)
    renderer_classes = (GRPCMessageRenderer,)
'''


RESOURCE = '''@api.route(methods=['POST'])
class {method_name}(GRPCResource):
    name = '{underscored_method_name}'
    req_schema = schemas.{req_name}Schema()
    resp_schema = schemas.{resp_name}Schema()

    def create(self, request):
        return service.{underscored_method_name}(request.data)
'''


class Generator(object):

    writer = sys.stdout

    def __init__(self, pb2_module_name, grpc_server, service_name):
        self.pb2_module_name = pb2_module_name
        self.grpc_server = grpc_server

        if '.' in self.pb2_module_name:
            self.pb2_path, self.pb2_name = self.pb2_module_name.rsplit('.', 1)
        else:
            self.pb2_path, self.pb2_name = '', self.pb2_module_name

        self.pb2_module = import_module(self.pb2_module_name)
        self.sym_db_pool = self.pb2_module._sym_db.pool

        proto_package_name = self.pb2_name[:-len('_pb2')]
        self.service_name = service_name or self.camelize(proto_package_name)

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
        self.writer.write(HEADER.format(
            service_name=self.service_name,
            target=self.grpc_server
        ))

    def write_rpc_resources(self):
        stub_class = getattr(self.pb2_module, self.service_name + 'Stub')

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
            # Yes, it is tricky...
            req_name = stub_method._request_serializer.im_class.__name__
            resp_name = stub_method._response_deserializer.func_closure[0].cell_contents.__name__
            self.writer.write('\n\n' + RESOURCE.format(
                method_name=stub_method_name,
                underscored_method_name=self.underscore(stub_method_name),
                req_name=req_name,
                resp_name=resp_name
            ))

    def generate(self):
        self.write_module_header()
        self.write_rpc_resources()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pb2-module-name', required=True,
                        help='The name of the generated `xx_pdb2.py` '
                             'module with the full Python path.')
    parser.add_argument('--grpc-server', required=True,
                        help='The host and port of gRPC server (in '
                             'the form of "host:port").')
    parser.add_argument('--service-name',
                        help='The name of the gRPC service.')
    args = parser.parse_args()
    generator = Generator(args.pb2_module_name,
                          args.grpc_server,
                          args.service_name)
    generator.generate()


if __name__ == '__main__':
    main()
