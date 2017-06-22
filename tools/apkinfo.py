# This file is part of Androguard.
#
# Copyright (C) 2012, Anthony Desnos <desnos at t0t0.fr>
# All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS-IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import StringIO
from struct import pack, unpack
from xml.sax.saxutils import escape
from zlib import crc32
import re
import collections
import sys
import os
import logging
import types
import random
import string
import imp

from xml.dom import minidom

NS_ANDROID_URI = 'http://schemas.android.com/apk/res/android'

ZIPMODULE = 1


def read(filename, binary=True):
    with open(filename, 'rb' if binary else 'r') as f:
        return f.read()


def sign_apk(filename, keystore, storepass):
    from subprocess import Popen, PIPE, STDOUT
    compile = Popen([CONF["PATH_JARSIGNER"], "-sigalg", "MD5withRSA",
                     "-digestalg", "SHA1", "-storepass", storepass, "-keystore",
                     keystore, filename, "alias_name"],
                    stdout=PIPE,
                    stderr=STDOUT)
    stdout, stderr = compile.communicate()


class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class FileNotPresent(Error):
    pass


######################################################## APK FORMAT ########################################################
class APK(object):
    """
        This class can access to all elements in an APK file

        :param filename: specify the path of the file, or raw data
        :param raw: specify if the filename is a path or raw data (optional)
        :param mode: specify the mode to open the file (optional)
        :param magic_file: specify the magic file (optional)
        :param zipmodule: specify the type of zip module to use (0:chilkat, 1:zipfile, 2:patch zipfile)

        :type filename: string
        :type raw: boolean
        :type mode: string
        :type magic_file: string
        :type zipmodule: int

        :Example:
          APK("myfile.apk")
          APK(read("myfile.apk"), raw=True)
    """

    def __init__(self,
                 filename,
                 raw=False,
                 mode="r",
                 magic_file=None,
                 zipmodule=ZIPMODULE):
        self.filename = filename

        self.xml = {}
        self.axml = {}
        self.arsc = {}

        self.package = ""
        self.androidversion = {}
        self.permissions = []
        self.declared_permissions = {}
        self.valid_apk = False

        self.files = {}
        self.files_crc32 = {}

        self.magic_file = magic_file

        if raw is True:
            self.__raw = filename
        else:
            self.__raw = read(filename)

        self.zipmodule = zipmodule

        if zipmodule == 0:
            self.zip = ChilkatZip(self.__raw)
        elif zipmodule == 2:
            from androguard.patch import zipfile
            self.zip = zipfile.ZipFile(StringIO.StringIO(self.__raw), mode=mode)
        else:
            import zipfile
            self.zip = zipfile.ZipFile(StringIO.StringIO(self.__raw), mode=mode)

        for i in self.zip.namelist():
            if i == "AndroidManifest.xml":
                self.axml[i] = AXMLPrinter(self.zip.read(i))
                try:
                    self.xml[i] = minidom.parseString(self.axml[i].get_buff())
                except:
                    self.xml[i] = None

                if self.xml[i] != None:
                    self.package = self.xml[i].documentElement.getAttribute(
                        "package")
                    self.androidversion[
                        "Code"
                    ] = self.xml[i].documentElement.getAttributeNS(
                        NS_ANDROID_URI, "versionCode")
                    self.androidversion[
                        "Name"
                    ] = self.xml[i].documentElement.getAttributeNS(
                        NS_ANDROID_URI, "versionName")

                    self.valid_apk = True

    def get_AndroidManifest(self):
        """
            Return the Android Manifest XML file

            :rtype: xml object
        """
        return self.xml["AndroidManifest.xml"]

    def is_valid_APK(self):
        """
            Return true if the APK is valid, false otherwise

            :rtype: boolean
        """
        return self.valid_apk

    def get_filename(self):
        """
            Return the filename of the APK

            :rtype: string
        """
        return self.filename

    def get_package(self):
        """
            Return the name of the package

            :rtype: string
        """
        return self.package

    def get_version_code(self):
        """
            Return the android version code

            :rtype: string
        """
        return self.androidversion["Code"]

    def get_version_name(self):
        """
            Return the android version name

            :rtype: string
        """
        return self.androidversion["Name"]

    def get_raw(self):
        """
            Return raw bytes of the APK

            :rtype: string
        """
        return self.__raw

    def get_elements(self, tag_name, attribute):
        """
            Return elements in xml files which match with the tag name and the specific attribute

            :param tag_name: a string which specify the tag name
            :param attribute: a string which specify the attribute
        """
        l = []
        for i in self.xml:
            for item in self.xml[i].getElementsByTagName(tag_name):
                value = item.getAttributeNS(NS_ANDROID_URI, attribute)
                value = self.format_value(value)

                l.append(str(value))
        return l

    def format_value(self, value):
        if len(value) > 0:
            if value[0] == ".":
                value = self.package + value
            else:
                v_dot = value.find(".")
                if v_dot == 0:
                    value = self.package + "." + value
                elif v_dot == -1:
                    value = self.package + "." + value
        return value

    def get_element(self, tag_name, attribute, **attribute_filter):
        """
            Return element in xml files which match with the tag name and the specific attribute

            :param tag_name: specify the tag name
            :type tag_name: string
            :param attribute: specify the attribute
            :type attribute: string

            :rtype: string
        """
        for i in self.xml:
            for item in self.xml[i].getElementsByTagName(tag_name):
                skip_this_item = False
                for attr, val in attribute_filter.items():
                    attr_val = item.getAttributeNS(NS_ANDROID_URI, attr)
                    if attr_val != val:
                        skip_this_item = True
                        break

                if skip_this_item:
                    continue

                value = item.getAttributeNS(NS_ANDROID_URI, attribute)

                if len(value) > 0:
                    return value
        return None

    def get_max_sdk_version(self):
        """
            Return the android:maxSdkVersion attribute

            :rtype: string
        """
        return self.get_element("uses-sdk", "maxSdkVersion")

    def get_min_sdk_version(self):
        """
            Return the android:minSdkVersion attribute

            :rtype: string
        """
        return self.get_element("uses-sdk", "minSdkVersion")

    def get_target_sdk_version(self):
        """
            Return the android:targetSdkVersion attribute

            :rtype: string
        """
        return self.get_element("uses-sdk", "targetSdkVersion")

    def get_android_manifest_axml(self):
        """
            Return the :class:`AXMLPrinter` object which corresponds to the AndroidManifest.xml file

            :rtype: :class:`AXMLPrinter`
        """
        try:
            return self.axml["AndroidManifest.xml"]
        except KeyError:
            return None

    def get_android_manifest_xml(self):
        """
            Return the xml object which corresponds to the AndroidManifest.xml file

            :rtype: object
        """
        try:
            return self.xml["AndroidManifest.xml"]
        except KeyError:
            return None

    def show(self):

        print "PACKAGE: ", self.get_package()
        print "VERSION NAME:", self.get_version_name()
        print "VERSION CODE:", self.get_version_code()

################################## AXML FORMAT ########################################
# Translated from
# http://code.google.com/p/android4me/source/browse/src/android/content/res/AXmlResourceParser.java

UTF8_FLAG = 0x00000100
CHUNK_STRINGPOOL_TYPE = 0x001C0001
CHUNK_NULL_TYPE = 0x00000000


class StringBlock(object):

    def __init__(self, buff):
        self.start = buff.get_idx()
        self._cache = {}
        self.header_size, self.header = self.skipNullPadding(buff)

        self.chunkSize = unpack('<i', buff.read(4))[0]
        self.stringCount = unpack('<i', buff.read(4))[0]
        self.styleOffsetCount = unpack('<i', buff.read(4))[0]

        self.flags = unpack('<i', buff.read(4))[0]
        self.m_isUTF8 = ((self.flags & UTF8_FLAG) != 0)

        self.stringsOffset = unpack('<i', buff.read(4))[0]
        self.stylesOffset = unpack('<i', buff.read(4))[0]

        self.m_stringOffsets = []
        self.m_styleOffsets = []
        self.m_charbuff = ""
        self.m_styles = []

        for i in range(0, self.stringCount):
            self.m_stringOffsets.append(unpack('<i', buff.read(4))[0])

        for i in range(0, self.styleOffsetCount):
            self.m_styleOffsets.append(unpack('<i', buff.read(4))[0])

        size = self.chunkSize - self.stringsOffset
        if self.stylesOffset != 0:
            size = self.stylesOffset - self.stringsOffset

        # FIXME
        if (size % 4) != 0:
            warning("ooo")

        self.m_charbuff = buff.read(size)

        if self.stylesOffset != 0:
            size = self.chunkSize - self.stylesOffset

            # FIXME
            if (size % 4) != 0:
                warning("ooo")

            for i in range(0, size / 4):
                self.m_styles.append(unpack('<i', buff.read(4))[0])

    def skipNullPadding(self, buff):

        def readNext(buff, first_run=True):
            header = unpack('<i', buff.read(4))[0]

            if header == CHUNK_NULL_TYPE and first_run:
                info("Skipping null padding in StringBlock header")
                header = readNext(buff, first_run=False)
            elif header != CHUNK_STRINGPOOL_TYPE:
                warning("Invalid StringBlock header")

            return header

        header = readNext(buff)
        return header >> 8, header & 0xFF

    def getString(self, idx):
        if idx in self._cache:
            return self._cache[idx]

        if idx < 0 or not self.m_stringOffsets or idx >= len(
                self.m_stringOffsets):
            return ""

        offset = self.m_stringOffsets[idx]

        if self.m_isUTF8:
            self._cache[idx] = self.decode8(offset)
        else:
            self._cache[idx] = self.decode16(offset)

        return self._cache[idx]

    def getStyle(self, idx):
        # FIXME
        return self.m_styles[idx]

    def decode8(self, offset):
        str_len, skip = self.decodeLength(offset, 1)
        offset += skip

        encoded_bytes, skip = self.decodeLength(offset, 1)
        offset += skip

        data = self.m_charbuff[offset: offset + encoded_bytes]

        return self.decode_bytes(data, 'utf-8', str_len)

    def decode16(self, offset):
        str_len, skip = self.decodeLength(offset, 2)
        offset += skip

        encoded_bytes = str_len * 2

        data = self.m_charbuff[offset: offset + encoded_bytes]

        return self.decode_bytes(data, 'utf-16', str_len)

    def decode_bytes(self, data, encoding, str_len):
        string = data.decode(encoding, 'replace')
        if len(string) != str_len:
            warning("invalid decoded string length")
        return string

    def decodeLength(self, offset, sizeof_char):
        length = ord(self.m_charbuff[offset])

        sizeof_2chars = sizeof_char << 1
        fmt_chr = 'B' if sizeof_char == 1 else 'H'
        fmt = "<2" + fmt_chr

        length1, length2 = unpack(fmt, self.m_charbuff[offset:(offset + sizeof_2chars)])

        highbit = 0x80 << (8 * (sizeof_char - 1))

        if (length & highbit) != 0:
            return ((length1 & ~highbit) << (8 * sizeof_char)) | length2, sizeof_2chars
        else:
            return length1, sizeof_char

    def show(self):
        print "StringBlock(%x, %x, %x, %x, %x, %x" % (
            self.start,
            self.header,
            self.header_size,
            self.chunkSize,
            self.stringsOffset,
            self.flags)
        for i in range(0, len(self.m_stringOffsets)):
            print i, repr(self.getString(i))

START_DOCUMENT = 0
END_DOCUMENT = 1
START_TAG = 2
END_TAG = 3
TEXT = 4

ATTRIBUTE_IX_NAMESPACE_URI = 0
ATTRIBUTE_IX_NAME = 1
ATTRIBUTE_IX_VALUE_STRING = 2
ATTRIBUTE_IX_VALUE_TYPE = 3
ATTRIBUTE_IX_VALUE_DATA = 4
ATTRIBUTE_LENGHT = 5

CHUNK_AXML_FILE = 0x00080003
CHUNK_RESOURCEIDS = 0x00080180
CHUNK_XML_FIRST = 0x00100100
CHUNK_XML_START_NAMESPACE = 0x00100100
CHUNK_XML_END_NAMESPACE = 0x00100101
CHUNK_XML_START_TAG = 0x00100102
CHUNK_XML_END_TAG = 0x00100103
CHUNK_XML_TEXT = 0x00100104
CHUNK_XML_LAST = 0x00100104


class AXMLParser(object):

    def __init__(self, raw_buff):
        self.reset()

        self.valid_axml = True
        self.buff = BuffHandle(raw_buff)

        axml_file = unpack('<L', self.buff.read(4))[0]

        if axml_file == CHUNK_AXML_FILE:
            self.buff.read(4)

            self.sb = StringBlock(self.buff)

            self.m_resourceIDs = []
            self.m_prefixuri = {}
            self.m_uriprefix = {}
            self.m_prefixuriL = []

            self.visited_ns = []
        else:
            self.valid_axml = False
            warning("Not a valid xml file")

    def is_valid(self):
        return self.valid_axml

    def reset(self):
        self.m_event = -1
        self.m_lineNumber = -1
        self.m_name = -1
        self.m_namespaceUri = -1
        self.m_attributes = []
        self.m_idAttribute = -1
        self.m_classAttribute = -1
        self.m_styleAttribute = -1

    def next(self):
        self.doNext()
        return self.m_event

    def doNext(self):
        if self.m_event == END_DOCUMENT:
            return

        event = self.m_event

        self.reset()
        while True:
            chunkType = -1

            # Fake END_DOCUMENT event.
            if event == END_TAG:
                pass

            # START_DOCUMENT
            if event == START_DOCUMENT:
                chunkType = CHUNK_XML_START_TAG
            else:
                if self.buff.end():
                    self.m_event = END_DOCUMENT
                    break
                chunkType = unpack('<L', self.buff.read(4))[0]

            if chunkType == CHUNK_RESOURCEIDS:
                chunkSize = unpack('<L', self.buff.read(4))[0]
                # FIXME
                if chunkSize < 8 or chunkSize % 4 != 0:
                    warning("Invalid chunk size")

                for i in range(0, chunkSize / 4 - 2):
                    self.m_resourceIDs.append(
                        unpack('<L', self.buff.read(4))[0])

                continue

            # FIXME
            if chunkType < CHUNK_XML_FIRST or chunkType > CHUNK_XML_LAST:
                warning("invalid chunk type")

            # Fake START_DOCUMENT event.
            if chunkType == CHUNK_XML_START_TAG and event == -1:
                self.m_event = START_DOCUMENT
                break

            self.buff.read(4)  # /*chunkSize*/
            lineNumber = unpack('<L', self.buff.read(4))[0]
            self.buff.read(4)  # 0xFFFFFFFF

            if chunkType == CHUNK_XML_START_NAMESPACE or chunkType == CHUNK_XML_END_NAMESPACE:
                if chunkType == CHUNK_XML_START_NAMESPACE:
                    prefix = unpack('<L', self.buff.read(4))[0]
                    uri = unpack('<L', self.buff.read(4))[0]

                    self.m_prefixuri[prefix] = uri
                    self.m_uriprefix[uri] = prefix
                    self.m_prefixuriL.append((prefix, uri))
                    self.ns = uri
                else:
                    self.ns = -1
                    self.buff.read(4)
                    self.buff.read(4)
                    (prefix, uri) = self.m_prefixuriL.pop()

                continue

            self.m_lineNumber = lineNumber

            if chunkType == CHUNK_XML_START_TAG:
                self.m_namespaceUri = unpack('<L', self.buff.read(4))[0]
                self.m_name = unpack('<L', self.buff.read(4))[0]

                # FIXME
                self.buff.read(4)  # flags

                attributeCount = unpack('<L', self.buff.read(4))[0]
                self.m_idAttribute = (attributeCount >> 16) - 1
                attributeCount = attributeCount & 0xFFFF
                self.m_classAttribute = unpack('<L', self.buff.read(4))[0]
                self.m_styleAttribute = (self.m_classAttribute >> 16) - 1

                self.m_classAttribute = (self.m_classAttribute & 0xFFFF) - 1

                for i in range(0, attributeCount * ATTRIBUTE_LENGHT):
                    self.m_attributes.append(unpack('<L', self.buff.read(4))[0])

                for i in range(ATTRIBUTE_IX_VALUE_TYPE, len(self.m_attributes),
                               ATTRIBUTE_LENGHT):
                    self.m_attributes[i] = self.m_attributes[i] >> 24

                self.m_event = START_TAG
                break

            if chunkType == CHUNK_XML_END_TAG:
                self.m_namespaceUri = unpack('<L', self.buff.read(4))[0]
                self.m_name = unpack('<L', self.buff.read(4))[0]
                self.m_event = END_TAG
                break

            if chunkType == CHUNK_XML_TEXT:
                self.m_name = unpack('<L', self.buff.read(4))[0]

                # FIXME
                self.buff.read(4)
                self.buff.read(4)

                self.m_event = TEXT
                break

    def getPrefixByUri(self, uri):
        try:
            return self.m_uriprefix[uri]
        except KeyError:
            return -1

    def getPrefix(self):
        try:
            return self.sb.getString(self.m_uriprefix[self.m_namespaceUri])
        except KeyError:
            return u''

    def getName(self):
        if self.m_name == -1 or (self.m_event != START_TAG and
                                 self.m_event != END_TAG):
            return u''

        return self.sb.getString(self.m_name)

    def getText(self):
        if self.m_name == -1 or self.m_event != TEXT:
            return u''

        return self.sb.getString(self.m_name)

    def getNamespacePrefix(self, pos):
        prefix = self.m_prefixuriL[pos][0]
        return self.sb.getString(prefix)

    def getNamespaceUri(self, pos):
        uri = self.m_prefixuriL[pos][1]
        return self.sb.getString(uri)

    def getXMLNS(self):
        buff = ""
        for i in self.m_uriprefix:
            if i not in self.visited_ns:
                buff += "xmlns:%s=\"%s\"\n" % (
                    self.sb.getString(self.m_uriprefix[i]),
                    self.sb.getString(self.m_prefixuri[self.m_uriprefix[i]]))
                self.visited_ns.append(i)
        return buff

    def getNamespaceCount(self, pos):
        pass

    def getAttributeOffset(self, index):
        # FIXME
        if self.m_event != START_TAG:
            warning("Current event is not START_TAG.")

        offset = index * 5
        # FIXME
        if offset >= len(self.m_attributes):
            warning("Invalid attribute index")

        return offset

    def getAttributeCount(self):
        if self.m_event != START_TAG:
            return -1

        return len(self.m_attributes) / ATTRIBUTE_LENGHT

    def getAttributePrefix(self, index):
        offset = self.getAttributeOffset(index)
        uri = self.m_attributes[offset + ATTRIBUTE_IX_NAMESPACE_URI]

        prefix = self.getPrefixByUri(uri)

        if prefix == -1:
            return ""

        return self.sb.getString(prefix)

    def getAttributeName(self, index):
        offset = self.getAttributeOffset(index)
        name = self.m_attributes[offset + ATTRIBUTE_IX_NAME]

        if name == -1:
            return ""

        res = self.sb.getString(name)
        if not res:
            attr = self.m_resourceIDs[name]
            if attr in SYSTEM_RESOURCES['attributes']['inverse']:
                res = 'android:' + SYSTEM_RESOURCES['attributes']['inverse'][
                    attr
                ]

        return res

    def getAttributeValueType(self, index):
        offset = self.getAttributeOffset(index)
        return self.m_attributes[offset + ATTRIBUTE_IX_VALUE_TYPE]

    def getAttributeValueData(self, index):
        offset = self.getAttributeOffset(index)
        return self.m_attributes[offset + ATTRIBUTE_IX_VALUE_DATA]

    def getAttributeValue(self, index):
        offset = self.getAttributeOffset(index)
        valueType = self.m_attributes[offset + ATTRIBUTE_IX_VALUE_TYPE]
        if valueType == TYPE_STRING:
            valueString = self.m_attributes[offset + ATTRIBUTE_IX_VALUE_STRING]
            return self.sb.getString(valueString)
        # WIP
        return ""

# resource constants

TYPE_ATTRIBUTE = 2
TYPE_DIMENSION = 5
TYPE_FIRST_COLOR_INT = 28
TYPE_FIRST_INT = 16
TYPE_FLOAT = 4
TYPE_FRACTION = 6
TYPE_INT_BOOLEAN = 18
TYPE_INT_DEC = 16
TYPE_INT_HEX = 17
TYPE_LAST_COLOR_INT = 31
TYPE_LAST_INT = 31
TYPE_NULL = 0
TYPE_REFERENCE = 1
TYPE_STRING = 3

TYPE_TABLE = {
    TYPE_ATTRIBUTE: "attribute",
    TYPE_DIMENSION: "dimension",
    TYPE_FLOAT: "float",
    TYPE_FRACTION: "fraction",
    TYPE_INT_BOOLEAN: "int_boolean",
    TYPE_INT_DEC: "int_dec",
    TYPE_INT_HEX: "int_hex",
    TYPE_NULL: "null",
    TYPE_REFERENCE: "reference",
    TYPE_STRING: "string",
}

RADIX_MULTS = [0.00390625, 3.051758E-005, 1.192093E-007, 4.656613E-010]
DIMENSION_UNITS = ["px", "dip", "sp", "pt", "in", "mm"]
FRACTION_UNITS = ["%", "%p"]

COMPLEX_UNIT_MASK = 15


def complexToFloat(xcomplex):
    return (float)(xcomplex & 0xFFFFFF00) * RADIX_MULTS[(xcomplex >> 4) & 3]


def getPackage(id):
    if id >> 24 == 1:
        return "android:"
    return ""


def format_value(_type, _data, lookup_string=lambda ix: "<string>"):
    if _type == TYPE_STRING:
        return lookup_string(_data)

    elif _type == TYPE_ATTRIBUTE:
        return "?%s%08X" % (getPackage(_data), _data)

    elif _type == TYPE_REFERENCE:
        return "@%s%08X" % (getPackage(_data), _data)

    elif _type == TYPE_FLOAT:
        return "%f" % unpack("=f", pack("=L", _data))[0]

    elif _type == TYPE_INT_HEX:
        return "0x%08X" % _data

    elif _type == TYPE_INT_BOOLEAN:
        if _data == 0:
            return "false"
        return "true"

    elif _type == TYPE_DIMENSION:
        return "%f%s" % (complexToFloat(_data), DIMENSION_UNITS[_data & COMPLEX_UNIT_MASK])

    elif _type == TYPE_FRACTION:
        return "%f%s" % (complexToFloat(_data) * 100, FRACTION_UNITS[_data & COMPLEX_UNIT_MASK])

    elif _type >= TYPE_FIRST_COLOR_INT and _type <= TYPE_LAST_COLOR_INT:
        return "#%08X" % _data

    elif _type >= TYPE_FIRST_INT and _type <= TYPE_LAST_INT:
        return "%d" % long2int(_data)

    return "<0x%X, type 0x%02X>" % (_data, _type)


class AXMLPrinter(object):

    def __init__(self, raw_buff):
        self.axml = AXMLParser(raw_buff)
        self.xmlns = False

        self.buff = u''

        while True and self.axml.is_valid():
            _type = self.axml.next()

            if _type == START_DOCUMENT:
                self.buff += u'<?xml version="1.0" encoding="utf-8"?>\n'
            elif _type == START_TAG:
                self.buff += u'<' + self.getPrefix(self.axml.getPrefix(
                )) + self.axml.getName() + u'\n'
                self.buff += self.axml.getXMLNS()

                for i in range(0, self.axml.getAttributeCount()):
                    self.buff += "%s%s=\"%s\"\n" % (
                        self.getPrefix(
                            self.axml.getAttributePrefix(i)),
                        self.axml.getAttributeName(i),
                        self._escape(self.getAttributeValue(i)))

                self.buff += u'>\n'

            elif _type == END_TAG:
                self.buff += "</%s%s>\n" % (
                    self.getPrefix(self.axml.getPrefix()), self.axml.getName())

            elif _type == TEXT:
                self.buff += "%s\n" % self.axml.getText()

            elif _type == END_DOCUMENT:
                break

    # pleed patch
    def _escape(self, s):
        s = s.replace("&", "&amp;")
        s = s.replace('"', "&quot;")
        s = s.replace("'", "&apos;")
        s = s.replace("<", "&lt;")
        s = s.replace(">", "&gt;")
        return escape(s)

    def get_buff(self):
        return self.buff.encode('utf-8')

    def get_xml(self):
        return minidom.parseString(self.get_buff()).toprettyxml(
            encoding="utf-8")

    def get_xml_obj(self):
        return minidom.parseString(self.get_buff())

    def getPrefix(self, prefix):
        if prefix is None or len(prefix) == 0:
            return u''

        return prefix + u':'

    def getAttributeValue(self, index):
        _type = self.axml.getAttributeValueType(index)
        _data = self.axml.getAttributeValueData(index)

        return format_value(_type, _data, lambda _: self.axml.getAttributeValue(index))


class SV(object):

    def __init__(self, size, buff):
        self.__size = size
        self.__value = unpack(self.__size, buff)[0]

    def _get(self):
        return pack(self.__size, self.__value)

    def __str__(self):
        return "0x%x" % self.__value

    def __int__(self):
        return self.__value

    def get_value_buff(self):
        return self._get()

    def get_value(self):
        return self.__value

    def set_value(self, attr):
        self.__value = attr


class SVs(object):

    def __init__(self, size, ntuple, buff):
        self.__size = size

        self.__value = ntuple._make(unpack(self.__size, buff))

    def _get(self):
        l = []
        for i in self.__value._fields:
            l.append(getattr(self.__value, i))
        return pack(self.__size, *l)

    def _export(self):
        return [x for x in self.__value._fields]

    def get_value_buff(self):
        return self._get()

    def get_value(self):
        return self.__value

    def set_value(self, attr):
        self.__value = self.__value._replace(**attr)

    def __str__(self):
        return self.__value.__str__()


class BuffHandle(object):

    def __init__(self, buff):
        self.__buff = buff
        self.__idx = 0

    def size(self):
        return len(self.__buff)

    def set_idx(self, idx):
        self.__idx = idx

    def get_idx(self):
        return self.__idx

    def readNullString(self, size):
        data = self.read(size)
        return data

    def read_b(self, size):
        return self.__buff[self.__idx:self.__idx + size]

    def read_at(self, offset, size):
        return self.__buff[offset:offset + size]

    def read(self, size):
        if isinstance(size, SV):
            size = size.value

        buff = self.__buff[self.__idx:self.__idx + size]
        self.__idx += size

        return buff

    def end(self):
        return self.__idx == len(self.__buff)


class Buff(object):

    def __init__(self, offset, buff):
        self.offset = offset
        self.buff = buff

        self.size = len(buff)


def long2int(l):
    if l > 0x7fffffff:
        l = (0x7fffffff & l) - 0x80000000
    return l
