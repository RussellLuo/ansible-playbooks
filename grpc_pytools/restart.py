# -*- coding: utf-8 -*-

"""Generate simple RESTArt APIs for all gRPC methods defined in the xx_pb2.py file.

Usage:
    $ python -m grpc_pytools.restart -h

Example:
    $ python -m grpc_pytools.restart --proto-ast-file=/path/to/xx_ast.json --pb2-module-name=python.path.to.xx_pb2 --grpc-server=localhost:50051
"""

import argparse
import sys

from . import helpers


HEADER = '''# -*- coding: utf-8 -*-

from restart.api import RESTArt
from restart.exceptions import BadRequest, InternalServerError
from restart.parsers import JSONParser
from restart.renderers import JSONRenderer
from restart.resource import Resource

import schemas
import services

api = RESTArt()
{service_definitions}


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
        serialized = resource.resp_schema.dump(data)
        if serialized.errors:
            raise InternalServerError(serialized.errors)
        return super(GRPCMessageRenderer, self).render(
            serialized.data, context)


class GRPCResource(Resource):
    parser_classes = (GRPCMessageParser,)
    renderer_classes = (GRPCMessageRenderer,)
'''


RESOURCE = '''@api.route(uri='/{underscored_service_name}/{underscored_method_name}', methods=['POST'])
class {method_name}(GRPCResource):
    name = '{underscored_service_name}.{underscored_method_name}'
    req_schema = schemas.{req_name}Schema()
    resp_schema = schemas.{resp_name}Schema()

    def create(self, request):
        return {underscored_service_name}.{underscored_method_name}(request.data)
'''


class Generator(object):

    writer = sys.stdout

    def __init__(self, proto_ast_file, pb2_module_name, grpc_server):
        self.proto_ast, self.ast_maps = helpers.load_proto_ast(proto_ast_file)
        self.pb2_path, self.pb2_name = helpers.split_module_name(
            pb2_module_name)
        self.grpc_server = grpc_server

    def write_module_header(self, services):
        service_definitions = '\n'.join([
            "{service_name} = services.{service_class_name}('{target}')".format(
                service_name=helpers.underscore(service['name']),
                service_class_name=service['name'],
                target=self.grpc_server
            )
            for service in services
        ])
        self.writer.write(HEADER.format(
            service_definitions=service_definitions
        ))

    def write_rpc_resources(self, service):
        for method in service['methods']:
            req_name = self.ast_maps['messages'][method['input_type']]['name']
            resp_name = self.ast_maps['messages'][method['output_type']]['name']
            self.writer.write('\n\n' + RESOURCE.format(
                underscored_service_name=helpers.underscore(service['name']),
                underscored_method_name=helpers.underscore(method['name']),
                method_name=method['name'],
                req_name=req_name,
                resp_name=resp_name
            ))

    def generate(self):
        services = self.proto_ast['services']
        self.write_module_header(services)
        for service in services:
            self.write_rpc_resources(service)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--proto-ast-file', required=True,
                        help='The path of the AST-like JSON file.')
    parser.add_argument('--pb2-module-name', required=True,
                        help='The name of the generated `xx_pb2.py` '
                             'module with the full Python path.')
    parser.add_argument('--grpc-server', required=True,
                        help='The host and port of gRPC server (in '
                             'the form of "host:port").')
    args = parser.parse_args()
    generator = Generator(args.proto_ast_file,
                          args.pb2_module_name,
                          args.grpc_server)
    generator.generate()


if __name__ == '__main__':
    main()
