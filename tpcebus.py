# -*- encoding: utf-8 -*-

import re
from urllib     import urlencode
from myurlfetch import urlfetch

from storelayer import rtcached

def _make_raw_data_fetchers():

    materials = (
        ('http://117.56.56.194/Asp/start21.aspx'              , 'utf-8', 'Glid'), # raw data of route
        ('http://117.56.56.194/Asp/GetTimeByRouteStop4.aspx'  , 'utf-8', 'GSName'), # raw data of stop
        ('http://117.56.56.194/WordPlan/WordBus.aspx?Lang=cht', 'utf-8'), # names of route
        ('http://117.56.56.194/WordPlan/cht/WordBus_PATH.js'  , 'utf-16') # names of stop
    )
    make_partial_urlfetch = ( lambda url, encoding, *keys: (
                lambda *values:
                    urlfetch(
                        url,
                        urlencode( dict((k, v.encode('utf-8')) for k, v in zip(keys, values)) ) if keys else None,
                        encoding
                    )
            ))
    return (make_partial_urlfetch(*material) for material in materials)

def _ebus_format_handler(raw_data):
    tables = [
            [ row.split('_,') for row in table.split('_|') if row]
            for table in raw_data.split('_&')
        ]
    return tables

def _make_js_handler(variable):
    def handler(raw_data):
        raw_data = raw_data.replace('\n', '').replace(';', '\n')
        names = re.finditer('(?<='+variable+'\=\[).*(?=\])', raw_data).next().group(0)
        names = [name for name in names.split("'")]
        return [name for name in names if name.strip(' \r,')]
    return handler 

def _handled_data_fetchers():
    handlers = (
            _ebus_format_handler,
            _ebus_format_handler,
            _make_js_handler('PATH'),
            _make_js_handler('STOP')
        )
    make_handled_data_fetcher = ( lambda handler, raw_data_fetcher: (
            lambda *args: handler(raw_data_fetcher(*args))
        ))
    return (
        make_handled_data_fetcher(handler, raw_data_fetcher)
        for handler, raw_data_fetcher in zip(handlers, _make_raw_data_fetchers())
    )

_raw_route, _raw_stop, route_names, stop_names = _handled_data_fetchers()

_raw_route  = _raw_route
_raw_stop   = _raw_stop
route_names = rtcached(route_names)
stop_names  = rtcached(stop_names)

def _find_sep(table):
    sep = 0
    while table[sep][3] == '0':
        sep += 1

@rtcached(time=1)
def _suffixed_raw_route(route_name):
    '''
    Argument  : unicode route_name
    Dependence: _raw_route
    Return    : (rotated_table, return_sep_index)'''
    table = _raw_route(route_name)[0]
    sep   = _find_sep(table)
    table = zip(*table)
    return (table, sep)

@rtcached(time=1)
def _suffixed_raw_stop(stop_name):
    '''
    Argument  : unicode stop_name
    Dependence: _raw_stop
    Return    : rotated_table'''
    return zip(*_raw_stop(stop_name)[0][1:])

@rtcached
def _raw_route_stops(route_name):
    '''
    Argument  : unicode route_name
    Dependence: _suffixed_raw_route
    Return    : ((stop, ...), (stop, ...))'''
    table, sep = _suffixed_raw_route(route_name)
    return (table[0][:sep], table[0][sep:])

def _raw_route_waits(route_name):
    '''
    Argument  : unicode route_name
    Dependence: _suffixed_raw_route
    Return    : ((wait, ...), (wait, ...))'''
    table, sep = _suffixed_raw_route(route_name)
    return (table[2][:sep], table[2][sep:])

@rtcached
def route_stops(route):
    '''
    Argument  : tuple(unicode route_name, bool is_return) route
    Dependence: _raw_route_stops
    Return    : (stop, ...)'''
    route_name, is_return = route
    return _raw_route_stops(route_name)[is_return]

def route_waits(route):
    '''
    Argument  : tuple(unicode route_name, bool is_return) route
    Dependence: _raw_route_stops
    Return    : (route, ...)'''
    route_name, is_return = route
    return [wait//60 for wait in map(int, _raw_route_waits(route_name)[is_return])]

@rtcached
def stop_routes(stop_name):
    '''
    Argument  : unicode stop_name
    Dependence: _suffixed_raw_stop 
    Return    : [(route_name, is_return), ...]'''
    table = _suffixed_raw_stop(stop_name)
    return zip(table[0], map(bool, map(int, table[3])) )

def stop_waits(stop_name):
    '''
    Argument  : unicode stop_name
    Dependence: _suffixed_raw_stop
    Return    : [wait, ...]'''
    return [wait//60 if wait != 99999 else -2 for wait in map(int, _suffixed_raw_stop(stop_name)[5])]

@rtcached
def stop_locations(stop_name):
    '''
    Argument  : unicode stop_name
    Dependence: _suffixed_raw_stop
    Return    : [(east_longitude, north_latitude), ...]'''
    table = _suffixed_raw_stop(stop_name)
    return zip(map(float, table[1]), map(float, table[2]))


if __name__ == '__main__':
    route = (u'綠2左', False)
    for stop, wait in zip(*[f(route) for f in (route_stops, route_waits)]):
        print '%s: %d' % (stop, wait)

    stop_name = u'尖山腳'
    for route, wait, location in zip(*(f(stop_name) for f in (stop_routes, stop_waits, stop_locations))):
        print '%s at %s: %d' % (route, location, wait)
