#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Author: mcxiaoke
# @Date:   2015-11-26 16:52:55
from __future__ import print_function
import os
import sys
import struct
import shutil
import argparse
import time
from multiprocessing import Pool

__version__ = '0.9.12-SNAPSHOT'

ZIP_SHORT = 2
MARKET_PATH = 'markets.txt'
OUTPUT_PATH = 'archives'
MAGIC = '!ZXK!'

def write_market(path, market, output):
    if not os.path.exists(output):
        os.makedirs(output)
    path = os.path.abspath(path)
    name,ext = os.path.splitext(os.path.basename(path))
    apk_name = name + "-" + market + ext
    apk_file = os.path.join(output,apk_name)
    shutil.copy(path,apk_file)
    # print('apkfile:',apkfile)
    index = os.stat(apk_file).st_size
    index -= ZIP_SHORT
    with open(apk_file,"r+b") as f:
        f.seek(index)
        # write comment length 
        f.write(struct.pack('<H',len(market) + ZIP_SHORT + len(MAGIC)))
        # write comment content
        # content = [market_string + market_length + magic_string]
        f.write(market)
        f.write(struct.pack('<H',len(market)))
        f.write(MAGIC)
    return apk_file


def read_market(path):
    index = os.stat(path).st_size
    # print('path:',path,'length:',index)
    index -= len(MAGIC)
    f = open(path,'rb')
    f.seek(index)
    # read and check magic
    magic = f.read(len(MAGIC))
    # print('magic',magic)
    if magic == MAGIC:
        index -= ZIP_SHORT
        f.seek(index)
        # read market string length
        market_length = struct.unpack('<H',f.read(ZIP_SHORT))[0]
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

def verify_market(file,market):
    return read_market(file) == market

def parse_markets(path):
    with open(path) as f:
        return filter(None,map(lambda x: x.split('#')[0].strip(), f.readlines()))

def process(file, market = MARKET_PATH,output = OUTPUT_PATH):
    markets = parse_markets(market)
    counter = 0
    for market in markets:
        apk_file = write_market(file, market, output)
        verified = verify_market(apk_file, market)
        if not verified:
            print('apk',apk_file,'for market',market,'verify failed')
            # break
        else:
            print('processed apk',apk_file)
            ++counter
    print('all',counter,'apks saved to',os.path.abspath(output)) 

def show_info(file):
    print('the market of file',file,'is',read_market(file))

def run_test(file,times):
    print('start to run market packaging testing...')
    t0 = time.time()
    for i in xrange(1,times):
        write_market(file,'%i Test Market' % i, 'temp')
    print('run',times,'using',(time.time() - t0), 'seconds')
    pass

def check(file, market = MARKET_PATH,output = OUTPUT_PATH, info=False, test = 0):
    if not os.path.exists(file):
        print('apk file',file,'not exists or not readable')
        return
    if info:
        show_info(file)
        return
    if test > 0:
        run_test(file,test)
        return
    if not os.path.exists(market):
        print('market file',market,'not exists or not readable')
        return
    old_market = read_market(file)
    if old_market:
        print('apk file',file,'already had market:',old_market,
            'please using original release apk file')
        return
    process(file,market,output)

def parse_args():
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description='PackerNg v{0} created by mcxiaoke. \nNext Generation Android Market Packaging Tool'.format(__version__),
        epilog='''Project Home: https://github.com/mcxiaoke/packer-ng-plugin
        ''')
    parser.add_argument('file', nargs='?',
                        help='original release apk file path (required)')
    parser.add_argument('market', nargs='?',default = MARKET_PATH, 
                        help='markets file path [default: ./markets.txt]')
    parser.add_argument('output', nargs='?',default = OUTPUT_PATH, 
                        help='archives output path [default: ./archives]')
    parser.add_argument('-i', '--info', action='store_const', const=True, 
                        help='show apk file market info')
    parser.add_argument('-t', '--test', default = 0, type = int,  
                        help='perform market packaging test')
    args = parser.parse_args()
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
    # print(args)
    return args

if __name__ == '__main__':
    check(**vars(parse_args()))
