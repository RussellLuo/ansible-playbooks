# -*- coding: utf-8 -*-

import sys

from enum import Enum

from google.protobuf.compiler import plugin_pb2 as plugin


IS_PY3 = sys.version_info > (3,)


class ProtoType(Enum):
    TYPE_UNKNOWN = 0
    TYPE_DOUBLE = 1
    TYPE_FLOAT = 2
    TYPE_INT64 = 3
    TYPE_UINT64 = 4
    TYPE_INT32 = 5
    TYPE_FIXED64 = 6
    TYPE_FIXED32 = 7
    TYPE_BOOL = 8
    TYPE_STRING = 9
    TYPE_GROUP = 10
    TYPE_MESSAGE = 11
    TYPE_BYTES = 12
    TYPE_UINT32 = 13
    TYPE_ENUM = 14
    TYPE_SFIXED32 = 15
    TYPE_SFIXED64 = 16
    TYPE_SINT32 = 17
    TYPE_SINT64 = 18


class ProtoLabel(Enum):
    LABEL_OPTIONAL = 1
    LABEL_REQUIRED = 2
    LABEL_REPEATED = 3


class Generator(object):
    """The base generator for implementing a protoc plugin."""

    reader = sys.stdin.buffer if IS_PY3 else sys.stdin
    writer = sys.stdout.buffer if IS_PY3 else sys.stdout

    _types_map = ProtoType._value2member_map_
    _labels_map = ProtoLabel._value2member_map_

    def _parse(self, data):
        request = plugin.CodeGeneratorRequest()
        request.ParseFromString(data)
        return request

    def _serialize(self, response):
        return response.SerializeToString()

    def _add_data(self, response, proto_file):
        raise NotImplementedError

    def _generate(self, request):
        response = plugin.CodeGeneratorResponse()
        for proto_file in request.proto_file:
            name, content = self._make_file(proto_file)
            f = response.file.add()
            f.name = name
            f.content = content
        return response

    def generate(self):
        input = self.reader.read()
        request = self._parse(input)
        response = self._generate(request)
        output = self._serialize(response)
        self.writer.write(output)
