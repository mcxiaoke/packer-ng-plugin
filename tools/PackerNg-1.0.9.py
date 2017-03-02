# -*- coding: utf-8 -*-
# @Author: mcxiaoke
# @Date:   2015-11-26 16:52:55
# @Last Modified by:   mcxiaoke
# @Last Modified time: 2017-03-02 18:30:36
from __future__ import print_function
import os
import sys
import struct
import shutil
import argparse
import time
from apkinfo import APK
from string import Template

__version__ = '1.0.9'  # 2017.03.03

ZIP_SHORT = 2
MARKET_PATH = 'markets.txt'
OUTPUT_PATH = 'apks'
ARCHIVE_FORMAT = '${name}-${package}-v${vname}-${vcode}-${market}${ext}'
MAGIC = '!ZXK!'

INTRO_TEXT = "\nAttention: if your app using Android gradle plugin 2.2.0 or later, \
be sure to install one of the generated Apks to device or emulator, \
to ensure the apk can be installed without errors. \
More details please go to github \
https://github.com/mcxiaoke/packer-ng-plugin.\n"


def write_market(path, market, output, format):
    '''
    write market info to apk file
    write_market(apk-file-path, market-name, output-path)
    '''
    path = os.path.abspath(path)
    output = unicode(output)
    if not os.path.exists(path):
        print('apk file', path, 'not exists')
        return
    if read_market(path):
        print('apk file', path, 'had market already')
        return
    if not output:
        output = os.path.dirname(path)
    if not os.path.exists(output):
        os.makedirs(output)
    name, ext = os.path.splitext(os.path.basename(path))
    # name,package,vname,vcode
    app = parse_apk(path)

    dic = dict(
        name=name,
        package=app['app_package'],
        vname=app['version_name'],
        vcode=app['version_code'],
        market=market.decode('utf8'),
        ext=ext)
    tpl = Template(format)
    apk_name=tpl.substitute(dic)

    # apk_name = '%s-%s-%s-%s%s' % (app['app_package'], market.decode('utf8'), app['version_name'], app['version_code'], ext)
    # apk_name = name + "-" + market + ext
    apk_file = os.path.join(output, apk_name)
    shutil.copy(path, apk_file)
    # print('apk file:',apk_file)
    index = os.stat(apk_file).st_size
    index -= ZIP_SHORT
    with open(apk_file, "r+b") as f:
        f.seek(index)
        # write comment length
        f.write(struct.pack('<H', len(market) + ZIP_SHORT + len(MAGIC)))
        # write comment content
        # content = [market_string + market_length + magic_string]
        f.write(market)
        f.write(struct.pack('<H', len(market)))
        f.write(MAGIC)
    return apk_file


def read_market(path):
    '''
    read market info from apk file
    read_market(apk-file-path)
    '''
    index = os.stat(path).st_size
    # print('path:',path,'length:',index)
    index -= len(MAGIC)
    f = open(path, 'rb')
    f.seek(index)
    # read and check magic
    magic = f.read(len(MAGIC))
    # print('magic',magic)
    if magic == MAGIC:
        index -= ZIP_SHORT
        f.seek(index)
        # read market string length
        market_length = struct.unpack('<H', f.read(ZIP_SHORT))[0]
        # print('comment length:',market_length)
        index -= market_length
        f.seek(index)
        # read market
        market = f.read(market_length)
        # print('found market:',market)
        return market
    else:
        # print('magic not matched')
        return None


def verify_market(path, market):
    '''
    verify apk market info
    verify_market(apk-file-path,market-name)
    '''
    return read_market(path) == market


def show_market(path):
    '''
    show market info for apk file
    show_market(apk-file-path)
    '''
    app = parse_apk(path)
    market = read_market(path)
    if market:
        market = market.decode('utf8')
    print(u'Name: %s\nMarket: %s\nPackage:%s\nVersionName: %s\nVersionCode: %s' % (
        app['app_name'], market, app['app_package'],
        app['version_name'], app['version_code']))


def parse_markets(path):
    '''
    parse file lines to market name list
    parse_markets(market-file-path) 
    '''
    with open(path) as f:
        return filter(None, map(lambda x: x.split('#')[0].strip(), f.readlines()))


def parse_apk(path):
    '''
    parse apk file, get name, package, version
    '''
    apk = APK(path)
    if not apk.is_valid_APK():
        return None
    return {
        'app_file': path.decode('utf8'),
        'app_name': apk.get_app_name(),
        'app_package': apk.get_package(),
        'version_name': apk.get_version_name(),
        'version_code': apk.get_version_code()
    }


def process(path, market=MARKET_PATH, output=OUTPUT_PATH, format=ARCHIVE_FORMAT):
    '''
    process apk file to create market apk archives
    process(apk-file-path, market = MARKET_PATH, output = OUTPUT_PATH)
    '''
    print('start to write market info to apk files ...')
    markets = parse_markets(market)
    counter = 0
    for market in markets:
        apk_file = write_market(path, market, output, format)
        verified = verify_market(apk_file, market)
        if not verified:
            print('apk', apk_file, 'for market', market, 'verify failed')
            # break
        else:
            print('processed apk', apk_file)
            counter += 1
    print('all', counter, 'apks saved to', os.path.abspath(output))
    print(INTRO_TEXT)


def run_test(path, times):
    '''
    run market packer performance test
    '''
    print('start to run market packaging testing...')
    t0 = time.time()
    for i in xrange(1, times):
        write_market(path, '%s Test Market' % i, 'temp')
    print('run', times, 'using', (time.time() - t0), 'seconds')
    pass


def _check(apkfile, marketfile=MARKET_PATH, output=OUTPUT_PATH, format=ARCHIVE_FORMAT, show=False, test=0):
    '''
    check apk file exists, check apk valid, check arguments, check market file exists
    '''
    if not os.path.exists(apkfile):
        print('apk file', apkfile, 'not exists or not readable')
        return
    if not parse_apk(apkfile):
        print('apk file', apkfile, 'is not valid apk')
        return
    if show:
        show_market(apkfile)
        return
    if test > 0:
        run_test(apkfile, test)
        return
    if not os.path.exists(marketfile):
        print('marketfile file', marketfile, 'not exists or not readable.')
        return
    old_market = read_market(apkfile)
    if old_market:
        print('apk file', apkfile, 'already had market:', old_market,
              'please using original release apk file')
        return
    process(apkfile, marketfile, output, format)


def _parse_args():
    '''
    parse command line arguments
    '''
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='PackerNg v{0} created by mcxiaoke.\n {1}'.format(__version__, INTRO_TEXT),
        epilog='')
    parser.add_argument('apkfile', nargs='?',
                        help='original release apk file path (required)')
    parser.add_argument('marketfile', nargs='?', default=MARKET_PATH,
                        help='markets file path [default: ./markets.txt]')
    parser.add_argument('output', nargs='?', default=OUTPUT_PATH,
                        help='archives output path [default: ./archives]')
    parser.add_argument('-f', '--format', nargs='?', default=ARCHIVE_FORMAT, const=True,
                        help="archive format [default:'${name}-${package}-v${vname}-${vcode}-${market}${ext}']")
    parser.add_argument('-s', '--show', action='store_const', const=True,
                        help='show apk file info (pkg/market/version)')
    parser.add_argument('-t', '--test', default=0, type=int,
                        help='perform serval times packer-ng test')
    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        return None
    return args

if __name__ == '__main__':
    args = _parse_args()
    if args:
        _check(**vars(args))
