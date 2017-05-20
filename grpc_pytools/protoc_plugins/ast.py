# -*- coding: utf-8 -*-

import json
import os
import sys

from .generator import Generator


class ASTGenerator(Generator):
    """A generator that generates an AST-like JSON file from a .proto file."""

    def _make_enum(self, enum):
        return dict(
            name=enum.name,
            values=[
                dict(
                    name=value.name,
                    number=value.number
                )
                for value in enum.value
            ]
        )

    def _make_message(self, message):
        return dict(
            name=message.name,
            fields=[
                dict(
                    type=self._types_map[field.type].name,
                    type_name=field.type_name,
                    name=field.name,
                    label=self._labels_map[field.label].name,
                    number=field.number
                )
                for field in message.field
            ],
            enum_types=[t.name for t in message.enum_type],
            nested_types=[t.name for t in message.nested_type]
        )

    def _walk_message(self, message):
        yield 'message', message

        for enum in message.enum_type:
            yield 'enum', enum

        for nested in message.nested_type:
            for type, item in self._walk_message(nested):
                yield type, item

    def _make_data(self, proto_file):
        # Toplevel info
        data = dict(
            name=proto_file.name,
            syntax=proto_file.syntax,
            package=proto_file.package,
        )

        # Enum info
        enums = [
            self._make_enum(enum)
            for enum in proto_file.enum_type
        ]
        data['enums'] = enums

        # Message info
        messages = []
        for message in proto_file.message_type:
            for type, item in self._walk_message(message):
                if type == 'enum':
                    enums.append(self._make_enum(item))
                elif type == 'message':
                    messages.append(self._make_message(item))
        data['messages'] = messages

        # Service info
        data['services'] = [
            dict(
                name=service.name,
                methods=[
                    dict(
                        name=method.name,
                        input_type=method.input_type,
                        output_type=method.output_type
                    )
                    for method in service.method
                ]
            )
            for service in proto_file.service
        ]

        return data

    def _make_file(self, proto_file):
        data = self._make_data(proto_file)
        name = (
            os.path.splitext(os.path.basename(proto_file.name))[0]
            + '_ast.json'
        )
        content = json.dumps(data, indent=2)
        return name, content


def main():
    ASTGenerator(sys.stdin, sys.stdout).generate()


if __name__ == '__main__':
    main()
