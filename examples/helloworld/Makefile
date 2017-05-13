.PHONY: all

all: gen

gen:
	python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. helloworld.proto
	python -m grpc_pytools.pythonic --pb2-module-name='helloworld_pb2' --service-name='Greeter' > service.py
	python -m grpc_pytools.marshmallow --pb2-module-name='helloworld_pb2' > schemas.py
	python -m grpc_pytools.restart --pb2-module-name='helloworld_pb2' --grpc-server='localhost:50051' --service-name='Greeter' > apis.py
