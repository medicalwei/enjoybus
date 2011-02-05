# -*- encoding: utf-8 -*-
import re
from time      import sleep
from urllib2   import urlopen, URLError
from functools import partial
from operator  import concat

try:
   from google.appengine.api.urlfetch import DownloadError as URLError
except ImportError:
    pass

from storelayer import rtcached, rtcache 
from myurlfetch import urlfetch

rtcached = partial(rtcached, namespace_prefixer = lambda ns: 'ntcebus_%s' % ns)
urlfetch = partial(urlfetch, encoding='big5')

URL_NTC_EBUS_MENU  = 'http://210.69.92.234/pda/index.html'
URL_NTC_EBUS_ROUTE = 'http://210.69.92.234/pda/BusStop.asp?rid=%s'
RE_MENU_ROUTE_CODE = re.compile("(?<=value=').*(?=')", re.M)
RE_MENU_ROUTE_NAME = re.compile("(?<='>).*?(?=</option>)", re.M)
RE_ROUTE_TABLE_TD  = re.compile("(?<=<td>).*?(?=</td>)", re.M)

@rtcached
def _raw_menu():
    '''
    Dependence: urlfetch
    Return    : ([route_name, ...], [route_code, ...])'''
    source = urlfetch(URL_NTC_EBUS_MENU)
    return (RE_MENU_ROUTE_NAME.findall(source), RE_MENU_ROUTE_CODE.findall(source))

def _menu():
    '''
    Dependence: _raw_menu
    Return    : {route_name: route_code, ...}'''
    return dict(zip(*_raw_menu()))

def route_names():
    '''
    Dependence: _menu
    Return    : [route_name, ...]'''
    return _raw_menu()[0]

@rtcached(time=1)
def _raw_route(route_name):
    '''
    Argument  : unicode route_name
    Dependence: urlfetch
    Return    : [data, ...]'''
    return RE_ROUTE_TABLE_TD.findall(urlfetch(URL_NTC_EBUS_ROUTE % _menu()[route_name]))

@rtcached
def _raw_route_stops(route_name):
    '''
    Argument  : unicode route_name
    Dependence: _raw_route, _clean
    Return    : ([...], [...])'''
    raw_route = _raw_route(route_name)
    return (_clean(raw_route[::4]), _clean(raw_route[2::4]))

def _raw_route_waits(route_name):
    ''' 
    Argument:   unicode route_name
    Dependence: _raw_route_clean
    Return    : ([...], [...])'''
    raw_route = _raw_route(route_name)
    return (_clean(raw_route[1::4]), _clean(raw_route[3::4]))

def _clean(seq):
    try:
        return seq[:seq.index('')]
    except ValueError:
        return seq

def route_stops(route):
    '''
    Argument  : tuple(unicode route_name, bool is_return) route
    Dependence: _raw_route_stops
    Return    : [stop, ...]'''
    route_name, is_return = route
    return _raw_route_stops(route_name)[is_return]

def route_waits(route):
    '''
    Argument  : tuple(unicode route_name, bool is_return) route
    Dependence: _raw_route_stops
    Return    : [wait, ...]'''
    route_name, is_return = route
    return [int(wait) if wait.isdigit() else -1 for wait in _raw_route_waits(route_name)[is_return]]

@rtcached
def _raw_stops():
    '''
    Dependence: route_names, route_stops 
    Return    : {stop_name: [stop_route, ...], ...}'''
    stops = {}
    for route_name in route_names():
        for is_return in (False, True):
            route = (route_name, is_return)
            for stop_name in route_stops(route):
                try:
                    stops[stop_name].add(route)
                except KeyError:
                    stops[stop_name] = set((route, ))
    for route in stops:
        stops[route] = list(stops[route])
    return stops

def stop_names():
    '''
    Dependence: _raw_stops
    Return    : [stop_name, ...]'''
    return _raw_stops().keys()

def stop_routes(stop_name):
    '''
    Argument  : unicode stop_name
    Dependence: _raw_stops
    Return    : [route, ...]'''
    return _raw_stops()[stop_name]

def stop_waits(stop_name):
    '''
    Argument  : unicode stop_name
    Dependence: stop_routes, route_waits
    Return    : [wait, ...]'''
    routes = stop_routes(stop_name)
    return [route_waits(route)[routes.index(stop_name)] for route in routes]

def stop_locations(stop_name):
    '''
    Argument  : unicode stop_name
    Dependence: stop_routes
    Return    : [None, ...]'''
    return [None] * len(stop_routes(stop_name))

if __name__ == '__main__':
    route = (u'838', False)
    for stop, wait in zip(*(f(route) for f in (route_stops, route_waits))):
        print '%s: %d' % (stop, wait)

    stop_name = u'捷運景安站'
    for route, wait, location in zip(*[f(stop_name) for f in (stop_routes, stop_waits, stop_locations)]):
        print '%s at %s: %d' % (route, location, wait)

    rtcache.dump(open('rtcache.ntcebus.pickled', 'w'))
