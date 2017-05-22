# -*- coding: utf-8 -*-

import json
import os

from .generator import Generator


class ASTGenerator(Generator):
    """A generator that generates an AST-like JSON file from a .proto file."""

    def _make_enum(self, path, enum):
        return dict(
            path=path,
            name=enum.name,
            values=[
                dict(
                    name=value.name,
                    number=value.number
                )
                for value in enum.value
            ]
        )

    def _make_message(self, path, message):
        def make_path(name):
            return path + '.' + message.name + '.' + name

        return dict(
            path=path,
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
            nested_enums=[make_path(t.name) for t in message.enum_type],
            nested_messages=[make_path(t.name) for t in message.nested_type]
        )

    def _walk_message(self, path, message):
        yield 'message', path, message

        nested_path = path + '.' + message.name

        for enum in message.enum_type:
            yield 'enum', nested_path, enum

        for nested in message.nested_type:
            for type, path, item in self._walk_message(nested_path, nested):
                yield type, path, item

    def _make_data(self, proto_file):
        # Toplevel info
        data = dict(
            name=proto_file.name,
            syntax=proto_file.syntax,
            package=proto_file.package,
        )

        base_path = '.' + proto_file.package

        # Enum info
        enums = [
            self._make_enum(base_path, enum)
            for enum in proto_file.enum_type
        ]
        data['enums'] = enums

        # Message info
        messages = []
        for message in proto_file.message_type:
            for type, path, item in self._walk_message(base_path, message):
                if type == 'enum':
                    enums.append(self._make_enum(path, item))
                elif type == 'message':
                    messages.append(self._make_message(path, item))
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
    ASTGenerator().generate()


if __name__ == '__main__':
    main()
