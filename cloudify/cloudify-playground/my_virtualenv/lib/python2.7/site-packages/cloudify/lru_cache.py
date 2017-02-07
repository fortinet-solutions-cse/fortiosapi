########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

# Copied and modified from
# http://code.activestate.com/recipes/498245-lru-and-lfu-cache-decorators/

import collections
import functools
from itertools import ifilterfalse


def lru_cache(maxsize=100, on_purge=None):
    """Least-recently-used cache decorator.

    Arguments to the cached function must be hashable.
    Clear the cache with f.clear().
    """
    maxqueue = maxsize * 10

    def decorating_function(user_function):
        cache = {}
        queue = collections.deque()
        refcount = collections.defaultdict(int)
        sentinel = object()
        kwd_mark = object()

        # lookup optimizations (ugly but fast)
        queue_append, queue_popleft = queue.append, queue.popleft
        queue_appendleft, queue_pop = queue.appendleft, queue.pop

        @functools.wraps(user_function)
        def wrapper(*args, **kwargs):
            # cache key records both positional and keyword args
            key = args
            if kwargs:
                key += (kwd_mark,) + tuple(sorted(kwargs.items()))

            # record recent use of this key
            queue_append(key)
            refcount[key] += 1

            # get cache entry or compute if not found
            try:
                result = cache[key]
            except KeyError:
                result = user_function(*args, **kwargs)
                cache[key] = result

                # purge least recently used cache entry
                if len(cache) > maxsize:
                    key = queue_popleft()
                    refcount[key] -= 1
                    while refcount[key]:
                        key = queue_popleft()
                        refcount[key] -= 1
                    if on_purge:
                        on_purge(cache[key])
                    del cache[key], refcount[key]

            # periodically compact the queue by eliminating duplicate keys
            # while preserving order of most recent access
            if len(queue) > maxqueue:
                refcount.clear()
                queue_appendleft(sentinel)
                for key in ifilterfalse(refcount.__contains__,
                                        iter(queue_pop, sentinel)):
                    queue_appendleft(key)
                    refcount[key] = 1
            return result

        def clear():
            if on_purge:
                for value in cache.itervalues():
                    on_purge(value)
            cache.clear()
            queue.clear()
            refcount.clear()

        wrapper._cache = cache
        wrapper.clear = clear
        return wrapper
    return decorating_function
