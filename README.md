<h1 align="center">𝜗</h1>

* `EvictingQueue` - queue with evicting, non-blocking puts, blocking gets with timeouts, and iteration semantics
* `StoppableThread` - thread with cancellation semantics
* `Store` - callback executor with thread-safe writers

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
