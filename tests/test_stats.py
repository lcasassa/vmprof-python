import json
import zlib

import py
import six

import vmprof
from vmprof.reader import LibraryData
from vmprof.stats import Node


def get_or_write_libcache(filename):
    libache_filename = str(py.path.local(__file__).join('..', filename + '.libcache'))
    try:
        with open(libache_filename, 'rb') as f:
            s = zlib.decompress(f.read())
            if not isinstance(s, str):
                s = s.decode('utf-8')
            d = json.loads(s)
        lib_cache = {}
        for k, v in d.items():
            lib_cache[k] = LibraryData(v[0], v[1], v[2], v[3], [tuple(x) for x in v[4]])
        return lib_cache
    except (IOError, OSError):
        pass
    path = py.path.local(__file__).join('..', filename)
    lib_cache = {}
    vmprof.read_profile(path, virtual_only=True,
                        include_extra_info=True, lib_cache=lib_cache)
    d = {}
    for k, lib in six.iteritems(lib_cache):
        d[k] = (lib.name, lib.start, lib.end, lib.is_virtual, lib.symbols)
    with open(libache_filename, "wb") as f:
        f.write(zlib.compress(json.dumps(d).encode('utf-8')))
    return lib_cache


def test_read_simple():
    lib_cache = get_or_write_libcache('simple_nested.pypy.prof')
    path = py.path.local(__file__).join('..', 'simple_nested.pypy.prof')
    stats = vmprof.read_profile(path, virtual_only=True,
                                include_extra_info=True, lib_cache=lib_cache)
    tree = stats.get_tree()
    main_name = 'py:<module>:2:foo.py'
    foo_name = 'py:foo:6:foo.py'
    bar_name = 'py:bar:2:foo.py'
    assert tree['foo'].name == foo_name
    assert tree['foo'].meta['jit'] == 19
    assert tree['foo']['bar'].name == bar_name
    assert tree['foo']['bar'].meta['jit'] == 62
    assert tree['foo']['bar'].jitcodes == {140523638275600: 27,
                                           140523638276656: 12}
    assert tree['foo'].jitcodes == {140523638277712: 19}
    assert not tree['foo']['bar'].children
    assert tree['foo']['bar'].meta['gc:minor'] == 2
    data = json.loads(tree.as_json())
    main_addr = str(tree.addr)
    foo_addr = str(tree['foo'].addr)
    bar_addr = str(tree['foo']['bar'].addr)
    expected = [main_name, main_addr, 120, {}, [
        [foo_name, foo_addr, 120, {'jit': 120, 'gc:minor': 2}, [
            [bar_name, bar_addr, 101, {'gc:minor': 2, 'jit': 101}, []]]]]]
    assert data == expected
