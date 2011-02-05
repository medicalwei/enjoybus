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
    Return    : [route_names, ...]'''
    return _raw_menu()[0]

@rtcached(time=1)
def _raw_route(route_name):
    '''

    Argument:   unicode route_name
    Dependence: urlfetch
    Return    : [route_name, ...]'''
    return RE_ROUTE_TABLE_TD.findall(urlfetch(URL_NTC_EBUS_ROUTE % _menu()[route_name]))

@rtcached
def _raw_route_stops(route_name):
    '''

    Argument:   unicode route_name
    Dependence: _raw_route, _clean
    Return    : ([...], [...])'''
    raw_route = _raw_route(route_name)
    return (_clean(raw_route[::4]), _clean(raw_route[2::4]))

def _raw_route_waits(route_name):
    '''
    
    Argument:   unicode route_name
    Dependence: _raw_route_clean
    Return    : ([...], [...])'''
    raw_route_data = _raw_route(route_name)
    return (_clean(raw_route[1::4]), _clean(raw_route[3::4]))

def _clean(seq):
    try:
        return seq[:seq.index('')]
    except ValueError:
        return seq

def route_stops(route_name, is_return):
    '''

    Argument:
        unicode route_name
        bool    is_return 
    Dependence: _raw_route_stops
    Return    : [...]'''
    return _raw_route_stops(route_name)[is_return]

def route_waits(route_name, is_return):
    '''

    Argument:
        unicode route_name
        bool    is_return
    Dependence: _raw_route_stops
    Return    : [...]'''
    return _raw_route_waits(route_name)[is_return]

@rtcached
def _raw_stops():
    stops = {}
    for route_name in route_names():
        for is_return in (False, True):
            for stop_name in route_stops(route_name, is_return):
                try:
                    stops[stop_name].add((route_name, is_return))
                except KeyError:
                    stops[stop_name] = set(((route_name, is_return), ))
    return stops

def stop_names():
    return _raw_stops().keys()

def stop_routes(stop_name):
    return _raw_stops()[stop_name]

def stop_location(stop_name):
    return (None, None)

if __name__ == '__main__':
    #rtcache.load(open('rtcache.pickle'))
    print stop_names()
    #rtcache.dump(open('rtcache.pickle', 'w'))
