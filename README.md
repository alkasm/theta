<h1 align="center">𝜗</h1>

* `EvictingQueue` - SPSC queue, similar to `queue.Queue` but with evicting, non-blocking puts and simple iteration semantics.  
* `StoppableThread` - thread which contains a `threading.Event` stop flag for cancellable tasks.  
* `Store` - callback executor primarily designed to be used as a simple MPMC data store.  

[Read the docs](https://alkasm.github.io/theta/) for examples and the API reference.

## Install

```sh
pip install theta-alkasm
```

## Development

In a virtual environment:

```
$ poetry install
$ poetry check
$ poetry run pytest
$ poetry run black theta
$ poetry run mypy theta
```
