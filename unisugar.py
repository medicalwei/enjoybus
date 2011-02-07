# -*- encoding: utf-8 -*-
# confirmed it is work in python 2.6 and GAE
# DO NOT COMMIT!

import re
import sys

import chardet

U_PART = re.compile(r'(?:\\u[0-9A-F]{4})+', re.I)
X_PART = re.compile(r'(?:\\x[0-9A-F]{2})+', re.I)

def uni(obj, encoding=None, unescape=True):
    r'''decode and unescape anything to unicode.
    
    Argument:
        any obj
            any obj you want to decode into unicode.
        string encoding
            assign a encoding to encode this obj.
            encoding will auto detect if it is not assigned.
        bool unescape
            unescape \uXXXX and \xXX if found them in obj.
    
    Return: unicode'''

    if not isinstance(obj, basestring):
        obj = str(obj)
        encoding = sys.getfilesystemencoding()

    if unescape:
        if r'\x' in obj:
            obj = X_PART.sub(lambda m: m.group().decode('string-escape'), obj)
        if r'\u' in obj:
            obj = uni(obj, encoding, unescape=False)
            obj = U_PART.sub(lambda m: m.group().decode('unicode-escape'), obj)
            return obj

    if isinstance(obj, str):
        if encoding:
            try:
                return obj.decode(encoding)
            except UnicodeDecodeError:
                pass
        return obj.decode(chardet.detect(obj)['encoding'])
    else:
        return obj

def cod(obj, encoding=None):
    '''encode anything to 8-bit string.
    
    encdoing is set to 'utf-8' if encoding is None.
    
    Return: string'''
    if not isinstance(obj, basestring):
        return str(obj)

    if encoding == None:
        encoding = 'utf-8'

    if isinstance(obj, unicode):
        return obj.encode(encoding)
    else:
        return obj

# url* with unicode
#   unicode -> urlencode (using urllib.urlencode)
#   unicode ->
#       urlread (using urllib2.urlopen or urlfetch.fetch in GAE)
#   -> unicode

import urllib

def urlencode(d, encoding=None):
    if d != None:
        return urllib.urlencode(dict(
            (cod(k, encoding), cod(d[k], encoding)) for k in d
       ))

try:
    from google.appengine.api import urlfetch
    urllib2 = None
except:
    urlfetch = None
    import urllib2

from time import time

def urlread(url, data=None, timeout=None, encoding=None, number=10):
    timer = time()
    data = urlencode(data)
    if timeout == None: timeout = 5
    result = None
    while not result and number > 0:
        print 'reading the %s ... ' % url.split('/')[-1],
        sys.stdout.flush()
        if urlfetch:
            try:
                result = urlfetch.fetch(
                        url      = url,
                        payload  = data,
                        method   = urlfetch.GET if not data else urlfetch.POST,
                        deadline = timeout
                    ).content
            except urlfetch.DownloadError:
                pass
        elif urllib2:
            try:
                result = urllib2.urlopen(
                        url     = url,
                        data    = data,
                        timeout = timeout
                    ).read()
            except urllib2.URLError:
                pass
        print '%2.2f seconds' % (time() - timer)
        number -= 1
    if result:
        return uni(result, encoding)

if __name__ == '__main__':
    print

    u = u'unicode 字串'
    s = '8-bit string 字串'
    d = {u: s}
    u2 = u'\xe9\x8c\xaf\xe8\xaa\xa4\xe7\x9a\x84 unicode \xe5\xad\x97\xe4\xb8\xb2'
    s2 = '\u932f\u8aa4\u7684 8-bit string \u5b57\u4e32'

    for f, m in zip(
        (lambda x: x, uni),
        (u'print directly:',
         u'`uni` decoded:',
         u'`cod` encoded:')
    ):
        print m
        for obj in (u, s, d, u2, s2):
            obj = f(obj)
            print '    %s %s' % (type(obj), cod(obj))
        print

    #print cod(urlread('http://210.69.92.234/pda/BusStop.asp?rid=312'))
    #print cod(urlread('http://117.56.56.194/Asp/start21.aspx', {'Glid': '275'}))
