# pykasm

A collection of useful utilities and utility libraries for my projects.

## Install

```sh
pip install pykasm-alkasm
```

## Examples

### `TimeoutIterable`

A timeout will not help with indefinite blocking. Concurrent futures will
attempt to cancel the pull on the generator, if possible.

```python
from pykasm import TimeoutIterable
from time import sleep

def tired_generator(n):
    for seconds in range(n):
        yield f"sleeping for {seconds} second(s)"
        sleep(seconds)

# will timeout if more than 3 seconds elapse between iterations
for v in TimeoutIterable(tired_generator(5), timeout=3.14):
    print(v)
```

> ```
> sleeping for 1 second(s)
> sleeping for 2 second(s)
> sleeping for 3 second(s)
> ```

### `StreamBuffer`

The stream buffer is not particularly robust. 
* Indefinite blocking will cause the thread to also indefinitely block.
* Generators that tax the CPU heavily may have a hard time shutting off. 
* Use with caution, and not in production.

```python
from pykasm import StreamBuffer
from itertools import count
from time import sleep

# collect values from infinite generator `count()` over a period of time
sleep_time = 0.0001
with StreamBuffer(count()) as buf:
    time.sleep(sleep_time)
    counts = list(buf.flush())
print(f"collected {len(counts)} values in {sleep_time} seconds!")
```

> ```
> collected 13647 values in 0.0001 seconds!
> ```

### `@timed`

You'll need to set logging level to `DEBUG` to see the timer messages.

```python
from pykasm import timed
from time import sleep
import logging
logging.basicConfig(level=logging.DEBUG)

@timed
def takes_a_second():
    time.sleep(1)

takes_a_second()
```

> ```
> DEBUG:root:takes_a_second took 1004.352 ms
> ```