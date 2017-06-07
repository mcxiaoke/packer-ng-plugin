# -*- coding: utf-8 -*-
# @Author: mcxiaoke
# @Date:   2017-06-06 14:03:18
# @Last Modified by:   mcxiaoke
# @Last Modified time: 2017-06-07 11:33:29
from __future__ import print_function
import os
import sys
import mmap
import struct

# ref: https://android.googlesource.com/platform/tools/apksig/+/master
ZIP_EOCD_REC_MIN_SIZE = 22
ZIP_EOCD_REC_SIG = 0x06054b50
ZIP_EOCD_CENTRAL_DIR_TOTAL_RECORD_COUNT_OFFSET = 10
ZIP_EOCD_CENTRAL_DIR_SIZE_FIELD_OFFSET = 12
ZIP_EOCD_CENTRAL_DIR_OFFSET_FIELD_OFFSET = 16
ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET = 20
ZIP_EOCD_COMMENT_MIN_LENGTH = 0

UINT16_MAX_VALUE = 0xffff  # 65535

APK_SIG_BLOCK_MAGIC_HI = 0x3234206b636f6c42
APK_SIG_BLOCK_MAGIC_LO = 0x20676953204b5041
APK_SIG_BLOCK_MIN_SIZE = 32
APK_SIGNATURE_SCHEME_V2_BLOCK_ID = 0x7109871a

# channel info key
PLUGIN_CHANNEL_KEY = 'zKey'  # 0x7a4b6579
# channel extra key
PLUGIN_EXTRA_KEY = 'zExt'  # 0x7a457874
# channel date key
PLUGIN_DATE_KEY = 'zDat'  # 0x7a446174
# plugin block id
PLUGIN_BLOCK_ID = 0x7a786b21  # "zxk!"

SEP_KV = '∘'
SEP_LINE = '∙'

AUTHOR = 'mcxiaoke'
VERSION = '1.0.0'
try:
    props = dict(line.strip().split('=') for line in open('../gradle.properties') if line.strip())
    VERSION = props.get('VERSION_NAME')
except Exception as e:
    VERSION = '1.0.0'

print('AUTHOR:', AUTHOR)
print('VERSION:', VERSION)

APK1 = 'apks/Cat/packer-ng-release-v1.7.1-SNAPSHOT-田园猫.apk'
APK2 = 'apks/Cat/packer-ng-release-v1.7.1-SNAPSHOT-Special@Cat%001.apk'
APK3 = 'apks/Fish/packer-ng-release-v1.7.1-SNAPSHOT-2017年.apk'
APK4 = 'apks/sample-Cat-release.apk'

APK = APK1


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


def to_hex(s):
    return " ".join("{:02x}".format(ord(c)) for c in s)


def show_info(apk):
    with open(apk, "r+b") as f:
        mm = mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ)
        fileSize = mm.size()
        print('fileSize:', fileSize)
        # 99.99% of APKs have a zero-length comment field
        maxCommentSize = min(UINT16_MAX_VALUE, fileSize - ZIP_EOCD_REC_MIN_SIZE)
        maxEocdSize = ZIP_EOCD_REC_MIN_SIZE + maxCommentSize
        print('maxCommentSize:', maxCommentSize)
        print('maxEocdSize:', maxEocdSize)
        bufOffsetInFile = fileSize - maxEocdSize
        print('bufOffsetInFile:', bufOffsetInFile)
        # buf = zip.getByteBuffer(bufOffsetInFile, maxEocdSize)
        buf = mm[bufOffsetInFile:bufOffsetInFile+maxEocdSize]
        # print('buf:',to_hex(buf))
        archiveSize = len(buf)
        print('archiveSize:', archiveSize)
        maxCommentLength = min(archiveSize - ZIP_EOCD_REC_MIN_SIZE, UINT16_MAX_VALUE)
        print('maxCommentLength:', maxCommentLength)
        eocdWithEmptyCommentStartPosition = archiveSize - ZIP_EOCD_REC_MIN_SIZE
        print('eocdWithEmptyCommentStartPosition:', eocdWithEmptyCommentStartPosition)

        '''
        for (int expectedCommentLength = 0; expectedCommentLength <= maxCommentLength;
                expectedCommentLength++) {
            int eocdStartPos = eocdWithEmptyCommentStartPosition - expectedCommentLength;
            if (zipContents.getInt(eocdStartPos) == ZIP_EOCD_REC_SIG) {
                int actualCommentLength =
                        getUnsignedInt16(
                                zipContents, eocdStartPos + ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET);
                if (actualCommentLength == expectedCommentLength) {
                    return eocdStartPos;
                }
            }
        }
        '''
        expectedCommentLength = 0
        eocdOffsetInBuf = -1
        while expectedCommentLength <= maxCommentLength:
            eocdStartPos = eocdWithEmptyCommentStartPosition - expectedCommentLength
            print('expectedCommentLength:', expectedCommentLength)
            print('eocdStartPos:', eocdStartPos)
            print('unpack:', to_hex(buf[eocdStartPos:eocdStartPos+4]))
            seg = struct.unpack('<i', buf[eocdStartPos:eocdStartPos+4])
            print('seg:', hex(seg[0]))
            if seg[0] == ZIP_EOCD_REC_SIG:
                actualCommentLength = struct.unpack('<H', buf[eocdStartPos + ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET:eocdStartPos + ZIP_EOCD_COMMENT_LENGTH_FIELD_OFFSET+2])
                print('actualCommentLength:', actualCommentLength)
                if actualCommentLength[0] == expectedCommentLength:
                    eocdOffsetInBuf = eocdStartPos
                    break
            expectedCommentLength += 1
        print('eocdOffsetInBuf:', eocdOffsetInBuf)
        if eocdOffsetInBuf != -1:
            eocdOffset = bufOffsetInFile + eocdOffsetInBuf
            print('eocdOffset:', eocdOffset)
            eocdBuf = buf[eocdOffsetInBuf:]
            # print('eocdBuf:', to_hex(eocdBuf))
            cdso = struct.unpack('<I', eocdBuf[ZIP_EOCD_CENTRAL_DIR_OFFSET_FIELD_OFFSET:ZIP_EOCD_CENTRAL_DIR_OFFSET_FIELD_OFFSET+4])
            cdStartOffset = cdso[0]
            print('cdStartOffset', cdStartOffset)
            cdsb = struct.unpack('<I', eocdBuf[ZIP_EOCD_CENTRAL_DIR_SIZE_FIELD_OFFSET:ZIP_EOCD_CENTRAL_DIR_SIZE_FIELD_OFFSET+4])
            cdSizeBytes = cdsb[0]
            print('cdSizeBytes', cdSizeBytes)
            cdEndOffset = cdStartOffset + cdSizeBytes
            print('cdEndOffset', cdEndOffset)
            cdrc = struct.unpack('<H', eocdBuf[ZIP_EOCD_CENTRAL_DIR_TOTAL_RECORD_COUNT_OFFSET:ZIP_EOCD_CENTRAL_DIR_TOTAL_RECORD_COUNT_OFFSET+2])
            cdRecordCount = cdrc[0]
            print('cdRecordCount', cdRecordCount)
            sections = ZipSections(cdStartOffset,
                                   cdSizeBytes,
                                   cdRecordCount,
                                   eocdOffset,
                                   eocdBuf)

            centralDirStartOffset = sections.cdStartOffset
            centralDirEndOffset = centralDirStartOffset + sections.cdSizeBytes
            eocdStartOffset = sections.eocdOffset
            print('centralDirStartOffset:', centralDirStartOffset)
            print('centralDirEndOffset:', centralDirEndOffset)
            print('eocdStartOffset:', eocdStartOffset)
            if centralDirEndOffset == eocdStartOffset:
                if centralDirStartOffset >= APK_SIG_BLOCK_MIN_SIZE:
                    fStart = centralDirStartOffset-24
                    fEnd = centralDirStartOffset
                    footer = mm[fStart:fEnd]
                    footerSize = len(footer)
                    # print('footer:',to_hex(footer))
                    mlo = struct.unpack('<q', footer[8:16])
                    mhi = struct.unpack('<q', footer[16:24])
                    lo = mlo[0]
                    hi = mhi[0]
                    print('magic lo:', hex(lo))
                    print('magic hi:', hex(hi))
                    if lo == APK_SIG_BLOCK_MAGIC_LO and hi == APK_SIG_BLOCK_MAGIC_HI:
                        asbf = struct.unpack('<q', footer[0:8])
                        apkSigBlockSizeInFooter = asbf[0]
                        print('apkSigBlockSizeInFooter:', apkSigBlockSizeInFooter)
                        if apkSigBlockSizeInFooter >= footerSize and apkSigBlockSizeInFooter < sys.maxint - 8:
                            totalSize = apkSigBlockSizeInFooter + 8
                            print('totalSize:', totalSize)
                            apkSigBlockOffset = centralDirStartOffset - totalSize
                            print('apkSigBlockOffset:', apkSigBlockOffset)
                            if apkSigBlockOffset >= 0:
                                apkSigBlock = mm[apkSigBlockOffset:apkSigBlockOffset+8]
                                # print('apkSigBlock:', to_hex(apkSigBlock))
                                asbh = struct.unpack('<q', apkSigBlock[0:8])
                                apkSigBlockSizeInHeader = asbh[0]
                                print('apkSigBlockSizeInHeader:', apkSigBlockSizeInHeader)
                                if apkSigBlockSizeInHeader == apkSigBlockSizeInFooter:
                                    apkSigningBlock = mm[apkSigBlockOffset:apkSigBlockOffset+totalSize]
                                    apkSigningBlockOffset = apkSigBlockOffset
                                    # ByteBuffer pairs = sliceFromTo(apkSigningBlock, 8, apkSigningBlock.capacity() - 24);
                                    pairs = apkSigningBlock[8:-24]
                                    pairsSize = len(pairs)
                                    print('pairsSize:', pairsSize)

                                    entryCount = 0
                                    position = 0
                                    signingBlock = None
                                    channelBlock = None
                                    while position < pairsSize:
                                        entryCount += 1
                                        print('entryCount', entryCount)
                                        if pairsSize - position < 8:
                                            print('Insufficient data to read size of APK Signing Block entry')
                                            break
                                        lenLong = struct.unpack('<q', pairs[position:position+8])[0]
                                        print('lenLong', lenLong)
                                        position += 8
                                        if lenLong < 4 or lenLong > sys.maxint - 8:
                                            print('APK Signing Block entry size out of range 1')
                                            break
                                        nextEntryPos = position + lenLong
                                        print('nextEntryPos', nextEntryPos)
                                        if nextEntryPos > pairsSize:
                                            print('APK Signing Block entry size out of range 2')
                                            break
                                        sid = struct.unpack('<i', pairs[position:position+4])[0]
                                        print('sid', hex(sid))
                                        position += 4
                                        if sid == APK_SIGNATURE_SCHEME_V2_BLOCK_ID:
                                            signingBlock = pairs[position:position+lenLong-4]
                                            signingBlockSize = len(signingBlock)
                                            print('signingBlockSize:', signingBlockSize)
                                        elif sid == PLUGIN_BLOCK_ID:
                                            channelBlock = pairs[position:position+lenLong-4]
                                            channelBlockSize = len(channelBlock)
                                            print('channelBlockSize:', channelBlockSize)
                                            print('channelKey:', to_hex(PLUGIN_CHANNEL_KEY))
                                            print('channelBlock:', channelBlock)
                                            print('channelBlockHex:', to_hex(channelBlock))
                                            values = dict(line.split(SEP_KV) for line in channelBlock.split(SEP_LINE) if line.strip())
                                            print('values:', values)
                                            print('channel:', values.get(PLUGIN_CHANNEL_KEY))
                                        position = nextEntryPos

                                else:
                                    print('APK Signing Block sizes in header and footer do not match')
                            else:
                                print('APK Signing Block offset out of range')
                        else:
                            print('APK Signing Block size out of range')
                    else:
                        print('No APK Signing Block before ZIP Central Directory')
                else:
                    print('APK too small for APK Signing Block')
            else:
                # error
                print('ZIP Central Directory is not immediately followed by End of Central Directory')
        else:
            eocdOffset = -1
            eocdBuf = None
            print('eocd start offset not found.')


if __name__ == '__main__':
    show_info(APK)
