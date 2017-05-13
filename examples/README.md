# Hello World Example

## Usage

First of all, change to directory `helloworld`.

### Generate the JSON proxy

1. Generate the helloworld_pb2.py file

    ```bash
    $ python -m grpc_tools.protoc -I. --python_out=. --grpc_python_out=. helloworld.proto
    ```

2. Generate the Pythonic service

    ```bash
    $ python -m grpc_pytools.pythonic --pb2-module-name='helloworld_pb2' --service-name='Greeter' > service.py
    ```

3. Generate the marshmallow schemas

    ```bash
    $ python -m grpc_pytools.marshmallow --pb2-module-name='helloworld_pb2' > schemas.py
    ```

4. Generate the RESTArt APIs

    ```bash
    $ python -m grpc_pytools.restart --pb2-module-name='helloworld_pb2' --grpc-server='localhost:50051' --service-name='Greeter' > apis.py
    ```

Simplify all the above steps by `make`:

```bash
$ make
```

### Run the gRPC server

```bash
$ python greeter_server.py
```

### Start the JSON proxy

```bash
$ restart apis:api -p 6666
```

### Consume the JSON APIs

```bash
# By cURL
$ curl -H 'Content-Type: application/json' -XPOST http://localhost:6666/say_hello -d '{"name": "russell"}'
# Or by HTTPie
$ http post http://localhost:6666/say_hello name=russell
```
