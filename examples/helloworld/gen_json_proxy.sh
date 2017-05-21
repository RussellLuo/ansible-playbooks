#!/bin/bash
set -e

if (( $# != 2 )); then
	echo "Usage: ./gen_json_proxy.sh <proto-file> <grpc-server>"
	exit 1
fi

proto_path=$1
grpc_server=$2

proto_dir=$(dirname ${proto_path})
proto_file=$(basename ${proto_path})
ast_file=${proto_file%.*}_ast.json
pb2_module_name=${proto_file%.*}_pb2

(
	cd ${proto_dir} &&
	python -m grpc_tools.protoc -I=. --pytools-ast_out=. ${proto_file} &&
	python -m grpc_tools.protoc -I=. --python_out=. --grpc_python_out=. ${proto_file} &&
	python -m grpc_pytools.pythonic --proto-ast-file=${ast_file} --pb2-module-name=${pb2_module_name} > services.py &&
	python -m grpc_pytools.marshmallow --proto-ast-file=${ast_file} --pb2-module-name=${pb2_module_name} > schemas.py &&
	python -m grpc_pytools.restart --proto-ast-file=${ast_file} --pb2-module-name=${pb2_module_name} --grpc-server=${grpc_server} > apis.py
)
