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
$ restart apis:api -p 60066
```

### Consume the JSON APIs

By cURL:

```bash
# Normal request with valid data
$ curl -i -H 'Content-Type: application/json' -XPOST http://localhost:60066/say_hello -d '{"name": "world"}'
HTTP/1.0 200 OK
Content-Type: application/json
Content-Length: 30
Server: Werkzeug/0.12.1 Python/2.7.10
Date: Mon, 15 May 2017 16:00:49 GMT

{"message": "Hello, world!"}

# Bad request with invalid data
$ curl -i -H 'Content-Type: application/json' -XPOST http://localhost:60066/say_hello -d '{"name": 1}'
HTTP/1.0 400 BAD REQUEST
Content-Type: application/json
Content-Length: 46
Server: Werkzeug/0.12.1 Python/2.7.10
Date: Mon, 15 May 2017 16:00:40 GMT

{"message": {"name": ["Not a valid string."]}}
```

Or by [HTTPie][1]:

```bash
# Normal request with valid data
$ http post http://localhost:60066/say_hello name=world
HTTP/1.0 200 OK
Content-Length: 30
Content-Type: application/json
Date: Mon, 15 May 2017 16:02:28 GMT
Server: Werkzeug/0.12.1 Python/2.7.10

{
    "message": "Hello, world!"
}

# Bad request with invalid data
$ http post http://localhost:60066/say_hello name:=1
HTTP/1.0 400 BAD REQUEST
Content-Length: 46
Content-Type: application/json
Date: Mon, 15 May 2017 16:02:59 GMT
Server: Werkzeug/0.12.1 Python/2.7.10

{
    "message": {
        "name": [
            "Not a valid string."
        ]
    }
}
```


[1]: https://github.com/jakubroztocil/httpie
