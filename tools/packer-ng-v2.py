# -*- coding: utf-8 -*-
# @Author: mcxiaoke
# @Date:   2017-06-06 14:03:18
# @Last Modified by:   mcxiaoke
# @Last Modified time: 2018-03-23 15:36:57
from __future__ import print_function
import os
import sys
import mmap
import struct
import zipfile
import logging
import time

logging.basicConfig(format='%(levelname)s:%(lineno)s: %(funcName)s() %(message)s',
                    level=logging.ERROR)
logger = logging.getLogger(__name__)

AUTHOR = 'mcxiaoke'
VERSION = '2.0.1'
try:
    props = dict(line.strip().split('=') for line in
                 open('../gradle.properties') if line.strip())
    VERSION = props.get('VERSION_NAME')
except Exception as e:
    VERSION = '2.0.1'

#####################################################################


# ref: https://android.googlesource.com/platform/tools/apksig/+/master
# ref: https://source.android.com/security/apksigning/v2

ZIP_EOCD_REC_MIN_SIZE = 22
ZIP_EOCD_REC_SIG = 0x06054b50
ZIP_EOCD_CENTRAL_DIR_TOTAL_RECORD_COUNT_OFFSET = 10
ZIP_EOCD_CENTRAL_DIR_SIZE_FIELD_OFFSET = 12
ZIP_EOCD_CENTRAL_DIR_OFFSET_FIELD_OFFSET = 16
ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET = 20
ZIP_EOCD_COMMENT_MIN_LENGTH = 0

UINT16_MAX_VALUE = 0xffff  # 65535

BlOCK_MAX_SIZE = 0x100000  # 1m=1024k

APK_SIG_BLOCK_MAGIC = 'APK Sig Block 42'
APK_SIG_BLOCK_MAGIC_HI = 0x3234206b636f6c42
APK_SIG_BLOCK_MAGIC_LO = 0x20676953204b5041
APK_SIG_BLOCK_MIN_SIZE = 32
APK_SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871a

# plugin channel key
PLUGIN_CHANNEL_KEY = 'CHANNEL'
# plugin block id
PLUGIN_BLOCK_ID = 0x7a786b21
# plugin block magic
PLUGIN_BLOCK_MAGIC = 'Packer Ng Sig V2'

SEP_KV = '∘'
SEP_LINE = '∙'

#####################################################################


class ZipFormatException(Exception):
    '''ZipFormatException'''
    pass


class SignatureNotFoundException(Exception):
    '''SignatureNotFoundException'''
    pass


class MagicNotFoundException(Exception):
    '''MagicNotFoundException'''
    pass

#####################################################################


class ByteDecoder(object):
    '''
    byte array decoder
    https://docs.python.org/2/library/struct.html
    '''

    def __init__(self, buf, littleEndian=True):
        self.buf = buf
        self.sign = '<' if littleEndian else '>'

    def getShort(self, offset=0):
        return struct.unpack('{}h'.format(self.sign),
                             self.buf[offset:offset + 2])[0]

    def getUShort(self, offset=0):
        return struct.unpack('{}H'.format(self.sign),
                             self.buf[offset:offset + 2])[0]

    def getInt(self, offset=0):
        return struct.unpack('{}i'.format(self.sign),
                             self.buf[offset:offset + 4])[0]

    def getUInt(self, offset=0):
        return struct.unpack('{}I'.format(self.sign),
                             self.buf[offset:offset + 4])[0]

    def getLong(self, offset=0):
        return struct.unpack('{}q'.format(self.sign),
                             self.buf[offset:offset + 8])[0]

    def getULong(self, offset=0):
        return struct.unpack('{}Q'.format(self.sign),
                             self.buf[offset:offset + 8])[0]

    def getFloat(self, offset=0):
        return struct.unpack('{}f'.format(self.sign),
                             self.buf[offset:offset + 4])[0]

    def getDouble(self, offset=0):
        return struct.unpack('{}d'.format(self.sign),
                             self.buf[offset:offset + 8])[0]

    def getChars(self, offset=0, size=16):
        return struct.unpack('{}{}'.format(self.sign, 's' * size),
                             self.buf[offset:offset + size])

#####################################################################


class ZipSections(object):
    '''
    long centralDirectoryOffset,
    long centralDirectorySizeBytes,
    int centralDirectoryRecordCount,
    long eocdOffset,
    ByteBuffer eocd
    '''

    def __init__(self, cdStartOffset,
                 cdSizeBytes,
                 cdRecordCount,
                 eocdOffset,
                 eocd):
        self.cdStartOffset = cdStartOffset
        self.cdSizeBytes = cdSizeBytes
        self.cdRecordCount = cdRecordCount
        self.eocdOffset = eocdOffset
        self.eocd = eocd

#####################################################################


def parseValues(content):
    '''
      PLUGIN BLOCK LAYOUT
      OFFSET    DATA TYPE           DESCRIPTION
      @+0       magic string        magic string 16 bytes
      @+16      payload length      payload length int 4 bytes
      @+20      payload             payload data bytes
      @-4      payload length      same as @+16 4 bytes
    '''
    magicLen = len(PLUGIN_BLOCK_MAGIC)
    logger.debug('content:%s', content)
    if not content or len(content) < magicLen + 4 * 2:
        return None
    content = content[magicLen + 4: -4]
    values = dict(line.split(SEP_KV)
                  for line in content.split(SEP_LINE) if line.strip())
    logger.debug('values:%s', values)
    return values


def createMap(apk):
    with open(apk, "rb") as f:
        size = os.path.getsize(apk)
        offset = max(0, size - BlOCK_MAX_SIZE)
        length = min(size, BlOCK_MAX_SIZE)
        offset = offset - offset % mmap.PAGESIZE
        logger.debug('file size=%s', size)
        logger.debug('file offset=%s', offset)
        return mmap.mmap(f.fileno(),
                         length=length,
                         offset=offset,
                         access=mmap.ACCESS_READ)


def findBlockByPluginMagic(apk):
    mm = createMap(apk)
    magicLen = len(PLUGIN_BLOCK_MAGIC)
    start = mm.rfind(PLUGIN_BLOCK_MAGIC)
    if start == -1:
        return None
    d = ByteDecoder(mm)
    logger.debug('magic start offset=%s', start)
    magic = ''.join(d.getChars(start, magicLen))
    logger.debug('magic start string=%s', magic)
    payloadLen = d.getInt(start + magicLen)
    logger.debug('magic payloadLen1=%s', payloadLen)

    end = start + magicLen + 4 + payloadLen + 4
    logger.debug('magic end offset=%s', end)
    logger.debug('magic payloadLen2=%s', d.getInt(end - 4))

    block = mm[start:end]
    mm.close()
    return block


def findBlockBySigningMagic(apk):
    # search APK Signing Block Magic words
    signingBlock = findBySigningMagic(apk)
    if signingBlock:
        return parseApkSigningBlock(signingBlock, PLUGIN_BLOCK_ID)


def findBlockByZipSections(apk):
    # find zip centralDirectory, then find apkSigningBlock
    signingBlock = findByZipSections(apk)
    if signingBlock:
        return parseApkSigningBlock(signingBlock, PLUGIN_BLOCK_ID)


def findBySigningMagic(apk):
    # findApkSigningBlockUsingSigningMagic
    mm = createMap(apk)
    index = mm.rfind(APK_SIG_BLOCK_MAGIC)
    if index == -1:
        raise MagicNotFoundException(
            'APK Signing Block Magic not found')
    d = ByteDecoder(mm)
    logger.debug('magic index=%s', index)
    logger.debug('magic string=%s', ''.join(d.getChars(index, 16)))
    bEnd = index + 16
    logger.debug('block end=%s', bEnd)
    bSize = d.getLong(bEnd - 24) + 8
    logger.debug('block size=%s', bSize)
    bStart = bEnd - bSize
    logger.debug('block start=%s', bStart)
    block = mm[bStart:bEnd]
    mm.close()
    return block


def findByZipSections(apk):
    # findApkSigningBlockUsingZipSections
    with open(apk, "rb") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        sections = findZipSections(mm)

        centralDirStartOffset = sections.cdStartOffset
        centralDirEndOffset = centralDirStartOffset + sections.cdSizeBytes
        eocdStartOffset = sections.eocdOffset
        logger.debug('centralDirStartOffset:%s', centralDirStartOffset)
        logger.debug('centralDirEndOffset:%s', centralDirEndOffset)
        logger.debug('eocdStartOffset:%s', eocdStartOffset)
        if centralDirEndOffset != eocdStartOffset:
            raise SignatureNotFoundException(
                "ZIP Central Directory is not "
                "immediately followed by "
                "End of Central Directory. CD end: {} eocd start: {}"
                .format(centralDirEndOffset, eocdStartOffset))
        if centralDirStartOffset < APK_SIG_BLOCK_MIN_SIZE:
            raise SignatureNotFoundException(
                "APK too small for APK Signing Block. "
                "ZIP Central Directory offset:{} "
                .format(centralDirStartOffset))

        fStart = centralDirStartOffset - 24
        mStart = centralDirStartOffset - 16
        fEnd = centralDirStartOffset
        logger.debug('fStart:%s', fStart)
        logger.debug('mStart:%s', mStart)
        logger.debug('fEnd:%s', fEnd)
        footer = mm[fStart:fEnd]
        footerSize = len(footer)
        # logger.debug('footer:%s',to_hex(footer))
        fd = ByteDecoder(footer)
        magic = ''.join(fd.getChars(8, 16))
        # logger.debug('magic str:%s', magic)
        lo = fd.getLong(8)
        hi = fd.getLong(16)
        logger.debug('magic lo:%s', hex(lo))
        logger.debug('magic hi:%s', hex(hi))

        if magic != APK_SIG_BLOCK_MAGIC:
            raise SignatureNotFoundException(
                "No APK Signing Block before ZIP Central Directory")
        # if lo != APK_SIG_BLOCK_MAGIC_LO or hi != APK_SIG_BLOCK_MAGIC_HI:
        #     raise SignatureNotFoundException(
        #         "No APK Signing Block before ZIP Central Directory")

        apkSigBlockSizeInFooter = fd.getLong(0)
        logger.debug('apkSigBlockSizeInFooter:%s', apkSigBlockSizeInFooter)

        if apkSigBlockSizeInFooter < footerSize or \
                apkSigBlockSizeInFooter > sys.maxsize - 8:
            raise SignatureNotFoundException(
                "APK Signing Block size out of range: {}"
                .format(apkSigBlockSizeInFooter))

        totalSize = apkSigBlockSizeInFooter + 8
        logger.debug('totalSize:%s', totalSize)
        apkSigBlockOffset = centralDirStartOffset - totalSize
        logger.debug('apkSigBlockOffset:%s', apkSigBlockOffset)

        if apkSigBlockOffset < 0:
            raise SignatureNotFoundException(
                "APK Signing Block offset out of range: " + apkSigBlockOffset)

        apkSigBlock = mm[apkSigBlockOffset:apkSigBlockOffset + 8]
        # logger.debug('apkSigBlock:%s', to_hex(apkSigBlock))
        apkSigBlockSizeInHeader = ByteDecoder(apkSigBlock).getLong(0)
        logger.debug('apkSigBlockSizeInHeader:%s', apkSigBlockSizeInHeader)

        if apkSigBlockSizeInHeader != apkSigBlockSizeInFooter:
            raise SignatureNotFoundException(
                "APK Signing Block sizes in header and"
                "footer do not match: {} vs {}"
                .format(apkSigBlockSizeInHeader, apkSigBlockSizeInFooter))

        block = mm[apkSigBlockOffset:apkSigBlockOffset + totalSize]
        mm.close()
        return block


def parseApkSigningBlock(block, blockId):
    # parseApkSigningBlock
    if not block or not blockId:
        return None
    '''
        // APK Signing Block
        // FORMAT:
        // OFFSET       DATA TYPE  DESCRIPTION
        // * @+0  bytes uint64:    size in bytes(excluding this field)
        // * @+8  bytes payload
        // * @-24 bytes uint64:    size in bytes(same as the one above)
        // * @-16 bytes uint128:   magic
    '''
    totalSize = len(block)
    bd0 = ByteDecoder(block)
    blockSizeInHeader = bd0.getULong(0)
    logger.debug('blockSizeInHeader:%s', blockSizeInHeader)
    blockSizeInFooter = bd0.getULong(totalSize - 24)
    logger.debug('blockSizeInFooter:%s', blockSizeInFooter)
    # slice only payload
    block = block[8:-24]
    bd = ByteDecoder(block)
    size = len(block)
    logger.debug('payloadSize:%s', size)

    entryCount = 0
    position = 0
    signingBlock = None
    channelBlock = None
    while position < size:
        entryCount += 1
        logger.debug('entryCount:%s', entryCount)
        if size - position < 8:
            raise SignatureNotFoundException(
                "Insufficient data to read size "
                "of APK Signing Block entry: {}"
                .format(entryCount))
        lenLong = bd.getLong(position)
        logger.debug('lenLong:%s', lenLong)
        position += 8
        if lenLong < 4 or lenLong > sys.maxsize - 8:
            raise SignatureNotFoundException(
                "APK Signing Block entry #{} size out of range: {}"
                .format(entryCount, lenLong))
        nextEntryPos = position + lenLong
        logger.debug('nextEntryPos:%s', nextEntryPos)
        if nextEntryPos > size:
            SignatureNotFoundException(
                "APK Signing Block entry #{}, available: {}"
                .format(entryCount, (size - position)))
        sid = bd.getInt(position)
        logger.debug('blockId:%s', hex(sid))
        position += 4
        if sid == APK_SIGNATURE_SCHEME_V2_BLOCK_ID:
            logger.debug('found signingBlock')
            signingBlock = block[position:position + lenLong - 4]
            signingBlockSize = len(signingBlock)
            logger.debug('signingBlockSize:%s', signingBlockSize)
            # logger.debug('signingBlockHex:%s', to_hex(signingBlock[0:32]))
        elif sid == blockId:
            logger.debug('found pluginBlock')
            pluginBlock = block[position:position + lenLong - 4]
            pluginBlockSize = len(pluginBlock)
            logger.debug('pluginBlockSize:%s', pluginBlockSize)
            logger.debug('pluginBlock:%s', pluginBlock)
            # logger.debug('pluginBlockHex:%s', to_hex(pluginBlock))
            return pluginBlock
        else:
            logger.debug('found unknown block:%s', hex(sid))
        position = nextEntryPos


def findZipSections(mm):
    eocd = findEocdRecord(mm)
    if not eocd:
        raise ZipFormatException(
            "ZIP End of Central Directory record not found")
    eocdOffset, eocdBuf = eocd
    ed = ByteDecoder(eocdBuf)
    # logger.debug('eocdBuf:%s', to_hex(eocdBuf))
    cdStartOffset = ed.getUInt(ZIP_EOCD_CENTRAL_DIR_OFFSET_FIELD_OFFSET)
    logger.debug('cdStartOffset:%s', cdStartOffset)
    if cdStartOffset > eocdOffset:
        raise ZipFormatException(
            "ZIP Central Directory start offset out of range: {}"
            ". ZIP End of Central Directory offset: {}"
            .format(cdStartOffset, eocdOffset))
    cdSizeBytes = ed.getUInt(ZIP_EOCD_CENTRAL_DIR_SIZE_FIELD_OFFSET)
    logger.debug('cdSizeBytes:%s', cdSizeBytes)
    cdEndOffset = cdStartOffset + cdSizeBytes
    logger.debug('cdEndOffset:%s', cdEndOffset)
    if cdEndOffset > eocdOffset:
        raise ZipFormatException(
            "ZIP Central Directory overlaps with End of Central Directory"
            ". CD end: {}, EoCD start: {}"
            .format(cdEndOffset, eocdOffset))
    cdRecordCount = ed.getUShort(
        ZIP_EOCD_CENTRAL_DIR_TOTAL_RECORD_COUNT_OFFSET)
    logger.debug('cdRecordCount:%s', cdRecordCount)
    sections = ZipSections(cdStartOffset,
                           cdSizeBytes,
                           cdRecordCount,
                           eocdOffset,
                           eocdBuf)
    return sections


def findEocdRecord(mm):
    fileSize = mm.size()
    logger.debug('fileSize:%s', fileSize)
    if fileSize < ZIP_EOCD_REC_MIN_SIZE:
        return None

    # 99.99% of APKs have a zero-length comment field
    maxCommentSize = min(UINT16_MAX_VALUE, fileSize - ZIP_EOCD_REC_MIN_SIZE)
    maxEocdSize = ZIP_EOCD_REC_MIN_SIZE + maxCommentSize
    logger.debug('maxCommentSize:%s', maxCommentSize)
    logger.debug('maxEocdSize:%s', maxEocdSize)
    bufOffsetInFile = fileSize - maxEocdSize
    logger.debug('bufOffsetInFile:%s', bufOffsetInFile)
    buf = mm[bufOffsetInFile:bufOffsetInFile + maxEocdSize]
    # logger.debug('buf:%s',to_hex(buf))
    eocdOffsetInBuf = findEocdStartOffset(buf)
    logger.debug('eocdOffsetInBuf:%s', eocdOffsetInBuf)
    if eocdOffsetInBuf != -1:
        return bufOffsetInFile + eocdOffsetInBuf, buf[eocdOffsetInBuf:]


def findEocdStartOffset(buf):
    archiveSize = len(buf)
    logger.debug('archiveSize:%s', archiveSize)
    maxCommentLength = min(
        archiveSize - ZIP_EOCD_REC_MIN_SIZE, UINT16_MAX_VALUE)
    logger.debug('maxCommentLength:%s', maxCommentLength)
    eocdEmptyCommentStartPos = archiveSize - ZIP_EOCD_REC_MIN_SIZE
    logger.debug('eocdEmptyCommentStartPos:%s',
                 eocdEmptyCommentStartPos)
    expectedCommentLength = 0
    eocdOffsetInBuf = -1
    while expectedCommentLength <= maxCommentLength:
        eocdStartPos = eocdEmptyCommentStartPos - expectedCommentLength
        logger.debug('expectedCommentLength:%s', expectedCommentLength)
        # logger.debug('eocdStartPos:%s', eocdStartPos)
        seg = ByteDecoder(buf).getInt(eocdStartPos)
        logger.debug('seg:%s', hex(seg))
        if seg == ZIP_EOCD_REC_SIG:
            actualCommentLength = ByteDecoder(buf).getUShort(
                eocdStartPos + ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET)
            logger.debug('actualCommentLength:%s', actualCommentLength)
            if actualCommentLength == expectedCommentLength:
                logger.debug('found eocdStartPos:%s', eocdStartPos)
                return eocdStartPos
        expectedCommentLength += 1
    return -1


#####################################################################


def timeit(method):

    def timed(*args, **kw):
        ts = time.time() * 1000
        result = method(*args, **kw)
        te = time.time() * 1000

        print('%s() executed in %.2f msec' % (method.__name__, te - ts))
        return result

    return timed


def to_hex(s):
    return " ".join("{:02x}".format(ord(c)) for c in s) if s else ""


def getChannel(apk):
    apk = os.path.abspath(apk)
    logger.debug('apk:%s', apk)
    try:
        zp = zipfile.ZipFile(apk)
        zp.testzip()
        content = findBlockByZipSections(apk)
        values = parseValues(content)
        if values:
            channel = values.get(PLUGIN_CHANNEL_KEY)
            logger.debug('channel:%s', channel)
            return channel
        else:
            logger.debug('channel not found')
    except Exception as e:
        logger.error('%s: %s', type(e).__name__, e)


def showInfo(apk):
    try:
        from apkinfo import APK
        info = APK(apk)
        print('Package: \t{}'.format(info.get_package()))
        print('Version: \t{}'.format(info.get_version_name()))
        print('Build: \t\t{}'.format(info.get_version_code()))
        print('File: \t\t{}'.format(os.path.basename(apk)))
        print('Size: \t\t{}'.format(os.path.getsize(apk)))
    except Exception as e:
        pass


def main():
    logger.debug('AUTHOR:%s', AUTHOR)
    logger.debug('VERSION:%s', VERSION)
    prog = os.path.basename(sys.argv[0])
    if len(sys.argv) < 2:
        print('Usage: {} app.apk'.format(prog))
        sys.exit(1)
    apk = os.path.abspath(sys.argv[1])
    channel = getChannel(apk)
    print('Channel: \t{}'.format(channel))
    showInfo(apk)


if __name__ == '__main__':
    main()
