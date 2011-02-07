# -*- encoding: utf-8 -*-
# python 2.5
 
from time      import time as now
from functools import wraps
from pickle    import dump, load, dumps, loads
 
try:
    from google.appengine.api import memcache
    from google.appengine.ext import db
except ImportError:
    memcache = None
    db = None
 
def storelayer_maker(memcachelike):
    '''Use a memcache-like object to make a store layer for functions.
   
   Arguments:
       memcachelike
           bool  set(key, value, time=0, namespace=None)
           value get(key, namespace=None)
           bool  delete(key, namespace=None)
   
   Return: <storelayer decorator maker>'''
 
    def storelayer_decorator_maker(time_or_func=None, namespace=None, key_prefixer=dumps, namespace_prefixer=lambda x:x, time=0):
        '''A maker of storelayer decorator. (or a decorator.)
       
        Arguments:
            sec/func time_or_func
                time if you want to build a decorator
                    seconds, the data will be invalidate after this or at this
                func if you use it as a decorator
           
            any namespace
                anything the low layer accepted
                default is the function name
               
            byte key_prefixer((args, kargs))
                will be called with the arguments pass here
                default is the pickle.dumps
               
            any namespace_prefixer(namespace)
                will be called when docotrating
                default is do nothing on namespace
               
            sec time
               as the time case of time_or_func
               
       Return: <storelayer decorator> or <storable function>'''
       
        # nonlocal memcachelike
        def storelayer_decorator(func):
            '''A storelayer decorator.
           
           Return: <storable function>'''
            # nonlocal memcachelike
            # nonlocal time, namespace
            ns = namespace_prefixer(namespace if namespace != None else func.func_name)
           
            @wraps(func)
            def storable(*args, **kargs):
                # nonlocal memcachelike
                # nonlocal time, namespace
                # nonlocal func
                key = key_prefixer((args, kargs))
                value = memcachelike.get(key=key, namespace=ns)
                if value == None or kargs.get('_focus_update', False):
                    if not func.__dict__.get('is_storable', False):
                        try:
                            del kargs['_focus_update']
                        except KeyError:
                            pass
                    value = func(*args, **kargs)
                    memcachelike.set(key=key, value=value, time=time, namespace=ns)
                return value
           
            # install the delete method to storable 
            storable.delete = lambda *args, **kargs: memcachelike.delete(key=key_prefixer((args, kargs)), namespace=ns)
            storable.is_storable = True
           
            return storable
           
        if callable(time_or_func):
            func = time_or_func
            time = 0
            return storelayer_decorator(time_or_func)
        else:
            time = time_or_func if time_or_func != None else time
            return storelayer_decorator
   
    return storelayer_decorator_maker
 
maker = storelayer_maker

# Build a simple cacher for runtime
# (and it is a simple example to show how to build a memcache-like instance for storelayer)
 
MAX_TIME = 30*24*60*60 # a month
 
class RTCache:
    '''A runtime cacher.
   
   The data will be clear at the end of the program.'''
    def __init__(self, pools=None):
        self.pools = pools if pools != None else {}
       
    def set(self, key, value, time=0, namespace=None):
        if time != 0 and time <= MAX_TIME:
            time += now()
   
        pool = self.pools.get(namespace, None)
        if pool == None:    
            pool = self.pools[namespace] = {}
        pool[key] = (value, time)
       
        return True
 
    def get(self, key, namespace=None):
        value, time = self.pools.get(namespace, {}).get(key, (None, None))
       
        if time != 0 and now() > time:
            self.delete(key, namespace)
        else:
            return value
           
    def delete(self, key, namespace=None):
        try:
            del self.pools[namespace][key]
            if not self.pools[namespace]:
                del self.pools[namespace]
        except KeyError:
            return 1
        else:
            return 2

    def dump(self, file):
        dump(self.pools, file)

    def load(self, file):
        self.pools = load(file)
 
rtcache = RTCache()
rtcached = storelayer_maker(rtcache)
 
if db:
 
    class Datastored(db.Model):
        namespace = db.StringProperty(multiline=True)
        name  = db.StringProperty(multiline=True)
        value = db.BlobProperty()
        time  = db.FloatProperty()
       
    def datastore(): pass
   
    def _ds_get_record(key, namespace=None):
        return iter(Datastored.gql('WHERE name = :name AND namespace = :namespace', name=key, namespace=namespace or '')).next()
   
    def _ds_set(key, value, time=0.0, namespace=''):
   
        if time != 0 and time <= MAX_TIME:
            time += now()
   
        try:
            record = datastore.get_record(key, namespace)
        except StopIteration:
            record = Datastored()
       
        record.namespace = namespace or ''
        record.name  = key
        record.value = dumps(value, protocol=2)
        record.time  = float(time)
        record.put()
       
        return True
   
    def _ds_get(key, namespace=None):
        try:
            record = datastore.get_record(key, namespace)
        except StopIteration:
            return None
        else:
            if record.time != 0 and now() > record.time:
                datastore.delete(record=record)
                value = None
            else:
                value = loads(str(record.value))
            return value
           
    def _ds_delete(key=None, namespace=None, record=None):
        if key == None and record == None:
            raise TypeError('the `key` or `record` is necessary')
        if record == None:
            try:
                record = datastore.get_record(key, namespace)
            except StopIteration:
                return 1
        record.delete()
        return 2
   
    datastore.set = _ds_set
    datastore.get = _ds_get
    datastore.delete = _ds_delete
    datastore.get_record = _ds_get_record
   
    datastored = storelayer_maker(datastore)
else:
    datastored = None 
 
# Make a storelayer with memcache
memcached = None if not memcache else storelayer_maker(memcache)
 
if __name__ == '__main__':
    from time import sleep
   
    # in default,
    # the namespace use the function name and here are two tests on a case,
    # so need to define two functions
    def test1(x): return x+c
    def test2(x): return x+c
   
    # in normal case,
    # caches will be reseted at the end of the program
    cases = [rtcached]
    # caches will be reseted at the close of the server
    if memcached : cases.append(memcached)
    # caches will not be reseted
    if datastored: cases.append(datastored)
  
    for storelayer in cases:
        case = storelayer(test1)
        print 'Test with default parameters.'
        c = 0; print '1st:', case(1) # 1 (if reseted else 3)
        c = 1; print '2nd:', case(1) # 1 (if reseted else 3)
        print 'delete:', case.delete(1) # 2 (singal of delete)
        c = 2; print '3rd:', case(1) # 3
        print 'focus update:'
        c = 3; print '4th:', case(1, _focus_update=True) # 4
        print
       
        case = storelayer(time=1)(test2)
        print 'Test with time=1.'
        c = 0; print '1st:', case(1) # 1 (always will be reset because the time limit)
        c = 1; print '2nd:', case(1) # 1
        print 'sleep(1)'; sleep(1)
        c = 2; print '3rd:', case(1) # 3
        print 'focus update:'
        c = 3; print '4th:', case(1, _focus_update=True) # 4
        print
   
    # An example for GAE environment
    if datastored and memcached:
        print 'Usage example:'
         
        @rtcached   # first, check the runtime cacher
        @memcached  # second, check the memcache
        @datastored # finally, check the datastore
        def slow_func(a):
            sleep(5)
            return a
   
   
        print 'start timer'
        timer = now()
   
        print '1st:', slow_func(1)
        print '2nd:', slow_func(1)
           
        print 'time costed:', now()-timer
