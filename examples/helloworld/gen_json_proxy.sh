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
pb2_module_name=${proto_file%.*}_pb2

(
	cd ${proto_dir} &&
	python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. ${proto_file} &&
	python -m grpc_pytools.pythonic --pb2-module-name=${pb2_module_name} > service.py &&
	python -m grpc_pytools.marshmallow --pb2-module-name=${pb2_module_name} > schemas.py &&
	python -m grpc_pytools.restart --pb2-module-name=${pb2_module_name} --grpc-server=${grpc_server} > apis.py
)
