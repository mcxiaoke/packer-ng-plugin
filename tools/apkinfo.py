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

# 0: chilkat
# 1: default python zipfile module
# 2: patch zipfile module
ZIPMODULE = 1

if sys.hexversion < 0x2070000:
    try:
        import chilkat
        ZIPMODULE = 0
        # UNLOCK : change it with your valid key !
        try:
            CHILKAT_KEY = read("key.txt")
        except Exception:
            CHILKAT_KEY = "testme"

    except ImportError:
        ZIPMODULE = 1
else:
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

################################################### CHILKAT ZIP FORMAT #####################################################
class ChilkatZip(object):

    def __init__(self, raw):
        self.files = []
        self.zip = chilkat.CkZip()

        self.zip.UnlockComponent(CHILKAT_KEY)

        self.zip.OpenFromMemory(raw, len(raw))

        filename = chilkat.CkString()
        e = self.zip.FirstEntry()
        while e is not None:
            e.get_FileName(filename)
            self.files.append(filename.getString())
            e = e.NextEntry()

    def delete(self, patterns):
        el = []

        filename = chilkat.CkString()
        e = self.zip.FirstEntry()
        while e is not None:
            e.get_FileName(filename)

            if re.match(patterns, filename.getString()) != None:
                el.append(e)
            e = e.NextEntry()

        for i in el:
            self.zip.DeleteEntry(i)

    def remplace_file(self, filename, buff):
        entry = self.zip.GetEntryByName(filename)
        if entry is not None:
            obj = chilkat.CkByteData()
            obj.append2(buff, len(buff))
            return entry.ReplaceData(obj)
        return False

    def write(self):
        obj = chilkat.CkByteData()
        self.zip.WriteToMemory(obj)
        return obj.getBytes()

    def namelist(self):
        return self.files

    def read(self, elem):
        e = self.zip.GetEntryByName(elem)
        s = chilkat.CkByteData()

        e.Inflate(s)
        return s.getBytes()

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

                    for item in self.xml[i].getElementsByTagName('uses-permission'):
                        self.permissions.append(str(item.getAttributeNS(
                            NS_ANDROID_URI, "name")))

                    # getting details of the declared permissions
                    for d_perm_item in self.xml[i].getElementsByTagName('permission'):
                        d_perm_name = self._get_res_string_value(str(
                            d_perm_item.getAttributeNS(NS_ANDROID_URI, "name")))
                        d_perm_label = self._get_res_string_value(str(
                            d_perm_item.getAttributeNS(NS_ANDROID_URI,
                                                       "label")))
                        d_perm_description = self._get_res_string_value(str(
                            d_perm_item.getAttributeNS(NS_ANDROID_URI,
                                                       "description")))
                        d_perm_permissionGroup = self._get_res_string_value(str(
                            d_perm_item.getAttributeNS(NS_ANDROID_URI,
                                                       "permissionGroup")))
                        d_perm_protectionLevel = self._get_res_string_value(str(
                            d_perm_item.getAttributeNS(NS_ANDROID_URI,
                                                       "protectionLevel")))

                        d_perm_details = {
                            "label": d_perm_label,
                            "description": d_perm_description,
                            "permissionGroup": d_perm_permissionGroup,
                            "protectionLevel": d_perm_protectionLevel,
                        }
                        self.declared_permissions[d_perm_name] = d_perm_details

                    self.valid_apk = True

        self.get_files_types()

    def _get_res_string_value(self, string):
        if not string.startswith('@string/'):
            return string
        string_key = string[9:]

        res_parser = self.get_android_resources()
        string_value = ''
        for package_name in res_parser.get_packages_names():
            extracted_values = res_parser.get_string(package_name, string_key)
            if extracted_values:
                string_value = extracted_values[1]
                break
        return string_value

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

    def get_app_name(self):
        """
            Return the appname of the APK

            :rtype: string
        """
        main_activity_name = self.get_main_activity()

        app_name = self.get_element('activity', 'label', name=main_activity_name)
        if not app_name:
            app_name = self.get_element('application', 'label')

        if app_name.startswith("@"):
            res_id = int(app_name[1:], 16)
            res_parser = self.get_android_resources()

            try:
                app_name = res_parser.get_resolved_res_configs(
                    res_id,
                    ARSCResTableConfig.default_config())[0][1]
            except Exception, e:
                warning("Exception selecting app icon: %s", e)
                app_name = ""
        return app_name

    def get_app_icon(self, max_dpi=65536):
        """
            Return the first non-greater density than max_dpi icon file name,
            unless exact icon resolution is set in the manifest, in which case
            return the exact file

            :rtype: string
        """
        main_activity_name = self.get_main_activity()

        app_icon = self.get_element('activity', 'icon', name=main_activity_name)

        if not app_icon:
            app_icon = self.get_element('application', 'icon')

        if not app_icon:
            res_id = self.get_res_id_by_key(self.package, 'mipmap', 'ic_launcher')
            if res_id:
                app_icon = "@%x" % res_id

        if not app_icon:
            res_id = self.get_res_id_by_key(self.package, 'drawable', 'ic_launcher')
            if res_id:
                app_icon = "@%x" % res_id

        if app_icon.startswith("@"):
            res_id = int(app_icon[1:], 16)
            res_parser = self.get_android_resources()
            candidates = res_parser.get_resolved_res_configs(res_id)

            app_icon = None
            current_dpi = 0

            try:
                for config, file_name in candidates:
                    dpi = config.get_density()
                    if dpi <= max_dpi and dpi > current_dpi:
                        app_icon = file_name
                        current_dpi = dpi
            except Exception, e:
                warning("Exception selecting app icon: %s", e)

        return app_icon

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

    def get_files(self):
        """
            Return the files inside the APK

            :rtype: a list of strings
        """
        return self.zip.namelist()

    def get_files_types(self):
        """
            Return the files inside the APK with their associated types (by using python-magic)

            :rtype: a dictionnary
        """
        try:
            import magic
        except ImportError:
            # no lib magic !
            for i in self.get_files():
                buffer = self.zip.read(i)
                self.files_crc32[i] = crc32(buffer)
                self.files[i] = "Unknown"
            return self.files

        if self.files != {}:
            return self.files

        builtin_magic = 0
        try:
            getattr(magic, "MagicException")
        except AttributeError:
            builtin_magic = 1

        if builtin_magic:
            ms = magic.open(magic.MAGIC_NONE)
            ms.load()

            for i in self.get_files():
                buffer = self.zip.read(i)
                self.files[i] = ms.buffer(buffer)
                if self.files[i] is None:
                    self.files[i] = "Unknown"
                else:
                    self.files[i] = self._patch_magic(buffer, self.files[i])
                self.files_crc32[i] = crc32(buffer)
        else:
            m = magic.Magic(magic_file=self.magic_file)
            for i in self.get_files():
                buffer = self.zip.read(i)
                self.files[i] = m.from_buffer(buffer)
                if self.files[i] is None:
                    self.files[i] = "Unknown"
                else:
                    self.files[i] = self._patch_magic(buffer, self.files[i])
                self.files_crc32[i] = crc32(buffer)

        return self.files

    def _patch_magic(self, buffer, orig):
        if ("Zip" in orig) or ("DBase" in orig):
            val = is_android_raw(buffer)
            if val == "APK":
                if is_valid_android_raw(buffer):
                    return "Android application package file"
            elif val == "AXML":
                return "Android's binary XML"

        return orig

    def get_files_crc32(self):
        if self.files_crc32 == {}:
            self.get_files_types()

        return self.files_crc32

    def get_files_information(self):
        """
            Return the files inside the APK with their associated types and crc32

            :rtype: string, string, int
        """
        if self.files == {}:
            self.get_files_types()

        for i in self.get_files():
            try:
                yield i, self.files[i], self.files_crc32[i]
            except KeyError:
                yield i, "", ""

    def get_raw(self):
        """
            Return raw bytes of the APK

            :rtype: string
        """
        return self.__raw

    def get_file(self, filename):
        """
            Return the raw data of the specified filename

            :rtype: string
        """
        try:
            return self.zip.read(filename)
        except KeyError:
            raise FileNotPresent(filename)

    def get_dex(self):
        """
            Return the raw data of the classes dex file

            :rtype: a string
        """
        try:
            return self.get_file("classes.dex")
        except FileNotPresent:
            return ""

    def get_all_dex(self):
        """
            Return the raw data of all classes dex files

            :rtype: a generator
        """
        try:
            yield self.get_file("classes.dex")

            # Multidex support
            basename = "classes%d.dex"
            for i in xrange(2, sys.maxint):
                yield self.get_file(basename % i)
        except FileNotPresent:
            pass

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

    def get_main_activity(self):
        """
            Return the name of the main activity

            :rtype: string
        """
        x = set()
        y = set()

        for i in self.xml:
            for item in self.xml[i].getElementsByTagName("activity"):
                for sitem in item.getElementsByTagName("action"):
                    val = sitem.getAttributeNS(NS_ANDROID_URI, "name")
                    if val == "android.intent.action.MAIN":
                        x.add(item.getAttributeNS(NS_ANDROID_URI, "name"))

                for sitem in item.getElementsByTagName("category"):
                    val = sitem.getAttributeNS(NS_ANDROID_URI, "name")
                    if val == "android.intent.category.LAUNCHER":
                        y.add(item.getAttributeNS(NS_ANDROID_URI, "name"))

        z = x.intersection(y)
        if len(z) > 0:
            return self.format_value(z.pop())
        return None

    def get_activities(self):
        """
            Return the android:name attribute of all activities

            :rtype: a list of string
        """
        return self.get_elements("activity", "name")

    def get_services(self):
        """
            Return the android:name attribute of all services

            :rtype: a list of string
        """
        return self.get_elements("service", "name")

    def get_receivers(self):
        """
            Return the android:name attribute of all receivers

            :rtype: a list of string
        """
        return self.get_elements("receiver", "name")

    def get_providers(self):
        """
            Return the android:name attribute of all providers

            :rtype: a list of string
        """
        return self.get_elements("provider", "name")

    def get_intent_filters(self, category, name):
        d = {}

        d["action"] = []
        d["category"] = []

        for i in self.xml:
            for item in self.xml[i].getElementsByTagName(category):
                if self.format_value(
                        item.getAttributeNS(NS_ANDROID_URI, "name")
                        ) == name:
                    for sitem in item.getElementsByTagName("intent-filter"):
                        for ssitem in sitem.getElementsByTagName("action"):
                            if ssitem.getAttributeNS(NS_ANDROID_URI, "name") \
                                    not in d["action"]:
                                d["action"].append(ssitem.getAttributeNS(
                                    NS_ANDROID_URI, "name"))
                        for ssitem in sitem.getElementsByTagName("category"):
                            if ssitem.getAttributeNS(NS_ANDROID_URI, "name") \
                                    not in d["category"]:
                                d["category"].append(ssitem.getAttributeNS(
                                    NS_ANDROID_URI, "name"))

        if not d["action"]:
            del d["action"]

        if not d["category"]:
            del d["category"]

        return d

    def get_permissions(self):
        """
            Return permissions

            :rtype: list of string
        """
        return self.permissions

    def get_details_permissions(self):
        """
            Return permissions with details

            :rtype: list of string
        """
        l = {}

        for i in self.permissions:
            perm = i
            pos = i.rfind(".")

            if pos != -1:
                perm = i[pos + 1:]

            try:
                l[i] = DVM_PERMISSIONS["MANIFEST_PERMISSION"][perm]
            except KeyError:
                l[i] = ["normal", "Unknown permission from android reference",
                        "Unknown permission from android reference"]

        return l

    def get_requested_permissions(self):
        """
            Returns all requested permissions.

            :rtype: list of strings
        """
        return self.permissions

    def get_declared_permissions(self):
        '''
            Returns list of the declared permissions.

            :rtype: list of strings
        '''
        return self.declared_permissions.keys()

    def get_declared_permissions_details(self):
        '''
            Returns declared permissions with the details.

            :rtype: dict
        '''
        return self.declared_permissions

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

    def get_libraries(self):
        """
            Return the android:name attributes for libraries

            :rtype: list
        """
        return self.get_elements("uses-library", "name")

    def get_certificate(self, filename):
        """
            Return a certificate object by giving the name in the apk file
        """
        import chilkat

        cert = chilkat.CkCert()
        f = self.get_file(filename)
        data = chilkat.CkByteData()
        data.append2(f, len(f))
        success = cert.LoadFromBinary(data)
        return success, cert

    def new_zip(self, filename, deleted_files=None, new_files={}):
        """
            Create a new zip file

            :param filename: the output filename of the zip
            :param deleted_files: a regex pattern to remove specific file
            :param new_files: a dictionnary of new files

            :type filename: string
            :type deleted_files: None or a string
            :type new_files: a dictionnary (key:filename, value:content of the file)
        """
        if self.zipmodule == 2:
            from androguard.patch import zipfile
            zout = zipfile.ZipFile(filename, 'w')
        else:
            import zipfile
            zout = zipfile.ZipFile(filename, 'w')

        for item in self.zip.infolist():
            if deleted_files is not None:
                if re.match(deleted_files, item.filename) == None:
                    if item.filename in new_files:
                        zout.writestr(item, new_files[item.filename])
                    else:
                        buffer = self.zip.read(item.filename)
                        zout.writestr(item, buffer)
        zout.close()

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

    def get_android_resources(self):
        """
            Return the :class:`ARSCParser` object which corresponds to the resources.arsc file

            :rtype: :class:`ARSCParser`
        """
        try:
            return self.arsc["resources.arsc"]
        except KeyError:
            self.arsc["resources.arsc"] = ARSCParser(self.zip.read(
                "resources.arsc"))
            return self.arsc["resources.arsc"]

    def get_signature_name(self):
        """
            Return the name of the first signature file found.
        """
        return self.get_signature_names()[0]

    def get_signature_names(self):
        """
             Return a list of the signature file names.
        """
        signature_expr = re.compile("^(META-INF/)(.*)(\.RSA|\.EC|\.DSA)$")
        signatures = []

        for i in self.get_files():
            if signature_expr.search(i):
                signatures.append(i)

        if len(signatures) > 0:
            return signatures

        return None

    def get_signature(self):
        """
            Return the data of the first signature file found.
        """
        return self.get_signatures()[0]

    def get_signatures(self):
        """
            Return a list of the data of the signature files.
        """
        signature_expr = re.compile("^(META-INF/)(.*)(\.RSA|\.EC|\.DSA)$")
        signature_datas = []

        for i in self.get_files():
            if signature_expr.search(i):
                signature_datas.append(self.get_file(i))

        if len(signature_datas) > 0:
            return signature_datas

        return None

    def show(self):
        self.get_files_types()

        print "FILES: "
        for i in self.get_files():
            try:
                print "\t", i, self.files[i], "%x" % self.files_crc32[i]
            except KeyError:
                print "\t", i, "%x" % self.files_crc32[i]

        print "DECLARED PERMISSIONS:"
        declared_permissions = self.get_declared_permissions()
        for i in declared_permissions:
            print "\t", i

        print "REQUESTED PERMISSIONS:"
        requested_permissions = self.get_requested_permissions()
        for i in requested_permissions:
            print "\t", i

        print "MAIN ACTIVITY: ", self.get_main_activity()

        print "ACTIVITIES: "
        activities = self.get_activities()
        for i in activities:
            filters = self.get_intent_filters("activity", i)
            print "\t", i, filters or ""

        print "SERVICES: "
        services = self.get_services()
        for i in services:
            filters = self.get_intent_filters("service", i)
            print "\t", i, filters or ""

        print "RECEIVERS: "
        receivers = self.get_receivers()
        for i in receivers:
            filters = self.get_intent_filters("receiver", i)
            print "\t", i, filters or ""

        print "PROVIDERS: ", self.get_providers()


def show_Certificate(cert):
    print "Issuer: C=%s, CN=%s, DN=%s, E=%s, L=%s, O=%s, OU=%s, S=%s" % (
        cert.issuerC(), cert.issuerCN(), cert.issuerDN(), cert.issuerE(),
        cert.issuerL(), cert.issuerO(), cert.issuerOU(), cert.issuerS())
    print "Subject: C=%s, CN=%s, DN=%s, E=%s, L=%s, O=%s, OU=%s, S=%s" % (
        cert.subjectC(), cert.subjectCN(), cert.subjectDN(), cert.subjectE(),
        cert.subjectL(), cert.subjectO(), cert.subjectOU(), cert.subjectS())

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

### resource constants

TYPE_ATTRIBUTE = 2
TYPE_DIMENSION = 5
TYPE_FIRST_COLOR_INT = 28
TYPE_FIRST_INT = 16
TYPE_FLOAT = 4
TYPE_FRACTION = 6
TYPE_INT_BOOLEAN = 18
TYPE_INT_COLOR_ARGB4 = 30
TYPE_INT_COLOR_ARGB8 = 28
TYPE_INT_COLOR_RGB4 = 31
TYPE_INT_COLOR_RGB8 = 29
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
    TYPE_INT_COLOR_ARGB4: "int_color_argb4",
    TYPE_INT_COLOR_ARGB8: "int_color_argb8",
    TYPE_INT_COLOR_RGB4: "int_color_rgb4",
    TYPE_INT_COLOR_RGB8: "int_color_rgb8",
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


RES_NULL_TYPE = 0x0000
RES_STRING_POOL_TYPE = 0x0001
RES_TABLE_TYPE = 0x0002
RES_XML_TYPE = 0x0003

# Chunk types in RES_XML_TYPE
RES_XML_FIRST_CHUNK_TYPE = 0x0100
RES_XML_START_NAMESPACE_TYPE = 0x0100
RES_XML_END_NAMESPACE_TYPE = 0x0101
RES_XML_START_ELEMENT_TYPE = 0x0102
RES_XML_END_ELEMENT_TYPE = 0x0103
RES_XML_CDATA_TYPE = 0x0104
RES_XML_LAST_CHUNK_TYPE = 0x017f

# This contains a uint32_t array mapping strings in the string
# pool back to resource identifiers.  It is optional.
RES_XML_RESOURCE_MAP_TYPE = 0x0180

# Chunk types in RES_TABLE_TYPE
RES_TABLE_PACKAGE_TYPE = 0x0200
RES_TABLE_TYPE_TYPE = 0x0201
RES_TABLE_TYPE_SPEC_TYPE = 0x0202

ACONFIGURATION_MCC = 0x0001
ACONFIGURATION_MNC = 0x0002
ACONFIGURATION_LOCALE = 0x0004
ACONFIGURATION_TOUCHSCREEN = 0x0008
ACONFIGURATION_KEYBOARD = 0x0010
ACONFIGURATION_KEYBOARD_HIDDEN = 0x0020
ACONFIGURATION_NAVIGATION = 0x0040
ACONFIGURATION_ORIENTATION = 0x0080
ACONFIGURATION_DENSITY = 0x0100
ACONFIGURATION_SCREEN_SIZE = 0x0200
ACONFIGURATION_VERSION = 0x0400
ACONFIGURATION_SCREEN_LAYOUT = 0x0800
ACONFIGURATION_UI_MODE = 0x1000


class ARSCParser(object):

    def __init__(self, raw_buff):
        self.analyzed = False
        self.buff = BuffHandle(raw_buff)

        self.header = ARSCHeader(self.buff)
        self.packageCount = unpack('<i', self.buff.read(4))[0]

        self.stringpool_main = StringBlock(self.buff)

        self.next_header = ARSCHeader(self.buff)
        self.packages = {}
        self.values = {}
        self.resource_values = collections.defaultdict(collections.defaultdict)
        self.resource_configs = collections.defaultdict(lambda: collections.defaultdict(set))
        self.resource_keys = collections.defaultdict(
            lambda: collections.defaultdict(collections.defaultdict))

        for i in range(0, self.packageCount):
            current_package = ARSCResTablePackage(self.buff)
            package_name = current_package.get_name()

            self.packages[package_name] = []

            mTableStrings = StringBlock(self.buff)
            mKeyStrings = StringBlock(self.buff)

            self.packages[package_name].append(current_package)
            self.packages[package_name].append(mTableStrings)
            self.packages[package_name].append(mKeyStrings)

            pc = PackageContext(current_package, self.stringpool_main,
                                mTableStrings, mKeyStrings)

            current = self.buff.get_idx()
            while not self.buff.end():
                header = ARSCHeader(self.buff)
                self.packages[package_name].append(header)

                if header.type == RES_TABLE_TYPE_SPEC_TYPE:
                    self.packages[package_name].append(ARSCResTypeSpec(
                        self.buff, pc))

                elif header.type == RES_TABLE_TYPE_TYPE:
                    a_res_type = ARSCResType(self.buff, pc)
                    self.packages[package_name].append(a_res_type)
                    self.resource_configs[package_name][a_res_type].add(
                       a_res_type.config)

                    entries = []
                    for i in range(0, a_res_type.entryCount):
                        current_package.mResId = current_package.mResId & 0xffff0000 | i
                        entries.append((unpack('<i', self.buff.read(4))[0],
                                        current_package.mResId))

                    self.packages[package_name].append(entries)

                    for entry, res_id in entries:
                        if self.buff.end():
                            break

                        if entry != -1:
                            ate = ARSCResTableEntry(self.buff, res_id, pc)
                            self.packages[package_name].append(ate)

                elif header.type == RES_TABLE_PACKAGE_TYPE:
                    break
                else:
                    warning("unknown type")
                    break

                current += header.size
                self.buff.set_idx(current)

    def _analyse(self):
        if self.analyzed:
            return

        self.analyzed = True

        for package_name in self.packages:
            self.values[package_name] = {}

            nb = 3
            while nb < len(self.packages[package_name]):
                header = self.packages[package_name][nb]
                if isinstance(header, ARSCHeader):
                    if header.type == RES_TABLE_TYPE_TYPE:
                        a_res_type = self.packages[package_name][nb + 1]

                        if a_res_type.config.get_language(
                        ) not in self.values[package_name]:
                            self.values[package_name][
                                a_res_type.config.get_language()
                            ] = {}
                            self.values[package_name][a_res_type.config.get_language(
                            )]["public"] = []

                        c_value = self.values[package_name][
                            a_res_type.config.get_language()
                        ]

                        entries = self.packages[package_name][nb + 2]
                        nb_i = 0
                        for entry, res_id in entries:
                            if entry != -1:
                                ate = self.packages[package_name][nb + 3 + nb_i]

                                self.resource_values[ate.mResId][a_res_type.config] = ate
                                self.resource_keys[package_name][a_res_type.get_type()][ate.get_value()] = ate.mResId

                                if ate.get_index() != -1:
                                    c_value["public"].append(
                                        (a_res_type.get_type(), ate.get_value(),
                                         ate.mResId))

                                if a_res_type.get_type() not in c_value:
                                    c_value[a_res_type.get_type()] = []

                                if a_res_type.get_type() == "string":
                                    c_value["string"].append(
                                        self.get_resource_string(ate))

                                elif a_res_type.get_type() == "id":
                                    if not ate.is_complex():
                                        c_value["id"].append(
                                            self.get_resource_id(ate))

                                elif a_res_type.get_type() == "bool":
                                    if not ate.is_complex():
                                        c_value["bool"].append(
                                            self.get_resource_bool(ate))

                                elif a_res_type.get_type() == "integer":
                                    c_value["integer"].append(
                                        self.get_resource_integer(ate))

                                elif a_res_type.get_type() == "color":
                                    c_value["color"].append(
                                        self.get_resource_color(ate))

                                elif a_res_type.get_type() == "dimen":
                                    c_value["dimen"].append(
                                        self.get_resource_dimen(ate))

                                nb_i += 1
                        nb += 3 + nb_i - 1  # -1 to account for the nb+=1 on the next line
                nb += 1

    def get_resource_string(self, ate):
        return [ate.get_value(), ate.get_key_data()]

    def get_resource_id(self, ate):
        x = [ate.get_value()]
        if ate.key.get_data() == 0:
            x.append("false")
        elif ate.key.get_data() == 1:
            x.append("true")
        return x

    def get_resource_bool(self, ate):
        x = [ate.get_value()]
        if ate.key.get_data() == 0:
            x.append("false")
        elif ate.key.get_data() == -1:
            x.append("true")
        return x

    def get_resource_integer(self, ate):
        return [ate.get_value(), ate.key.get_data()]

    def get_resource_color(self, ate):
        entry_data = ate.key.get_data()
        return [
            ate.get_value(),
            "#%02x%02x%02x%02x" % (
                ((entry_data >> 24) & 0xFF),
                ((entry_data >> 16) & 0xFF),
                ((entry_data >> 8) & 0xFF),
                (entry_data & 0xFF))
        ]

    def get_resource_dimen(self, ate):
        try:
            return [
                ate.get_value(), "%s%s" % (
                    complexToFloat(ate.key.get_data()),
                    DIMENSION_UNITS[ate.key.get_data() & COMPLEX_UNIT_MASK])
                ]
        except IndexError:
            debug("Out of range dimension unit index for %s: %s" % (
                complexToFloat(ate.key.get_data()),
                ate.key.get_data() & COMPLEX_UNIT_MASK))
            return [ate.get_value(), ate.key.get_data()]

    # FIXME
    def get_resource_style(self, ate):
        return ["", ""]

    def get_packages_names(self):
        return self.packages.keys()

    def get_locales(self, package_name):
        self._analyse()
        return self.values[package_name].keys()

    def get_types(self, package_name, locale):
        self._analyse()
        return self.values[package_name][locale].keys()

    def get_public_resources(self, package_name, locale='\x00\x00'):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'
        buff += '<resources>\n'

        try:
            for i in self.values[package_name][locale]["public"]:
                buff += '<public type="%s" name="%s" id="0x%08x" />\n' % (
                    i[0], i[1], i[2])
        except KeyError:
            pass

        buff += '</resources>\n'

        return buff.encode('utf-8')

    def get_string_resources(self, package_name, locale='\x00\x00'):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'
        buff += '<resources>\n'

        try:
            for i in self.values[package_name][locale]["string"]:
                buff += '<string name="%s">%s</string>\n' % (i[0], i[1])
        except KeyError:
            pass

        buff += '</resources>\n'

        return buff.encode('utf-8')

    def get_strings_resources(self):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'

        buff += "<packages>\n"
        for package_name in self.get_packages_names():
            buff += "<package name=\"%s\">\n" % package_name

            for locale in self.get_locales(package_name):
                buff += "<locale value=%s>\n" % repr(locale)

                buff += '<resources>\n'
                try:
                    for i in self.values[package_name][locale]["string"]:
                        buff += '<string name="%s">%s</string>\n' % (i[0], i[1])
                except KeyError:
                    pass

                buff += '</resources>\n'
                buff += '</locale>\n'

            buff += "</package>\n"

        buff += "</packages>\n"

        return buff.encode('utf-8')

    def get_id_resources(self, package_name, locale='\x00\x00'):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'
        buff += '<resources>\n'

        try:
            for i in self.values[package_name][locale]["id"]:
                if len(i) == 1:
                    buff += '<item type="id" name="%s"/>\n' % (i[0])
                else:
                    buff += '<item type="id" name="%s">%s</item>\n' % (i[0],
                                                                       i[1])
        except KeyError:
            pass

        buff += '</resources>\n'

        return buff.encode('utf-8')

    def get_bool_resources(self, package_name, locale='\x00\x00'):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'
        buff += '<resources>\n'

        try:
            for i in self.values[package_name][locale]["bool"]:
                buff += '<bool name="%s">%s</bool>\n' % (i[0], i[1])
        except KeyError:
            pass

        buff += '</resources>\n'

        return buff.encode('utf-8')

    def get_integer_resources(self, package_name, locale='\x00\x00'):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'
        buff += '<resources>\n'

        try:
            for i in self.values[package_name][locale]["integer"]:
                buff += '<integer name="%s">%s</integer>\n' % (i[0], i[1])
        except KeyError:
            pass

        buff += '</resources>\n'

        return buff.encode('utf-8')

    def get_color_resources(self, package_name, locale='\x00\x00'):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'
        buff += '<resources>\n'

        try:
            for i in self.values[package_name][locale]["color"]:
                buff += '<color name="%s">%s</color>\n' % (i[0], i[1])
        except KeyError:
            pass

        buff += '</resources>\n'

        return buff.encode('utf-8')

    def get_dimen_resources(self, package_name, locale='\x00\x00'):
        self._analyse()

        buff = '<?xml version="1.0" encoding="utf-8"?>\n'
        buff += '<resources>\n'

        try:
            for i in self.values[package_name][locale]["dimen"]:
                buff += '<dimen name="%s">%s</dimen>\n' % (i[0], i[1])
        except KeyError:
            pass

        buff += '</resources>\n'

        return buff.encode('utf-8')

    def get_id(self, package_name, rid, locale='\x00\x00'):
        self._analyse()

        try:
            for i in self.values[package_name][locale]["public"]:
                if i[2] == rid:
                    return i
        except KeyError:
            return None

    class ResourceResolver(object):
        def __init__(self, android_resources, config=None):
            self.resources = android_resources
            self.wanted_config = config

        def resolve(self, res_id):
            result = []
            self._resolve_into_result(result, res_id, self.wanted_config)
            return result

        def _resolve_into_result(self, result, res_id, config):
            configs = self.resources.get_res_configs(res_id, config)
            if configs:
                for config, ate in configs:
                    self.put_ate_value(result, ate, config)

        def put_ate_value(self, result, ate, config):
            if ate.is_complex():
                complex_array = []
                result.append(config, complex_array)
                for _, item in ate.item.items:
                    self.put_item_value(complex_array, item, config, complex_=True)
            else:
                self.put_item_value(result, ate.key, config, complex_=False)

        def put_item_value(self, result, item, config, complex_):
            if item.is_reference():
                res_id = item.get_data()
                if res_id:
                    self._resolve_into_result(
                        result,
                        item.get_data(),
                        self.wanted_config)
            else:
                if complex_:
                    result.append(item.format_value())
                else:
                    result.append((config, item.format_value()))

    def get_resolved_res_configs(self, rid, config=None):
        resolver = ARSCParser.ResourceResolver(self, config)
        return resolver.resolve(rid)

    def get_res_configs(self, rid, config=None):
        self._analyse()

        if not rid:
            raise ValueError("'rid' should be set")

        try:
            res_options = self.resource_values[rid]
            if len(res_options) > 1 and config:
                return [(
                    config,
                    res_options[config])]
            else:
                return res_options.items()

        except KeyError:
            return []

    def get_string(self, package_name, name, locale='\x00\x00'):
        self._analyse()

        try:
            for i in self.values[package_name][locale]["string"]:
                if i[0] == name:
                    return i
        except KeyError:
            return None

    def get_res_id_by_key(self, package_name, resource_type, key):
        try:
            return self.resource_keys[package_name][resource_type][key]
        except KeyError:
            return None

    def get_items(self, package_name):
        self._analyse()
        return self.packages[package_name]

    def get_type_configs(self, package_name, type_name=None):
        if package_name is None:
            package_name = self.get_packages_names()[0]
        result = collections.defaultdict(list)

        for res_type, configs in self.resource_configs[package_name].items():
            if res_type.get_package_name() == package_name and (
                    type_name is None or res_type.get_type() == type_name):
                result[res_type.get_type()].extend(configs)

        return result


class PackageContext(object):

    def __init__(self, current_package, stringpool_main, mTableStrings,
                 mKeyStrings):
        self.stringpool_main = stringpool_main
        self.mTableStrings = mTableStrings
        self.mKeyStrings = mKeyStrings
        self.current_package = current_package

    def get_mResId(self):
        return self.current_package.mResId

    def set_mResId(self, mResId):
        self.current_package.mResId = mResId

    def get_package_name(self):
        return self.current_package.get_name()


class ARSCHeader(object):

    def __init__(self, buff):
        self.start = buff.get_idx()
        self.type = unpack('<h', buff.read(2))[0]
        self.header_size = unpack('<h', buff.read(2))[0]
        self.size = unpack('<I', buff.read(4))[0]


class ARSCResTablePackage(object):

    def __init__(self, buff):
        self.start = buff.get_idx()
        self.id = unpack('<I', buff.read(4))[0]
        self.name = buff.readNullString(256)
        self.typeStrings = unpack('<I', buff.read(4))[0]
        self.lastPublicType = unpack('<I', buff.read(4))[0]
        self.keyStrings = unpack('<I', buff.read(4))[0]
        self.lastPublicKey = unpack('<I', buff.read(4))[0]
        self.mResId = self.id << 24

    def get_name(self):
        name = self.name.decode("utf-16", 'replace')
        name = name[:name.find("\x00")]
        return name


class ARSCResTypeSpec(object):

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent
        self.id = unpack('<b', buff.read(1))[0]
        self.res0 = unpack('<b', buff.read(1))[0]
        self.res1 = unpack('<h', buff.read(2))[0]
        self.entryCount = unpack('<I', buff.read(4))[0]

        self.typespec_entries = []
        for i in range(0, self.entryCount):
            self.typespec_entries.append(unpack('<I', buff.read(4))[0])


class ARSCResType(object):

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent
        self.id = unpack('<b', buff.read(1))[0]
        self.res0 = unpack('<b', buff.read(1))[0]
        self.res1 = unpack('<h', buff.read(2))[0]
        self.entryCount = unpack('<i', buff.read(4))[0]
        self.entriesStart = unpack('<i', buff.read(4))[0]
        self.mResId = (0xff000000 & self.parent.get_mResId()) | self.id << 16
        self.parent.set_mResId(self.mResId)

        self.config = ARSCResTableConfig(buff)

    def get_type(self):
        return self.parent.mTableStrings.getString(self.id - 1)

    def get_package_name(self):
        return self.parent.get_package_name()

    def __repr__(self):
        return "ARSCResType(%x, %x, %x, %x, %x, %x, %x, %s)" % (
            self.start,
            self.id,
            self.res0,
            self.res1,
            self.entryCount,
            self.entriesStart,
            self.mResId,
            "table:" + self.parent.mTableStrings.getString(self.id - 1)
        )


class ARSCResTableConfig(object):
    @classmethod
    def default_config(cls):
        if not hasattr(cls, 'DEFAULT'):
            cls.DEFAULT = ARSCResTableConfig(None)
        return cls.DEFAULT

    def __init__(self, buff=None, **kwargs):
        if buff is not None:
            self.start = buff.get_idx()
            self.size = unpack('<I', buff.read(4))[0]
            self.imsi = unpack('<I', buff.read(4))[0]
            self.locale = unpack('<I', buff.read(4))[0]
            self.screenType = unpack('<I', buff.read(4))[0]
            self.input = unpack('<I', buff.read(4))[0]
            self.screenSize = unpack('<I', buff.read(4))[0]
            self.version = unpack('<I', buff.read(4))[0]

            self.screenConfig = 0
            self.screenSizeDp = 0

            if self.size >= 32:
                self.screenConfig = unpack('<I', buff.read(4))[0]

                if self.size >= 36:
                    self.screenSizeDp = unpack('<I', buff.read(4))[0]

            self.exceedingSize = self.size - 36
            if self.exceedingSize > 0:
                info("Skipping padding bytes!")
                self.padding = buff.read(self.exceedingSize)
        else:
            self.start = 0
            self.size = 0
            self.imsi = \
                ((kwargs.pop('mcc', 0) & 0xffff) << 0) + \
                ((kwargs.pop('mnc', 0) & 0xffff) << 16)

            self.locale = 0
            for char_ix, char in kwargs.pop('locale', "")[0:4]:
                self.locale += (ord(char) << (char_ix * 8))

            self.screenType = \
                ((kwargs.pop('orientation', 0) & 0xff) << 0) + \
                ((kwargs.pop('touchscreen', 0) & 0xff) << 8) + \
                ((kwargs.pop('density', 0) & 0xffff) << 16)

            self.input = \
                ((kwargs.pop('keyboard', 0) & 0xff) << 0) + \
                ((kwargs.pop('navigation', 0) & 0xff) << 8) + \
                ((kwargs.pop('inputFlags', 0) & 0xff) << 16) + \
                ((kwargs.pop('inputPad0', 0) & 0xff) << 24)

            self.screenSize = \
                ((kwargs.pop('screenWidth', 0) & 0xffff) << 0) + \
                ((kwargs.pop('screenHeight', 0) & 0xffff) << 16)

            self.version = \
                ((kwargs.pop('sdkVersion', 0) & 0xffff) << 0) + \
                ((kwargs.pop('minorVersion', 0) & 0xffff) << 16)

            self.screenConfig = \
                ((kwargs.pop('screenLayout', 0) & 0xff) << 0) + \
                ((kwargs.pop('uiMode', 0) & 0xff) << 8) + \
                ((kwargs.pop('smallestScreenWidthDp', 0) & 0xffff) << 16)

            self.screenSizeDp = \
                ((kwargs.pop('screenWidthDp', 0) & 0xffff) << 0) + \
                ((kwargs.pop('screenHeightDp', 0) & 0xffff) << 16)

            self.exceedingSize = 0

    def get_language(self):
        x = self.locale & 0x0000ffff
        return chr(x & 0x00ff) + chr((x & 0xff00) >> 8)

    def get_country(self):
        x = (self.locale & 0xffff0000) >> 16
        return chr(x & 0x00ff) + chr((x & 0xff00) >> 8)

    def get_density(self):
        x = ((self.screenType >> 16) & 0xffff)
        return x

    def _get_tuple(self):
        return (
            self.imsi,
            self.locale,
            self.screenType,
            self.input,
            self.screenSize,
            self.version,
            self.screenConfig,
            self.screenSizeDp,
        )

    def __hash__(self):
        return hash(self._get_tuple())

    def __eq__(self, other):
        return self._get_tuple() == other._get_tuple()

    def __repr__(self):
        return repr(self._get_tuple())


class ARSCResTableEntry(object):

    def __init__(self, buff, mResId, parent=None):
        self.start = buff.get_idx()
        self.mResId = mResId
        self.parent = parent
        self.size = unpack('<H', buff.read(2))[0]
        self.flags = unpack('<H', buff.read(2))[0]
        self.index = unpack('<I', buff.read(4))[0]

        if self.flags & 1:
            self.item = ARSCComplex(buff, parent)
        else:
            self.key = ARSCResStringPoolRef(buff, self.parent)

    def get_index(self):
        return self.index

    def get_value(self):
        return self.parent.mKeyStrings.getString(self.index)

    def get_key_data(self):
        return self.key.get_data_value()

    def is_public(self):
        return self.flags == 0 or self.flags == 2

    def is_complex(self):
        return (self.flags & 1) == 1

    def __repr__(self):
        return "ARSCResTableEntry(%x, %x, %x, %x, %x, %r)" % (
            self.start,
            self.mResId,
            self.size,
            self.flags,
            self.index,
            self.item if self.is_complex() else self.key)


class ARSCComplex(object):

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.id_parent = unpack('<I', buff.read(4))[0]
        self.count = unpack('<I', buff.read(4))[0]

        self.items = []
        for i in range(0, self.count):
            self.items.append((unpack('<I', buff.read(4))[0],
                               ARSCResStringPoolRef(buff, self.parent)))

    def __repr__(self):
        return "ARSCComplex(%x, %d, %d)" % (self.start, self.id_parent, self.count)


class ARSCResStringPoolRef(object):

    def __init__(self, buff, parent=None):
        self.start = buff.get_idx()
        self.parent = parent

        self.skip_bytes = buff.read(3)
        self.data_type = unpack('<B', buff.read(1))[0]
        self.data = unpack('<I', buff.read(4))[0]

    def get_data_value(self):
        return self.parent.stringpool_main.getString(self.data)

    def get_data(self):
        return self.data

    def get_data_type(self):
        return self.data_type

    def get_data_type_string(self):
        return TYPE_TABLE[self.data_type]

    def format_value(self):
        return format_value(
            self.data_type,
            self.data,
            self.parent.stringpool_main.getString
        )

    def is_reference(self):
        return self.data_type == TYPE_REFERENCE

    def __repr__(self):
        return "ARSCResStringPoolRef(%x, %s, %x)" % (
            self.start,
            TYPE_TABLE.get(self.data_type, "0x%x" % self.data_type),
            self.data)


def get_arsc_info(arscobj):
    buff = ""
    for package in arscobj.get_packages_names():
        buff += package + ":\n"
        for locale in arscobj.get_locales(package):
            buff += "\t" + repr(locale) + ":\n"
            for ttype in arscobj.get_types(package, locale):
                buff += "\t\t" + ttype + ":\n"
                try:
                    tmp_buff = getattr(arscobj, "get_" + ttype + "_resources")(
                        package, locale).decode("utf-8", 'replace').split("\n")
                    for i in tmp_buff:
                        buff += "\t\t\t" + i + "\n"
                except AttributeError:
                    pass
    return buff


## classes

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

# frameworks/base/core/res/AndroidManifest.xml
# PERMISSIONS
DVM_PERMISSIONS = {
    "MANIFEST_PERMISSION": {

     # MESSAGES
    "SEND_SMS": ["dangerous", "send SMS messages", "Allows application to send SMS messages. Malicious applications may cost you money by sending messages without your confirmation."],
    "SEND_SMS_NO_CONFIRMATION": ["signatureOrSystem", "send SMS messages", "send SMS messages via the Messaging app with no user input or confirmation"],
    "RECEIVE_SMS": ["dangerous", "receive SMS", "Allows application to receive and process SMS messages. Malicious applications may monitor your messages or delete them without showing them to you."],
    "RECEIVE_MMS": ["dangerous", "receive MMS", "Allows application to receive and process MMS messages. Malicious applications may monitor your messages or delete them without showing them to you."],
    "RECEIVE_EMERGENCY_BROADCAST": [ "signatureOrSystem", "", "Allows an application to receive emergency cell broadcast messages, to record or display them to the user. Reserved for system apps." ],
    "READ_CELL_BROADCASTS"          : [ "dangerous", "received cell broadcast messages", "Allows an application to read previously received cell broadcast "\
                                                 "messages and to register a content observer to get notifications when "\
                                                 "a cell broadcast has been received and added to the database. For "\
                                                 "emergency alerts, the database is updated immediately after the "\
                                                 "alert dialog and notification sound/vibration/speech are presented."\
                                                 "The \"read\" column is then updated after the user dismisses the alert."\
                                                 "This enables supplementary emergency assistance apps to start loading "\
                                                 "additional emergency information (if Internet access is available) "\
                                                 "when the alert is first received, and to delay presenting the info "\
                                                 "to the user until after the initial alert dialog is dismissed." ],
        "READ_SMS" : [ "dangerous" , "read SMS or MMS" , "Allows application to read SMS messages stored on your phone or SIM card. Malicious applications may read your confidential messages." ],
        "WRITE_SMS" : [ "dangerous" , "edit SMS or MMS" , "Allows application to write to SMS messages stored on your phone or SIM card. Malicious applications may delete your messages." ],
        "RECEIVE_WAP_PUSH" : [ "dangerous" , "receive WAP" , "Allows application to receive and process WAP messages. Malicious applications may monitor your messages or delete them without showing them to you." ],
        "BROADCAST_SMS" : [ "signature" , "send SMS-received broadcast" , "Allows an application to broadcast a notification that an SMS message has been received. Malicious applications may use this to forge incoming SMS messages." ],
        "BROADCAST_WAP_PUSH" : [ "signature" , "send WAP-PUSH-received broadcast" , "Allows an application to broadcast a notification that a WAP-PUSH message has been received. Malicious applications may use this to forge MMS message receipt or to replace the content of any web page silently with malicious variants." ],

   # SOCIAL_INFO
        "READ_CONTACTS" : [ "dangerous" , "read contact data" , "Allows an application to read all of the contact (address) data stored on your phone. Malicious applications can use this to send your data to other people." ],
        "WRITE_CONTACTS" : [ "dangerous" , "write contact data" , "Allows an application to modify the contact (address) data stored on your phone. Malicious applications can use this to erase or modify your contact data." ],
    "BIND_DIRECTORY_SEARCH" : [ "signatureOrSystem", "execute contacts directory search", "Allows an application to execute contacts directory search. This should only be used by ContactsProvider." ],
    "READ_CALL_LOG": [ "dangerous", "read the user's call log.", "Allows an application to read the user's call log." ],
    "WRITE_CALL_LOG": [ "dangerous", "write (but not read) the user's contacts data.", "Allows an application to write (but not read) the user's contacts data." ],
    "READ_SOCIAL_STREAM" : [ "dangerous", "read from the user's social stream", "Allows an application to read from the user's social stream." ],
    "WRITE_SOCIAL_STREAM" : [ "dangerous", "write the user's social stream", "Allows an application to write (but not read) the user's social stream data." ],

     # PERSONAL_INFO
    "READ_PROFILE" : [ "dangerous", "read the user's personal profile data", "Allows an application to read the user's personal profile data."],
    "WRITE_PROFILE" : [ "dangerous", "write the user's personal profile data", "Allows an application to write (but not read) the user's personal profile data."],
    "RETRIEVE_WINDOW_CONTENT": [ "signatureOrSystem", "", "Allows an application to retrieve the content of the active window An active window is the window that has fired an accessibility event. " ],
        "BIND_APPWIDGET" : [ "signatureOrSystem" , "choose widgets" , "Allows the application to tell the system which widgets can be used by which application. With this permission, applications can give access to personal data to other applications. Not for use by normal applications." ],
    "BIND_KEYGUARD_APPWIDGET"       : [ "signatureOrSystem", "", "Private permission, to restrict who can bring up a dialog to add a new keyguard widget" ],

     # CALENDAR
    "READ_CALENDAR" : [ "dangerous" , "read calendar events" , "Allows an application to read all of the calendar events stored on your phone. Malicious applications can use this to send your calendar events to other people." ],
        "WRITE_CALENDAR": [ "dangerous" , "add or modify calendar events and send emails to guests" , "Allows an application to add or change the events on your calendar, which may send emails to guests. Malicious applications can use this to erase or modify your calendar events or to send emails to guests." ],


      # USER_DICTIONARY
   "READ_USER_DICTIONARY" : [ "dangerous" , "read user-defined dictionary" , "Allows an application to read any private words, names and phrases that the user may have stored in the user dictionary." ],

    # WRITE_USER_DICTIONARY
        "WRITE_USER_DICTIONARY" : [ "normal" , "write to user-defined dictionary" , "Allows an application to write new words into the user dictionary." ],

   # BOOKMARKS
        "READ_HISTORY_BOOKMARKS" : [ "dangerous" , "read Browser\'s history and bookmarks" , "Allows the application to read all the URLs that the browser has visited and all of the browser\'s bookmarks." ],
        "WRITE_HISTORY_BOOKMARKS" : [ "dangerous" , "write Browser\'s history and bookmarks" , "Allows an application to modify the browser\'s history or bookmarks stored on your phone. Malicious applications can use this to erase or modify your browser\'s data." ],

   # DEVICE_ALARMS
        "SET_ALARM" : [ "normal" , "set alarm in alarm clock" , "Allows the application to set an alarm in an installed alarm clock application. Some alarm clock applications may not implement this feature." ],

   # VOICEMAIL
    "ADD_VOICEMAIL" : [ "dangerous", "add voicemails into the system", "Allows an application to add voicemails into the system." ],

     # LOCATION
        "ACCESS_FINE_LOCATION" : [ "dangerous" , "fine (GPS) location" , "Access fine location sources, such as the Global Positioning System on the phone, where available. Malicious applications can use this to determine where you are and may consume additional battery power." ],
        "ACCESS_COARSE_LOCATION" : [ "dangerous" , "coarse (network-based) location" , "Access coarse location sources, such as the mobile network database, to determine an approximate phone location, where available. Malicious applications can use this to determine approximately where you are." ],
        "ACCESS_MOCK_LOCATION" : [ "dangerous" , "mock location sources for testing" , "Create mock location sources for testing. Malicious applications can use this to override the location and/or status returned by real-location sources such as GPS or Network providers." ],
        "ACCESS_LOCATION_EXTRA_COMMANDS" : [ "normal" , "access extra location provider commands" , "Access extra location provider commands. Malicious applications could use this to interfere with the operation of the GPS or other location sources." ],
   "INSTALL_LOCATION_PROVIDER" : [ "signatureOrSystem" , "permission to install a location provider" , "Create mock location sources for testing. Malicious applications can use this to override the location and/or status returned by real-location sources such as GPS or Network providers, or monitor and report your location to an external source." ],


     # NETWORK
        "INTERNET" : [ "dangerous" , "full Internet access" , "Allows an application to create network sockets." ],
        "ACCESS_NETWORK_STATE" : [ "normal" , "view network status" , "Allows an application to view the status of all networks." ],
        "ACCESS_WIFI_STATE" : [ "normal" , "view Wi-Fi status" , "Allows an application to view the information about the status of Wi-Fi." ],
        "CHANGE_WIFI_STATE" : [ "dangerous" , "change Wi-Fi status" , "Allows an application to connect to and disconnect from Wi-Fi access points and to make changes to configured Wi-Fi networks." ],
        "CHANGE_NETWORK_STATE" : [ "normal" , "change network connectivity" , "Allows an application to change the state of network connectivity." ],
    "ACCESS_WIMAX_STATE": [ "normal", "", "" ],
    "CHANGE_WIMAX_STATE": [ "dangerous", "", "" ],
        "NFC" : [ "dangerous" , "control Near-Field Communication" , "Allows an application to communicate with Near-Field Communication (NFC) tags, cards and readers." ],
    "CONNECTIVITY_INTERNAL": [ "signatureOrSystem", "use privileged ConnectivityManager API", "Allows an internal user to use privileged ConnectivityManager API" ],
    "RECEIVE_DATA_ACTIVITY_CHANGE": [ "signatureOrSystem", "", "" ],


    # BLUETOOTH_NETWORK
        "BLUETOOTH" : [ "dangerous" , "create Bluetooth connections" , "Allows an application to view configuration of the local Bluetooth phone and to make and accept connections with paired devices." ],
        "BLUETOOTH_ADMIN" : [ "dangerous" , "bluetooth administration" , "Allows an application to configure the local Bluetooth phone and to discover and pair with remote devices." ],


    # SYSTEM TOOLS
    "BLUETOOTH_STACK": [ "signature", "", "" ],
    "NET_ADMIN": [ "signature", "configure network interfaces, configure/use IPSec, etc", "Allows access to configure network interfaces, configure/use IPSec, etc." ],
    "REMOTE_AUDIO_PLAYBACK": [ "signature", "remote audio playback", "Allows registration for remote audio playback" ],
    "READ_EXTERNAL_STORAGE" : [ "normal", "read from external storage", "Allows an application to read from external storage" ],
    "INTERACT_ACROSS_USERS": [ "signatureOrSystemOrDevelopment", "", "Allows an application to call APIs that allow it to do interactions across the users on the device, using singleton services and user-targeted broadcasts.  This permission is not available to third party applications." ],
    "INTERACT_ACROSS_USERS_FULL": [ "signature", "", "Fuller form of INTERACT_ACROSS_USERS that removes restrictions on where broadcasts can be sent and allows other types of interactions." ],
    "MANAGE_USERS": [ "signatureOrSystem", "", "Allows an application to call APIs that allow it to query and manage users on the device. This permission is not available to third party applications." ],
    "GET_DETAILED_TASKS": [ "signature", "", "Allows an application to get full detailed information about recently running tasks, with full fidelity to the real state." ],
    "START_ANY_ACTIVITY": [ "signature", "", "Allows an application to start any activity, regardless of permission protection or exported state." ],
    "SET_SCREEN_COMPATIBILITY": [ "signature", "", "Change the screen compatibility mode of applications" ],
        "CHANGE_CONFIGURATION" : [ "signatureOrSystemOrDevelopment" , "change your UI settings" , "Allows an application to change the current configuration, such as the locale or overall font size." ],
        "FORCE_STOP_PACKAGES" : [ "signature" , "force-stop other applications" , "Allows an application to stop other applications forcibly." ],
        "SET_ANIMATION_SCALE" : [ "signatureOrSystemOrDevelopment" , "modify global animation speed" , "Allows an application to change the global animation speed (faster or slower animations) at any time." ],
        "GET_PACKAGE_SIZE" : [ "normal" , "measure application storage space" , "Allows an application to retrieve its code, data and cache sizes" ],
        "SET_PREFERRED_APPLICATIONS" : [ "signature" , "set preferred applications" , "Allows an application to modify your preferred applications. This can allow malicious applications to silently change the applications that are run, spoofing your existing applications to collect private data from you." ],
        "BROADCAST_STICKY" : [ "normal" , "send sticky broadcast" , "Allows an application to send sticky broadcasts, which remain after the broadcast ends. Malicious applications can make the phone slow or unstable by causing it to use too much memory." ],
   "MOUNT_UNMOUNT_FILESYSTEMS" : [ "signatureOrSystem" , "mount and unmount file systems" , "Allows the application to mount and unmount file systems for removable storage." ],
        "MOUNT_FORMAT_FILESYSTEMS" : [ "signatureOrSystem" , "format external storage" , "Allows the application to format removable storage." ],
        "ASEC_ACCESS" : [ "signature" , "get information on internal storage" , "Allows the application to get information on internal storage." ],
   "ASEC_CREATE" : [ "signature" , "create internal storage" , "Allows the application to create internal storage." ],
        "ASEC_DESTROY" : [ "signature" , "destroy internal storage" , "Allows the application to destroy internal storage." ],
        "ASEC_MOUNT_UNMOUNT" : [ "signature" , "mount/unmount internal storage" , "Allows the application to mount/unmount internal storage." ],
        "ASEC_RENAME" : [ "signature" , "rename internal storage" , "Allows the application to rename internal storage." ],
    "WRITE_APN_SETTINGS" : [ "signatureOrSystem" , "write Access Point Name settings" , "Allows an application to modify the APN settings, such as Proxy and Port of any APN." ],
        "SUBSCRIBED_FEEDS_READ" : [ "normal" , "read subscribed feeds" , "Allows an application to receive details about the currently synced feeds." ],
        "SUBSCRIBED_FEEDS_WRITE" : [ "dangerous" , "write subscribed feeds" , "Allows an application to modify your currently synced feeds. This could allow a malicious application to change your synced feeds." ],
        "CLEAR_APP_CACHE" : [ "dangerous" , "delete all application cache data" , "Allows an application to free phone storage by deleting files in application cache directory. Access is usually very restricted to system process." ],
        "DIAGNOSTIC" : [ "signature" , "read/write to resources owned by diag" , "Allows an application to read and write to any resource owned by the diag group; for example, files in /dev. This could potentially affect system stability and security. This should ONLY be used for hardware-specific diagnostics by the manufacturer or operator." ],
        "BROADCAST_PACKAGE_REMOVED" : [ "signature" , "send package removed broadcast" , "Allows an application to broadcast a notification that an application package has been removed. Malicious applications may use this to kill any other application running." ],
        "BATTERY_STATS" : [ "dangerous" , "modify battery statistics" , "Allows the modification of collected battery statistics. Not for use by normal applications." ],
    "MODIFY_APPWIDGET_BIND_PERMISSIONS" : [ "signatureOrSystem", "query/set which applications can bind AppWidgets.", "Internal permission allowing an application to query/set which applications can bind AppWidgets." ],
        "CHANGE_BACKGROUND_DATA_SETTING" : [ "signature" , "change background data usage setting" , "Allows an application to change the background data usage setting." ],
        "GLOBAL_SEARCH" : [ "signatureOrSystem" , "" , "This permission can be used on content providers to allow the global search " \
                          "system to access their data.  Typically it used when the provider has some "  \
                          "permissions protecting it (which global search would not be expected to hold)," \
                          "and added as a read-only permission to the path in the provider where global "\
                          "search queries are performed.  This permission can not be held by regular applications; "\
                               "it is used by applications to protect themselves from everyone else besides global search" ],
        "GLOBAL_SEARCH_CONTROL" : [ "signature" , "" , "Internal permission protecting access to the global search "              \
                             "system: ensures that only the system can access the provider "          \
                             "to perform queries (since this otherwise provides unrestricted "    \
                             "access to a variety of content providers), and to write the "             \
                             "search statistics (to keep applications from gaming the source "      \
                             "ranking)." ],
        "SET_WALLPAPER_COMPONENT" : [ "signatureOrSystem" , "set a live wallpaper" , "Allows applications to set a live wallpaper." ],
    "READ_DREAM_STATE"              : [ "signature", "", "Allows applications to read dream settings and dream state." ],
    "WRITE_DREAM_STATE"             : [ "signature", "", "Allows applications to write dream settings, and start or stop dreaming." ],
        "WRITE_SETTINGS" : [ "normal" , "modify global system settings" , "Allows an application to modify the system\'s settings data. Malicious applications can corrupt your system\'s configuration." ],

     # ACCOUNTS
        "GET_ACCOUNTS" : [ "normal" , "discover known accounts" , "Allows an application to access the list of accounts known by the phone." ],
        "AUTHENTICATE_ACCOUNTS" : [ "dangerous" , "act as an account authenticator" , "Allows an application to use the account authenticator capabilities of the Account Manager, including creating accounts as well as obtaining and setting their passwords." ],
        "USE_CREDENTIALS" : [ "dangerous" , "use the authentication credentials of an account" , "Allows an application to request authentication tokens." ],
        "MANAGE_ACCOUNTS" : [ "dangerous" , "manage the accounts list" , "Allows an application to perform operations like adding and removing accounts and deleting their password." ],
        "ACCOUNT_MANAGER" : [ "signature" , "act as the Account Manager Service" , "Allows an application to make calls to Account Authenticators" ],

   # AFFECTS_BATTERY
        "CHANGE_WIFI_MULTICAST_STATE" : [ "dangerous" , "allow Wi-Fi Multicast reception" , "Allows an application to receive packets not directly addressed to your device. This can be useful when discovering services offered nearby. It uses more power than the non-multicast mode." ],
        "VIBRATE" : [ "normal" , "control vibrator" , "Allows the application to control the vibrator." ],
        "FLASHLIGHT" : [ "normal" , "control flashlight" , "Allows the application to control the flashlight." ],
        "WAKE_LOCK" : [ "normal" , "prevent phone from sleeping" , "Allows an application to prevent the phone from going to sleep." ],

   # AUDIO_SETTINGS
        "MODIFY_AUDIO_SETTINGS" : [ "normal" , "change your audio settings" , "Allows application to modify global audio settings, such as volume and routing." ],

   # HARDWARE_CONTROLS
    "MANAGE_USB": [ "signatureOrSystem", "manage preferences and permissions for USB devices", "Allows an application to manage preferences and permissions for USB devices" ],
    "ACCESS_MTP": [ "signatureOrSystem", "access the MTP USB kernel driver", "Allows an application to access the MTP USB kernel driver. For use only by the device side MTP implementation." ],
        "HARDWARE_TEST" : [ "signature" , "test hardware" , "Allows the application to control various peripherals for the purpose of hardware testing." ],

   # MICROPHONE
        "RECORD_AUDIO" : [ "dangerous" , "record audio" , "Allows application to access the audio record path." ],

   # CAMERA
        "CAMERA" : [ "dangerous" , "take pictures and videos" , "Allows application to take pictures and videos with the camera. This allows the application to collect images that the camera is seeing at any time." ],

   # PHONE_CALLS
        "PROCESS_OUTGOING_CALLS" : [ "dangerous" , "intercept outgoing calls" , "Allows application to process outgoing calls and change the number to be dialled. Malicious applications may monitor, redirect or prevent outgoing calls." ],
        "MODIFY_PHONE_STATE" : [ "signatureOrSystem" , "modify phone status" , "Allows modification of the telephony state - power on, mmi, etc. Does not include placing calls." ],
        "READ_PHONE_STATE" : [ "dangerous" , "read phone state and identity" , "Allows the application to access the phone features of the device. An application with this permission can determine the phone number and serial number of this phone, whether a call is active, the number that call is connected to and so on." ],
    "READ_PRIVILEGED_PHONE_STATE": [ "signatureOrSystem", "read access to privileged phone state", "Allows read access to privileged phone state." ],
    "CALL_PHONE" : [ "dangerous" , "directly call phone numbers" , "Allows an application to initiate a phone call without going through the Dialer user interface for the user to confirm the call being placed. " ],
        "USE_SIP" : [ "dangerous" , "make/receive Internet calls" , "Allows an application to use the SIP service to make/receive Internet calls." ],

   # STORAGE
        "WRITE_EXTERNAL_STORAGE" : [ "dangerous" , "modify/delete SD card contents" , "Allows an application to write to the SD card." ],
    "WRITE_MEDIA_STORAGE": [ "signatureOrSystem", "write to internal media storage", "Allows an application to write to internal media storage" ],

     # SCREENLOCK
        "DISABLE_KEYGUARD" : [ "dangerous" , "disable key lock" , "Allows an application to disable the key lock and any associated password security. A legitimate example of this is the phone disabling the key lock when receiving an incoming phone call, then re-enabling the key lock when the call is finished." ],

   # APP_INFO
        "GET_TASKS" : [ "dangerous" , "retrieve running applications" , "Allows application to retrieve information about currently and recently running tasks. May allow malicious applications to discover private information about other applications." ],
        "REORDER_TASKS" : [ "normal" , "reorder applications running" , "Allows an application to move tasks to the foreground and background. Malicious applications can force themselves to the front without your control." ],
    "REMOVE_TASKS": [ "signature", "", "Allows an application to change to remove/kill tasks" ],
        "RESTART_PACKAGES" : [ "normal" , "kill background processes" , "Allows an application to kill background processes of other applications, even if memory is not low." ],
        "KILL_BACKGROUND_PROCESSES" : [ "normal" , "kill background processes" , "Allows an application to kill background processes of other applications, even if memory is not low." ],
        "PERSISTENT_ACTIVITY" : [ "normal" , "make application always run" , "Allows an application to make parts of itself persistent, so that the system can\'t use it for other applications." ],
        "RECEIVE_BOOT_COMPLETED" : [ "normal" , "automatically start at boot" , "Allows an application to start itself as soon as the system has finished booting. This can make it take longer to start the phone and allow the application to slow down the overall phone by always running." ],

   # DISPLAY
        "SYSTEM_ALERT_WINDOW" : [ "dangerous" , "display system-level alerts" , "Allows an application to show system-alert windows. Malicious applications can take over the entire screen of the phone." ],

   # WALLPAPER
   "SET_WALLPAPER" : [ "normal" , "set wallpaper" , "Allows the application to set the system wallpaper." ],
        "SET_WALLPAPER_HINTS" : [ "normal" , "set wallpaper size hints" , "Allows the application to set the system wallpaper size hints." ],

   # SYSTEM_CLOCK
        "SET_TIME_ZONE" : [ "normal" , "set time zone" , "Allows an application to change the phone\'s time zone." ],

   # STATUS_BAR
        "EXPAND_STATUS_BAR" : [ "normal" , "expand/collapse status bar" , "Allows application to expand or collapse the status bar." ],

   # SYNC_SETTINGS
        "READ_SYNC_SETTINGS" : [ "normal" , "read sync settings" , "Allows an application to read the sync settings, such as whether sync is enabled for Contacts." ],
        "WRITE_SYNC_SETTINGS" : [ "normal" , "write sync settings" , "Allows an application to modify the sync settings, such as whether sync is enabled for Contacts." ],
        "READ_SYNC_STATS" : [ "normal" , "read sync statistics" , "Allows an application to read the sync stats; e.g. the history of syncs that have occurred." ],

     # DEVELOPMENT_TOOLS
        "WRITE_SECURE_SETTINGS" : [ "signatureOrSystemOrDevelopment" , "modify secure system settings" , "Allows an application to modify the system\'s secure settings data. Not for use by normal applications." ],
        "DUMP" : [ "signatureOrSystemOrDevelopment" , "retrieve system internal status" , "Allows application to retrieve internal status of the system. Malicious applications may retrieve a wide variety of private and secure information that they should never normally need." ],
        "READ_LOGS" : [ "signatureOrSystemOrDevelopment" , "read sensitive log data" , "Allows an application to read from the system\'s various log files. This allows it to discover general information about what you are doing with the phone, potentially including personal or private information." ],
        "SET_DEBUG_APP" : [ "signatureOrSystemOrDevelopment" , "enable application debugging" , "Allows an application to turn on debugging for another application. Malicious applications can use this to kill other applications." ],
        "SET_PROCESS_LIMIT" : [ "signatureOrSystemOrDevelopment" , "limit number of running processes" , "Allows an application to control the maximum number of processes that will run. Never needed for normal applications." ],
        "SET_ALWAYS_FINISH" : [ "signatureOrSystemOrDevelopment" , "make all background applications close" , "Allows an application to control whether activities are always finished as soon as they go to the background. Never needed for normal applications." ],
        "SIGNAL_PERSISTENT_PROCESSES" : [ "signatureOrSystemOrDevelopment" , "send Linux signals to applications" , "Allows application to request that the supplied signal be sent to all persistent processes." ],
    "ACCESS_ALL_EXTERNAL_STORAGE"   : [ "signature", "", "Allows an application to access all multi-user external storage" ],

   # No groups ...
        "SET_TIME": [ "signatureOrSystem" , "set time" , "Allows an application to change the phone\'s clock time." ],
    "ALLOW_ANY_CODEC_FOR_PLAYBACK": [ "signatureOrSystem", "", "Allows an application to use any media decoder when decoding for playback." ],
        "STATUS_BAR" : [ "signatureOrSystem" , "disable or modify status bar" , "Allows application to disable the status bar or add and remove system icons." ],
        "STATUS_BAR_SERVICE" : [ "signature" , "status bar" , "Allows the application to be the status bar." ],
        "FORCE_BACK" : [ "signature" , "force application to close" , "Allows an application to force any activity that is in the foreground to close and go back. Should never be needed for normal applications." ],
        "UPDATE_DEVICE_STATS" : [ "signatureOrSystem" , "modify battery statistics" , "Allows the modification of collected battery statistics. Not for use by normal applications." ],
        "INTERNAL_SYSTEM_WINDOW" : [ "signature" , "display unauthorised windows" , "Allows the creation of windows that are intended to be used by the internal system user interface. Not for use by normal applications." ],
        "MANAGE_APP_TOKENS" : [ "signature" , "manage application tokens" , "Allows applications to create and manage their own tokens, bypassing their normal Z-ordering. Should never be needed for normal applications." ],
    "FREEZE_SCREEN": [ "signature", "", "Allows the application to temporarily freeze the screen for a full-screen transition." ],
        "INJECT_EVENTS" : [ "signature" , "inject user events" , "Allows an application to inject user events (keys, touch, trackball) into the event stream and deliver them to ANY window.  Without this permission, you can only deliver events to windows in your own process. Very few applications should need to use this permission" ],
    "FILTER_EVENTS": [ "signature", "", "Allows an application to register an input filter which filters the stream of user events (keys, touch, trackball) before they are dispatched to any window" ],
    "RETRIEVE_WINDOW_INFO"          : [ "signature", "", "Allows an application to retrieve info for a window from the window manager." ],
    "TEMPORARY_ENABLE_ACCESSIBILITY": [ "signature", "", "Allows an application to temporary enable accessibility on the device." ],
    "MAGNIFY_DISPLAY": [ "signature", "", "Allows an application to magnify the content of a display." ],
        "SET_ACTIVITY_WATCHER" : [ "signature" , "monitor and control all application launching" , "Allows an application to monitor and control how the system launches activities. Malicious applications may compromise the system completely. This permission is needed only for development, never for normal phone usage." ],
        "SHUTDOWN" : [ "signatureOrSystem" , "partial shutdown" , "Puts the activity manager into a shut-down state. Does not perform a complete shut down." ],
        "STOP_APP_SWITCHES" : [ "signatureOrSystem" , "prevent app switches" , "Prevents the user from switching to another application." ],
        "READ_INPUT_STATE" : [ "signature" , "record what you type and actions that you take" , "Allows applications to watch the keys that you press even when interacting with another application (such as entering a password). Should never be needed for normal applications." ],
        "BIND_INPUT_METHOD" : [ "signature" , "bind to an input method" , "Allows the holder to bind to the top-level interface of an input method. Should never be needed for normal applications." ],
    "BIND_ACCESSIBILITY_SERVICE"    : [ "signature", "", "Must be required by an android.accessibilityservice.AccessibilityService to ensure that only the system can bind to it. " ],
    "BIND_TEXT_SERVICE"             : [ "signature", "", "Must be required by a TextService (e.g. SpellCheckerService) to ensure that only the system can bind to it." ],
    "BIND_VPN_SERVICE"              : [ "signature", "", "Must be required by an {@link android.net.VpnService}, to ensure that only the system can bind to it." ],
        "BIND_WALLPAPER" : [ "signatureOrSystem" , "bind to wallpaper" , "Allows the holder to bind to the top-level interface of wallpaper. Should never be needed for normal applications." ],
        "BIND_DEVICE_ADMIN" : [ "signature" , "interact with device admin" , "Allows the holder to send intents to a device administrator. Should never be needed for normal applications." ],
        "SET_ORIENTATION" : [ "signature" , "change screen orientation" , "Allows an application to change the rotation of the screen at any time. Should never be needed for normal applications." ],
    "SET_POINTER_SPEED"             : [ "signature", "", "Allows low-level access to setting the pointer speed. Not for use by normal applications. " ],
    "SET_KEYBOARD_LAYOUT"           : [ "signature", "", "Allows low-level access to setting the keyboard layout. Not for use by normal applications." ],
        "INSTALL_PACKAGES" : [ "signatureOrSystem" , "directly install applications" , "Allows an application to install new or updated Android packages. Malicious applications can use this to add new applications with arbitrarily powerful permissions." ],
        "CLEAR_APP_USER_DATA" : [ "signature" , "delete other applications\' data" , "Allows an application to clear user data." ],
        "DELETE_CACHE_FILES" : [ "signatureOrSystem" , "delete other applications\' caches" , "Allows an application to delete cache files." ],
        "DELETE_PACKAGES" : [ "signatureOrSystem" , "delete applications" , "Allows an application to delete Android packages. Malicious applications can use this to delete important applications." ],
        "MOVE_PACKAGE" : [ "signatureOrSystem" , "Move application resources" , "Allows an application to move application resources from internal to external media and vice versa." ],
        "CHANGE_COMPONENT_ENABLED_STATE" : [ "signatureOrSystem" , "enable or disable application components" , "Allows an application to change whether or not a component of another application is enabled. Malicious applications can use this to disable important phone capabilities. It is important to be careful with permission, as it is possible to bring application components into an unusable, inconsistent or unstable state." ],
    "GRANT_REVOKE_PERMISSIONS"      : [ "signature", "", "Allows an application to grant or revoke specific permissions." ],
        "ACCESS_SURFACE_FLINGER" : [ "signature" , "access SurfaceFlinger" , "Allows application to use SurfaceFlinger low-level features." ],
        "READ_FRAME_BUFFER" : [ "signatureOrSystem" , "read frame buffer" , "Allows application to read the content of the frame buffer." ],
    "CONFIGURE_WIFI_DISPLAY"        : [ "signature", "", "Allows an application to configure and connect to Wifi displays" ],
    "CONTROL_WIFI_DISPLAY"          : [ "signature", "", "Allows an application to control low-level features of Wifi displays such as opening an RTSP socket.  This permission should only be used by the display manager." ],
        "BRICK" : [ "signature" , "permanently disable phone" , "Allows the application to disable the entire phone permanently. This is very dangerous." ],
        "REBOOT" : [ "signatureOrSystem" , "force phone reboot" , "Allows the application to force the phone to reboot." ],
        "DEVICE_POWER" : [ "signature" , "turn phone on or off" , "Allows the application to turn the phone on or off." ],
    "NET_TUNNELING"                 : [ "signature", "", "Allows low-level access to tun tap driver " ],
        "FACTORY_TEST" : [ "signature" , "run in factory test mode" , "Run as a low-level manufacturer test, allowing complete access to the phone hardware. Only available when a phone is running in manufacturer test mode." ],
        "MASTER_CLEAR" : [ "signatureOrSystem" , "reset system to factory defaults" , "Allows an application to completely reset the system to its factory settings, erasing all data, configuration and installed applications." ],
        "CALL_PRIVILEGED" : [ "signatureOrSystem" , "directly call any phone numbers" , "Allows the application to call any phone number, including emergency numbers, without your intervention. Malicious applications may place unnecessary and illegal calls to emergency services." ],
        "PERFORM_CDMA_PROVISIONING" : [ "signatureOrSystem" , "directly start CDMA phone setup" , "Allows the application to start CDMA provisioning. Malicious applications may start CDMA provisioning unnecessarily" ],
        "CONTROL_LOCATION_UPDATES" : [ "signatureOrSystem" , "control location update notifications" , "Allows enabling/disabling location update notifications from the radio. Not for use by normal applications." ],
        "ACCESS_CHECKIN_PROPERTIES" : [ "signatureOrSystem" , "access check-in properties" , "Allows read/write access to properties uploaded by the check-in service. Not for use by normal applications." ],
        "PACKAGE_USAGE_STATS" : [ "signatureOrSystem" , "update component usage statistics" , "Allows the modification of collected component usage statistics. Not for use by normal applications." ],
        "BACKUP" : [ "signatureOrSystem" , "control system back up and restore" , "Allows the application to control the system\'s back-up and restore mechanism. Not for use by normal applications." ],
    "CONFIRM_FULL_BACKUP"           : [ "signature", "", "Allows a package to launch the secure full-backup confirmation UI. ONLY the system process may hold this permission." ],
    "BIND_REMOTEVIEWS"              : [ "signatureOrSystem", "", "Must be required by a {@link android.widget.RemoteViewsService}, to ensure that only the system can bind to it." ],
        "ACCESS_CACHE_FILESYSTEM" : [ "signatureOrSystem" , "access the cache file system" , "Allows an application to read and write the cache file system." ],
        "COPY_PROTECTED_DATA" : [ "signature" , "Allows to invoke default container service to copy content. Not for use by normal applications." , "Allows to invoke default container service to copy content. Not for use by normal applications." ],
    "CRYPT_KEEPER" : [ "signatureOrSystem", "access to the encryption methods", "Internal permission protecting access to the encryption methods" ],
    "READ_NETWORK_USAGE_HISTORY" : [ "signatureOrSystem", "read historical network usage for specific networks and applications.", "Allows an application to read historical network usage for specific networks and applications."],
    "MANAGE_NETWORK_POLICY": [ "signature", "manage network policies and to define application-specific rules.", "Allows an application to manage network policies and to define application-specific rules."],
    "MODIFY_NETWORK_ACCOUNTING" : [ "signatureOrSystem", "account its network traffic against other UIDs.", "Allows an application to account its network traffic against other UIDs."],
        "C2D_MESSAGE" : [ "signature" , "C2DM permission." , "C2DM permission." ],
    "PACKAGE_VERIFICATION_AGENT" : [ "signatureOrSystem", "Package verifier needs to have this permission before the PackageManager will trust it to verify packages.", "Package verifier needs to have this permission before the PackageManager will trust it to verify packages."],
    "BIND_PACKAGE_VERIFIER" : [ "signature", "", "Must be required by package verifier receiver, to ensure that only the system can interact with it.."],
    "SERIAL_PORT"                   : [ "signature", "", "Allows applications to access serial ports via the SerialManager." ],
    "ACCESS_CONTENT_PROVIDERS_EXTERNALLY": [ "signature", "", "Allows the holder to access content providers from outside an ApplicationThread. This permission is enforced by the ActivityManagerService on the corresponding APIs,in particular ActivityManagerService#getContentProviderExternal(String) and ActivityManagerService#removeContentProviderExternal(String)."],
        "UPDATE_LOCK"   : [ "signatureOrSystem", "", "Allows an application to hold an UpdateLock, recommending that a headless OTA reboot "\
                         "*not* occur while the lock is held"],
        "WRITE_GSERVICES" : [ "signatureOrSystem" , "modify the Google services map" , "Allows an application to modify the Google services map. Not for use by normal applications." ],

        "ACCESS_USB" : [ "signatureOrSystem" , "access USB devices" , "Allows the application to access USB devices." ],
    },

    "MANIFEST_PERMISSION_GROUP":
        {
        "ACCOUNTS": "Permissions for direct access to the accounts managed by the Account Manager.",
        "AFFECTS_BATTERY": "Used for permissions that provide direct access to the hardware on the device that has an effect on battery life.  This includes vibrator, flashlight,  etc.",
        "APP_INFO": "Group of permissions that are related to the other applications installed on the system.",
        "AUDIO_SETTINGS": "Used for permissions that provide direct access to speaker settings the device.",
        "BLUETOOTH_NETWORK": "Used for permissions that provide access to other devices through Bluetooth.",
        "BOOKMARKS": "Used for permissions that provide access to the user bookmarks and browser history.",
        "CALENDAR": "Used for permissions that provide access to the device calendar to create / view events",
        "CAMERA": "Used for permissions that are associated with accessing camera or capturing images/video from the device.",
        "COST_MONEY": "Used for permissions that can be used to make the user spend money without their direct involvement.",
        "DEVICE_ALARMS": "Used for permissions that provide access to the user voicemail box.",
        "DEVELOPMENT_TOOLS": "Group of permissions that are related to development features.",
        "DISPLAY": "Group of permissions that allow manipulation of how another application displays UI to the user.",
        "HARDWARE_CONTROLS": "Used for permissions that provide direct access to the hardware on the device.",
        "LOCATION": "Used for permissions that allow access to the user's current location.",
        "MESSAGES": "Used for permissions that allow an application to send messages on behalf of the user or intercept messages being received by the user.",
        "MICROPHONE": "Used for permissions that are associated with accessing microphone audio from the device. Note that phone calls also capture audio but are in a separate (more visible) permission group.",
        "NETWORK": "Used for permissions that provide access to networking services.",
        "PERSONAL_INFO": "Used for permissions that provide access to the user's private data, such as contacts, calendar events, e-mail messages, etc.",
        "PHONE_CALLS": "Used for permissions that are associated with accessing and modifyign telephony state: intercepting outgoing calls, reading and modifying the phone state.",
        "STORAGE": "Group of permissions that are related to SD card access.",
        "SOCIAL_INFO": "Used for permissions that provide access to the user's social connections, such as contacts, call logs, social stream, etc.  This includes both reading and writing of this data (which should generally be expressed as two distinct permissions)",
        "SCREENLOCK": "Group of permissions that are related to the screenlock.",
        "STATUS_BAR": "Used for permissions that change the status bar.",
        "SYSTEM_CLOCK": "Group of permissions that are related to system clock.",
        "SYSTEM_TOOLS": "Group of permissions that are related to system APIs.",
        "SYNC_SETTINGS": "Used for permissions that access the sync settings or sync related information.",
        "USER_DICTIONARY": "Used for permissions that provide access to the user calendar to create / view events.",
        "VOICEMAIL": "Used for permissions that provide access to the user voicemail box.",
        "WALLPAPER": "Group of permissions that allow manipulation of how another application displays UI to the user.",
        "WRITE_USER_DICTIONARY": "Used for permissions that provide access to the user calendar to create / view events.",
    },
}


## andro conf

def is_ascii_problem(s):
    try:
        s.decode("ascii")
        return False
    except UnicodeDecodeError:
        return True


class Color(object):
    Normal = "\033[0m"
    Black = "\033[30m"
    Red = "\033[31m"
    Green = "\033[32m"
    Yellow = "\033[33m"
    Blue = "\033[34m"
    Purple = "\033[35m"
    Cyan = "\033[36m"
    Grey = "\033[37m"
    Bold = "\033[1m"


CONF = {
    "BIN_DED": "ded.sh",
    "PATH_DED": "./decompiler/ded/",
    "PATH_DEX2JAR": "./decompiler/dex2jar/",
    "BIN_DEX2JAR": "dex2jar.sh",
    "PATH_JAD": "./decompiler/jad/",
    "BIN_JAD": "jad",
    "BIN_WINEJAD": "jad.exe",
    "PATH_FERNFLOWER": "./decompiler/fernflower/",
    "BIN_FERNFLOWER": "fernflower.jar",
    "OPTIONS_FERNFLOWER": {"dgs": '1',
                           "asc": '1'},
    "PRETTY_SHOW": 1,
    "TMP_DIRECTORY": "/tmp/",
    # Full python or mix python/c++ (native)
    #"ENGINE" : "automatic",
    "ENGINE": "python",
    "RECODE_ASCII_STRING": False,
    "RECODE_ASCII_STRING_METH": None,
    "DEOBFUSCATED_STRING": True,
    #    "DEOBFUSCATED_STRING_METH" : get_deobfuscated_string,
    "PATH_JARSIGNER": "jarsigner",
    "COLORS": {
        "OFFSET": Color.Yellow,
        "OFFSET_ADDR": Color.Green,
        "INSTRUCTION_NAME": Color.Yellow,
        "BRANCH_FALSE": Color.Red,
        "BRANCH_TRUE": Color.Green,
        "BRANCH": Color.Blue,
        "EXCEPTION": Color.Cyan,
        "BB": Color.Purple,
        "NOTE": Color.Red,
        "NORMAL": Color.Normal,
        "OUTPUT": {
            "normal": Color.Normal,
            "registers": Color.Normal,
            "literal": Color.Green,
            "offset": Color.Purple,
            "raw": Color.Red,
            "string": Color.Red,
            "meth": Color.Cyan,
            "type": Color.Blue,
            "field": Color.Green,
        }
    },
    "PRINT_FCT": sys.stdout.write,
    "LAZY_ANALYSIS": False,
    "MAGIC_PATH_FILE": None,
    "DEFAULT_API": 19,
    "SESSION": None,
}


def default_colors(obj):
    CONF["COLORS"]["OFFSET"] = obj.Yellow
    CONF["COLORS"]["OFFSET_ADDR"] = obj.Green
    CONF["COLORS"]["INSTRUCTION_NAME"] = obj.Yellow
    CONF["COLORS"]["BRANCH_FALSE"] = obj.Red
    CONF["COLORS"]["BRANCH_TRUE"] = obj.Green
    CONF["COLORS"]["BRANCH"] = obj.Blue
    CONF["COLORS"]["EXCEPTION"] = obj.Cyan
    CONF["COLORS"]["BB"] = obj.Purple
    CONF["COLORS"]["NOTE"] = obj.Red
    CONF["COLORS"]["NORMAL"] = obj.Normal

    CONF["COLORS"]["OUTPUT"]["normal"] = obj.Normal
    CONF["COLORS"]["OUTPUT"]["registers"] = obj.Normal
    CONF["COLORS"]["OUTPUT"]["literal"] = obj.Green
    CONF["COLORS"]["OUTPUT"]["offset"] = obj.Purple
    CONF["COLORS"]["OUTPUT"]["raw"] = obj.Red
    CONF["COLORS"]["OUTPUT"]["string"] = obj.Red
    CONF["COLORS"]["OUTPUT"]["meth"] = obj.Cyan
    CONF["COLORS"]["OUTPUT"]["type"] = obj.Blue
    CONF["COLORS"]["OUTPUT"]["field"] = obj.Green


def disable_colors():
    """ Disable colors from the output (color = normal)"""
    for i in CONF["COLORS"]:
        if isinstance(CONF["COLORS"][i], dict):
            for j in CONF["COLORS"][i]:
                CONF["COLORS"][i][j] = Color.normal
        else:
            CONF["COLORS"][i] = Color.normal


def remove_colors():
    """ Remove colors from the output (no escape sequences)"""
    for i in CONF["COLORS"]:
        if isinstance(CONF["COLORS"][i], dict):
            for j in CONF["COLORS"][i]:
                CONF["COLORS"][i][j] = ""
        else:
            CONF["COLORS"][i] = ""


def enable_colors(colors):
    for i in colors:
        CONF["COLORS"][i] = colors[i]


def save_colors():
    c = {}
    for i in CONF["COLORS"]:
        if isinstance(CONF["COLORS"][i], dict):
            c[i] = {}
            for j in CONF["COLORS"][i]:
                c[i][j] = CONF["COLORS"][i][j]
        else:
            c[i] = CONF["COLORS"][i]
    return c


def long2int(l):
    if l > 0x7fffffff:
        l = (0x7fffffff & l) - 0x80000000
    return l


def long2str(l):
    """Convert an integer to a string."""
    if type(l) not in (types.IntType, types.LongType):
        raise ValueError, 'the input must be an integer'

    if l < 0:
        raise ValueError, 'the input must be greater than 0'
    s = ''
    while l:
        s = s + chr(l & 255L)
        l >>= 8

    return s


def str2long(s):
    """Convert a string to a long integer."""
    if type(s) not in (types.StringType, types.UnicodeType):
        raise ValueError, 'the input must be a string'

    l = 0L
    for i in s:
        l <<= 8
        l |= ord(i)

    return l


def random_string():
    return random.choice(string.letters) + ''.join([random.choice(
        string.letters + string.digits) for i in range(10 - 1)])


def is_android(filename):
    """Return the type of the file

        @param filename : the filename
        @rtype : "APK", "DEX", "ELF", None
    """
    if not filename:
        return None

    val = None
    with open(filename, "r") as fd:
        f_bytes = fd.read()
        val = is_android_raw(f_bytes)

    return val


def is_android_raw(raw):
    val = None

    if raw[0:2] == "PK":
        val = "APK"
    elif raw[0:3] == "dex":
        val = "DEX"
    elif raw[0:3] == "dey":
        val = "DEY"
    elif raw[0:7] == "\x7fELF\x01\x01\x01":
        val = "ELF"
    elif raw[0:4] == "\x03\x00\x08\x00":
        val = "AXML"
    elif raw[0:4] == "\x02\x00\x0C\x00":
        val = "ARSC"
    elif ('AndroidManifest.xml' in raw and
          'META-INF/MANIFEST.MF' in raw):
        val = "APK"

    return val


def is_valid_android_raw(raw):
    return raw.find("classes.dex") != -1

# from scapy
log_andro = logging.getLogger("apkinfo")
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
log_andro.addHandler(console_handler)
log_runtime = logging.getLogger("apkinfo.runtime")  # logs at runtime
log_interactive = logging.getLogger("andro.interactive")  # logs in interactive functions
log_loading = logging.getLogger("apkinfo.loading")  # logs when loading andro


def set_lazy():
    CONF["LAZY_ANALYSIS"] = True


def set_debug():
    log_andro.setLevel(logging.DEBUG)


def set_info():
    log_andro.setLevel(logging.INFO)


def get_debug():
    return log_andro.getEffectiveLevel() == logging.DEBUG


def warning(x):
    log_runtime.warning(x)
    import traceback
    traceback.print_exc()


def error(x):
    log_runtime.error(x)
    raise ()


def debug(x):
    log_runtime.debug(x)


def info(x):
    log_runtime.info(x)


def set_options(key, value):
    CONF[key] = value


def save_to_disk(buff, output):
    with open(output, "w") as fd:
        fd.write(buff)


def rrmdir(directory):
    for root, dirs, files in os.walk(directory, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))
    os.rmdir(directory)


def make_color_tuple(color):
    """
    turn something like "#000000" into 0,0,0
    or "#FFFFFF into "255,255,255"
    """
    R = color[1:3]
    G = color[3:5]
    B = color[5:7]

    R = int(R, 16)
    G = int(G, 16)
    B = int(B, 16)

    return R, G, B


def interpolate_tuple(startcolor, goalcolor, steps):
    """
    Take two RGB color sets and mix them over a specified number of steps.  Return the list
    """
    # white

    R = startcolor[0]
    G = startcolor[1]
    B = startcolor[2]

    targetR = goalcolor[0]
    targetG = goalcolor[1]
    targetB = goalcolor[2]

    DiffR = targetR - R
    DiffG = targetG - G
    DiffB = targetB - B

    buffer = []

    for i in range(0, steps + 1):
        iR = R + (DiffR * i / steps)
        iG = G + (DiffG * i / steps)
        iB = B + (DiffB * i / steps)

        hR = string.replace(hex(iR), "0x", "")
        hG = string.replace(hex(iG), "0x", "")
        hB = string.replace(hex(iB), "0x", "")

        if len(hR) == 1:
            hR = "0" + hR
        if len(hB) == 1:
            hB = "0" + hB

        if len(hG) == 1:
            hG = "0" + hG

        color = string.upper("#" + hR + hG + hB)
        buffer.append(color)

    return buffer


def color_range(startcolor, goalcolor, steps):
    """
    wrapper for interpolate_tuple that accepts colors as html ("#CCCCC" and such)
    """
    start_tuple = make_color_tuple(startcolor)
    goal_tuple = make_color_tuple(goalcolor)

    return interpolate_tuple(start_tuple, goal_tuple, steps)


### public resources
resources = {
    'style': {
        'Animation' : 16973824,
        'Animation.Activity' : 16973825,
        'Animation.Dialog' : 16973826,
        'Animation.InputMethod' : 16973910,
        'Animation.Toast' : 16973828,
        'Animation.Translucent' : 16973827,
        'DeviceDefault.ButtonBar' : 16974287,
        'DeviceDefault.ButtonBar.AlertDialog' : 16974288,
        'DeviceDefault.Light.ButtonBar' : 16974290,
        'DeviceDefault.Light.ButtonBar.AlertDialog' : 16974291,
        'DeviceDefault.Light.SegmentedButton' : 16974292,
        'DeviceDefault.SegmentedButton' : 16974289,
        'Holo.ButtonBar' : 16974053,
        'Holo.ButtonBar.AlertDialog' : 16974055,
        'Holo.Light.ButtonBar' : 16974054,
        'Holo.Light.ButtonBar.AlertDialog' : 16974056,
        'Holo.Light.SegmentedButton' : 16974058,
        'Holo.SegmentedButton' : 16974057,
        'MediaButton' : 16973879,
        'MediaButton.Ffwd' : 16973883,
        'MediaButton.Next' : 16973881,
        'MediaButton.Pause' : 16973885,
        'MediaButton.Play' : 16973882,
        'MediaButton.Previous' : 16973880,
        'MediaButton.Rew' : 16973884,
        'TextAppearance' : 16973886,
        'TextAppearance.DeviceDefault' : 16974253,
        'TextAppearance.DeviceDefault.DialogWindowTitle' : 16974264,
        'TextAppearance.DeviceDefault.Inverse' : 16974254,
        'TextAppearance.DeviceDefault.Large' : 16974255,
        'TextAppearance.DeviceDefault.Large.Inverse' : 16974256,
        'TextAppearance.DeviceDefault.Medium' : 16974257,
        'TextAppearance.DeviceDefault.Medium.Inverse' : 16974258,
        'TextAppearance.DeviceDefault.SearchResult.Subtitle' : 16974262,
        'TextAppearance.DeviceDefault.SearchResult.Title' : 16974261,
        'TextAppearance.DeviceDefault.Small' : 16974259,
        'TextAppearance.DeviceDefault.Small.Inverse' : 16974260,
        'TextAppearance.DeviceDefault.Widget' : 16974265,
        'TextAppearance.DeviceDefault.Widget.ActionBar.Menu' : 16974286,
        'TextAppearance.DeviceDefault.Widget.ActionBar.Subtitle' : 16974279,
        'TextAppearance.DeviceDefault.Widget.ActionBar.Subtitle.Inverse' : 16974283,
        'TextAppearance.DeviceDefault.Widget.ActionBar.Title' : 16974278,
        'TextAppearance.DeviceDefault.Widget.ActionBar.Title.Inverse' : 16974282,
        'TextAppearance.DeviceDefault.Widget.ActionMode.Subtitle' : 16974281,
        'TextAppearance.DeviceDefault.Widget.ActionMode.Subtitle.Inverse' : 16974285,
        'TextAppearance.DeviceDefault.Widget.ActionMode.Title' : 16974280,
        'TextAppearance.DeviceDefault.Widget.ActionMode.Title.Inverse' : 16974284,
        'TextAppearance.DeviceDefault.Widget.Button' : 16974266,
        'TextAppearance.DeviceDefault.Widget.DropDownHint' : 16974271,
        'TextAppearance.DeviceDefault.Widget.DropDownItem' : 16974272,
        'TextAppearance.DeviceDefault.Widget.EditText' : 16974274,
        'TextAppearance.DeviceDefault.Widget.IconMenu.Item' : 16974267,
        'TextAppearance.DeviceDefault.Widget.PopupMenu' : 16974275,
        'TextAppearance.DeviceDefault.Widget.PopupMenu.Large' : 16974276,
        'TextAppearance.DeviceDefault.Widget.PopupMenu.Small' : 16974277,
        'TextAppearance.DeviceDefault.Widget.TabWidget' : 16974268,
        'TextAppearance.DeviceDefault.Widget.TextView' : 16974269,
        'TextAppearance.DeviceDefault.Widget.TextView.PopupMenu' : 16974270,
        'TextAppearance.DeviceDefault.Widget.TextView.SpinnerItem' : 16974273,
        'TextAppearance.DeviceDefault.WindowTitle' : 16974263,
        'TextAppearance.DialogWindowTitle' : 16973889,
        'TextAppearance.Holo' : 16974075,
        'TextAppearance.Holo.DialogWindowTitle' : 16974103,
        'TextAppearance.Holo.Inverse' : 16974076,
        'TextAppearance.Holo.Large' : 16974077,
        'TextAppearance.Holo.Large.Inverse' : 16974078,
        'TextAppearance.Holo.Medium' : 16974079,
        'TextAppearance.Holo.Medium.Inverse' : 16974080,
        'TextAppearance.Holo.SearchResult.Subtitle' : 16974084,
        'TextAppearance.Holo.SearchResult.Title' : 16974083,
        'TextAppearance.Holo.Small' : 16974081,
        'TextAppearance.Holo.Small.Inverse' : 16974082,
        'TextAppearance.Holo.Widget' : 16974085,
        'TextAppearance.Holo.Widget.ActionBar.Menu' : 16974112,
        'TextAppearance.Holo.Widget.ActionBar.Subtitle' : 16974099,
        'TextAppearance.Holo.Widget.ActionBar.Subtitle.Inverse' : 16974109,
        'TextAppearance.Holo.Widget.ActionBar.Title' : 16974098,
        'TextAppearance.Holo.Widget.ActionBar.Title.Inverse' : 16974108,
        'TextAppearance.Holo.Widget.ActionMode.Subtitle' : 16974101,
        'TextAppearance.Holo.Widget.ActionMode.Subtitle.Inverse' : 16974111,
        'TextAppearance.Holo.Widget.ActionMode.Title' : 16974100,
        'TextAppearance.Holo.Widget.ActionMode.Title.Inverse' : 16974110,
        'TextAppearance.Holo.Widget.Button' : 16974086,
        'TextAppearance.Holo.Widget.DropDownHint' : 16974091,
        'TextAppearance.Holo.Widget.DropDownItem' : 16974092,
        'TextAppearance.Holo.Widget.EditText' : 16974094,
        'TextAppearance.Holo.Widget.IconMenu.Item' : 16974087,
        'TextAppearance.Holo.Widget.PopupMenu' : 16974095,
        'TextAppearance.Holo.Widget.PopupMenu.Large' : 16974096,
        'TextAppearance.Holo.Widget.PopupMenu.Small' : 16974097,
        'TextAppearance.Holo.Widget.TabWidget' : 16974088,
        'TextAppearance.Holo.Widget.TextView' : 16974089,
        'TextAppearance.Holo.Widget.TextView.PopupMenu' : 16974090,
        'TextAppearance.Holo.Widget.TextView.SpinnerItem' : 16974093,
        'TextAppearance.Holo.WindowTitle' : 16974102,
        'TextAppearance.Inverse' : 16973887,
        'TextAppearance.Large' : 16973890,
        'TextAppearance.Large.Inverse' : 16973891,
        'TextAppearance.Material' : 16974317,
        'TextAppearance.Material.Body1' : 16974320,
        'TextAppearance.Material.Body2' : 16974319,
        'TextAppearance.Material.Button' : 16974318,
        'TextAppearance.Material.Caption' : 16974321,
        'TextAppearance.Material.DialogWindowTitle' : 16974322,
        'TextAppearance.Material.Display1' : 16974326,
        'TextAppearance.Material.Display2' : 16974325,
        'TextAppearance.Material.Display3' : 16974324,
        'TextAppearance.Material.Display4' : 16974323,
        'TextAppearance.Material.Headline' : 16974327,
        'TextAppearance.Material.Inverse' : 16974328,
        'TextAppearance.Material.Large' : 16974329,
        'TextAppearance.Material.Large.Inverse' : 16974330,
        'TextAppearance.Material.Medium' : 16974331,
        'TextAppearance.Material.Medium.Inverse' : 16974332,
        'TextAppearance.Material.Menu' : 16974333,
        'TextAppearance.Material.Notification' : 16974334,
        'TextAppearance.Material.Notification.Emphasis' : 16974335,
        'TextAppearance.Material.Notification.Info' : 16974336,
        'TextAppearance.Material.Notification.Line2' : 16974337,
        'TextAppearance.Material.Notification.Time' : 16974338,
        'TextAppearance.Material.Notification.Title' : 16974339,
        'TextAppearance.Material.SearchResult.Subtitle' : 16974340,
        'TextAppearance.Material.SearchResult.Title' : 16974341,
        'TextAppearance.Material.Small' : 16974342,
        'TextAppearance.Material.Small.Inverse' : 16974343,
        'TextAppearance.Material.Subhead' : 16974344,
        'TextAppearance.Material.Title' : 16974345,
        'TextAppearance.Material.Widget' : 16974347,
        'TextAppearance.Material.Widget.ActionBar.Menu' : 16974348,
        'TextAppearance.Material.Widget.ActionBar.Subtitle' : 16974349,
        'TextAppearance.Material.Widget.ActionBar.Subtitle.Inverse' : 16974350,
        'TextAppearance.Material.Widget.ActionBar.Title' : 16974351,
        'TextAppearance.Material.Widget.ActionBar.Title.Inverse' : 16974352,
        'TextAppearance.Material.Widget.ActionMode.Subtitle' : 16974353,
        'TextAppearance.Material.Widget.ActionMode.Subtitle.Inverse' : 16974354,
        'TextAppearance.Material.Widget.ActionMode.Title' : 16974355,
        'TextAppearance.Material.Widget.ActionMode.Title.Inverse' : 16974356,
        'TextAppearance.Material.Widget.Button' : 16974357,
        'TextAppearance.Material.Widget.DropDownHint' : 16974358,
        'TextAppearance.Material.Widget.DropDownItem' : 16974359,
        'TextAppearance.Material.Widget.EditText' : 16974360,
        'TextAppearance.Material.Widget.IconMenu.Item' : 16974361,
        'TextAppearance.Material.Widget.PopupMenu' : 16974362,
        'TextAppearance.Material.Widget.PopupMenu.Large' : 16974363,
        'TextAppearance.Material.Widget.PopupMenu.Small' : 16974364,
        'TextAppearance.Material.Widget.TabWidget' : 16974365,
        'TextAppearance.Material.Widget.TextView' : 16974366,
        'TextAppearance.Material.Widget.TextView.PopupMenu' : 16974367,
        'TextAppearance.Material.Widget.TextView.SpinnerItem' : 16974368,
        'TextAppearance.Material.Widget.Toolbar.Subtitle' : 16974369,
        'TextAppearance.Material.Widget.Toolbar.Title' : 16974370,
        'TextAppearance.Material.WindowTitle' : 16974346,
        'TextAppearance.Medium' : 16973892,
        'TextAppearance.Medium.Inverse' : 16973893,
        'TextAppearance.Small' : 16973894,
        'TextAppearance.Small.Inverse' : 16973895,
        'TextAppearance.StatusBar.EventContent' : 16973927,
        'TextAppearance.StatusBar.EventContent.Title' : 16973928,
        'TextAppearance.StatusBar.Icon' : 16973926,
        'TextAppearance.StatusBar.Title' : 16973925,
        'TextAppearance.SuggestionHighlight' : 16974104,
        'TextAppearance.Theme' : 16973888,
        'TextAppearance.Theme.Dialog' : 16973896,
        'TextAppearance.Widget' : 16973897,
        'TextAppearance.Widget.Button' : 16973898,
        'TextAppearance.Widget.DropDownHint' : 16973904,
        'TextAppearance.Widget.DropDownItem' : 16973905,
        'TextAppearance.Widget.EditText' : 16973900,
        'TextAppearance.Widget.IconMenu.Item' : 16973899,
        'TextAppearance.Widget.PopupMenu.Large' : 16973952,
        'TextAppearance.Widget.PopupMenu.Small' : 16973953,
        'TextAppearance.Widget.TabWidget' : 16973901,
        'TextAppearance.Widget.TextView' : 16973902,
        'TextAppearance.Widget.TextView.PopupMenu' : 16973903,
        'TextAppearance.Widget.TextView.SpinnerItem' : 16973906,
        'TextAppearance.WindowTitle' : 16973907,
        'Theme' : 16973829,
        'ThemeOverlay' : 16974407,
        'ThemeOverlay.Material' : 16974408,
        'ThemeOverlay.Material.ActionBar' : 16974409,
        'ThemeOverlay.Material.Dark' : 16974411,
        'ThemeOverlay.Material.Dark.ActionBar' : 16974412,
        'ThemeOverlay.Material.Light' : 16974410,
        'Theme.Black' : 16973832,
        'Theme.Black.NoTitleBar' : 16973833,
        'Theme.Black.NoTitleBar.Fullscreen' : 16973834,
        'Theme.DeviceDefault' : 16974120,
        'Theme.DeviceDefault.Dialog' : 16974126,
        'Theme.DeviceDefault.DialogWhenLarge' : 16974134,
        'Theme.DeviceDefault.DialogWhenLarge.NoActionBar' : 16974135,
        'Theme.DeviceDefault.Dialog.MinWidth' : 16974127,
        'Theme.DeviceDefault.Dialog.NoActionBar' : 16974128,
        'Theme.DeviceDefault.Dialog.NoActionBar.MinWidth' : 16974129,
        'Theme.DeviceDefault.InputMethod' : 16974142,
        'Theme.DeviceDefault.Light' : 16974123,
        'Theme.DeviceDefault.Light.DarkActionBar' : 16974143,
        'Theme.DeviceDefault.Light.Dialog' : 16974130,
        'Theme.DeviceDefault.Light.DialogWhenLarge' : 16974136,
        'Theme.DeviceDefault.Light.DialogWhenLarge.NoActionBar' : 16974137,
        'Theme.DeviceDefault.Light.Dialog.MinWidth' : 16974131,
        'Theme.DeviceDefault.Light.Dialog.NoActionBar' : 16974132,
        'Theme.DeviceDefault.Light.Dialog.NoActionBar.MinWidth' : 16974133,
        'Theme.DeviceDefault.Light.NoActionBar' : 16974124,
        'Theme.DeviceDefault.Light.NoActionBar.Fullscreen' : 16974125,
        'Theme.DeviceDefault.Light.NoActionBar.Overscan' : 16974304,
        'Theme.DeviceDefault.Light.NoActionBar.TranslucentDecor' : 16974308,
        'Theme.DeviceDefault.Light.Panel' : 16974139,
        'Theme.DeviceDefault.NoActionBar' : 16974121,
        'Theme.DeviceDefault.NoActionBar.Fullscreen' : 16974122,
        'Theme.DeviceDefault.NoActionBar.Overscan' : 16974303,
        'Theme.DeviceDefault.NoActionBar.TranslucentDecor' : 16974307,
        'Theme.DeviceDefault.Panel' : 16974138,
        'Theme.DeviceDefault.Settings' : 16974371,
        'Theme.DeviceDefault.Wallpaper' : 16974140,
        'Theme.DeviceDefault.Wallpaper.NoTitleBar' : 16974141,
        'Theme.Dialog' : 16973835,
        'Theme.Holo' : 16973931,
        'Theme.Holo.Dialog' : 16973935,
        'Theme.Holo.DialogWhenLarge' : 16973943,
        'Theme.Holo.DialogWhenLarge.NoActionBar' : 16973944,
        'Theme.Holo.Dialog.MinWidth' : 16973936,
        'Theme.Holo.Dialog.NoActionBar' : 16973937,
        'Theme.Holo.Dialog.NoActionBar.MinWidth' : 16973938,
        'Theme.Holo.InputMethod' : 16973951,
        'Theme.Holo.Light' : 16973934,
        'Theme.Holo.Light.DarkActionBar' : 16974105,
        'Theme.Holo.Light.Dialog' : 16973939,
        'Theme.Holo.Light.DialogWhenLarge' : 16973945,
        'Theme.Holo.Light.DialogWhenLarge.NoActionBar' : 16973946,
        'Theme.Holo.Light.Dialog.MinWidth' : 16973940,
        'Theme.Holo.Light.Dialog.NoActionBar' : 16973941,
        'Theme.Holo.Light.Dialog.NoActionBar.MinWidth' : 16973942,
        'Theme.Holo.Light.NoActionBar' : 16974064,
        'Theme.Holo.Light.NoActionBar.Fullscreen' : 16974065,
        'Theme.Holo.Light.NoActionBar.Overscan' : 16974302,
        'Theme.Holo.Light.NoActionBar.TranslucentDecor' : 16974306,
        'Theme.Holo.Light.Panel' : 16973948,
        'Theme.Holo.NoActionBar' : 16973932,
        'Theme.Holo.NoActionBar.Fullscreen' : 16973933,
        'Theme.Holo.NoActionBar.Overscan' : 16974301,
        'Theme.Holo.NoActionBar.TranslucentDecor' : 16974305,
        'Theme.Holo.Panel' : 16973947,
        'Theme.Holo.Wallpaper' : 16973949,
        'Theme.Holo.Wallpaper.NoTitleBar' : 16973950,
        'Theme.InputMethod' : 16973908,
        'Theme.Light' : 16973836,
        'Theme.Light.NoTitleBar' : 16973837,
        'Theme.Light.NoTitleBar.Fullscreen' : 16973838,
        'Theme.Light.Panel' : 16973914,
        'Theme.Light.WallpaperSettings' : 16973922,
        'Theme.Material' : 16974372,
        'Theme.Material.Dialog' : 16974373,
        'Theme.Material.DialogWhenLarge' : 16974379,
        'Theme.Material.DialogWhenLarge.NoActionBar' : 16974380,
        'Theme.Material.Dialog.Alert' : 16974374,
        'Theme.Material.Dialog.MinWidth' : 16974375,
        'Theme.Material.Dialog.NoActionBar' : 16974376,
        'Theme.Material.Dialog.NoActionBar.MinWidth' : 16974377,
        'Theme.Material.Dialog.Presentation' : 16974378,
        'Theme.Material.InputMethod' : 16974381,
        'Theme.Material.Light' : 16974391,
        'Theme.Material.Light.DarkActionBar' : 16974392,
        'Theme.Material.Light.Dialog' : 16974393,
        'Theme.Material.Light.DialogWhenLarge' : 16974399,
        'Theme.Material.Light.DialogWhenLarge.NoActionBar' : 16974400,
        'Theme.Material.Light.Dialog.Alert' : 16974394,
        'Theme.Material.Light.Dialog.MinWidth' : 16974395,
        'Theme.Material.Light.Dialog.NoActionBar' : 16974396,
        'Theme.Material.Light.Dialog.NoActionBar.MinWidth' : 16974397,
        'Theme.Material.Light.Dialog.Presentation' : 16974398,
        'Theme.Material.Light.NoActionBar' : 16974401,
        'Theme.Material.Light.NoActionBar.Fullscreen' : 16974402,
        'Theme.Material.Light.NoActionBar.Overscan' : 16974403,
        'Theme.Material.Light.NoActionBar.TranslucentDecor' : 16974404,
        'Theme.Material.Light.Panel' : 16974405,
        'Theme.Material.Light.Voice' : 16974406,
        'Theme.Material.NoActionBar' : 16974382,
        'Theme.Material.NoActionBar.Fullscreen' : 16974383,
        'Theme.Material.NoActionBar.Overscan' : 16974384,
        'Theme.Material.NoActionBar.TranslucentDecor' : 16974385,
        'Theme.Material.Panel' : 16974386,
        'Theme.Material.Settings' : 16974387,
        'Theme.Material.Voice' : 16974388,
        'Theme.Material.Wallpaper' : 16974389,
        'Theme.Material.Wallpaper.NoTitleBar' : 16974390,
        'Theme.NoDisplay' : 16973909,
        'Theme.NoTitleBar' : 16973830,
        'Theme.NoTitleBar.Fullscreen' : 16973831,
        'Theme.NoTitleBar.OverlayActionModes' : 16973930,
        'Theme.Panel' : 16973913,
        'Theme.Translucent' : 16973839,
        'Theme.Translucent.NoTitleBar' : 16973840,
        'Theme.Translucent.NoTitleBar.Fullscreen' : 16973841,
        'Theme.Wallpaper' : 16973918,
        'Theme.WallpaperSettings' : 16973921,
        'Theme.Wallpaper.NoTitleBar' : 16973919,
        'Theme.Wallpaper.NoTitleBar.Fullscreen' : 16973920,
        'Theme.WithActionBar' : 16973929,
        'Widget' : 16973842,
        'Widget.AbsListView' : 16973843,
        'Widget.ActionBar' : 16973954,
        'Widget.ActionBar.TabBar' : 16974068,
        'Widget.ActionBar.TabText' : 16974067,
        'Widget.ActionBar.TabView' : 16974066,
        'Widget.ActionButton' : 16973956,
        'Widget.ActionButton.CloseMode' : 16973960,
        'Widget.ActionButton.Overflow' : 16973959,
        'Widget.AutoCompleteTextView' : 16973863,
        'Widget.Button' : 16973844,
        'Widget.Button.Inset' : 16973845,
        'Widget.Button.Small' : 16973846,
        'Widget.Button.Toggle' : 16973847,
        'Widget.CalendarView' : 16974059,
        'Widget.CompoundButton' : 16973848,
        'Widget.CompoundButton.CheckBox' : 16973849,
        'Widget.CompoundButton.RadioButton' : 16973850,
        'Widget.CompoundButton.Star' : 16973851,
        'Widget.DatePicker' : 16974062,
        'Widget.DeviceDefault' : 16974144,
        'Widget.DeviceDefault.ActionBar' : 16974187,
        'Widget.DeviceDefault.ActionBar.Solid' : 16974195,
        'Widget.DeviceDefault.ActionBar.TabBar' : 16974194,
        'Widget.DeviceDefault.ActionBar.TabText' : 16974193,
        'Widget.DeviceDefault.ActionBar.TabView' : 16974192,
        'Widget.DeviceDefault.ActionButton' : 16974182,
        'Widget.DeviceDefault.ActionButton.CloseMode' : 16974186,
        'Widget.DeviceDefault.ActionButton.Overflow' : 16974183,
        'Widget.DeviceDefault.ActionButton.TextButton' : 16974184,
        'Widget.DeviceDefault.ActionMode' : 16974185,
        'Widget.DeviceDefault.AutoCompleteTextView' : 16974151,
        'Widget.DeviceDefault.Button' : 16974145,
        'Widget.DeviceDefault.Button.Borderless' : 16974188,
        'Widget.DeviceDefault.Button.Borderless.Small' : 16974149,
        'Widget.DeviceDefault.Button.Inset' : 16974147,
        'Widget.DeviceDefault.Button.Small' : 16974146,
        'Widget.DeviceDefault.Button.Toggle' : 16974148,
        'Widget.DeviceDefault.CalendarView' : 16974190,
        'Widget.DeviceDefault.CheckedTextView' : 16974299,
        'Widget.DeviceDefault.CompoundButton.CheckBox' : 16974152,
        'Widget.DeviceDefault.CompoundButton.RadioButton' : 16974169,
        'Widget.DeviceDefault.CompoundButton.Star' : 16974173,
        'Widget.DeviceDefault.DatePicker' : 16974191,
        'Widget.DeviceDefault.DropDownItem' : 16974177,
        'Widget.DeviceDefault.DropDownItem.Spinner' : 16974178,
        'Widget.DeviceDefault.EditText' : 16974154,
        'Widget.DeviceDefault.ExpandableListView' : 16974155,
        'Widget.DeviceDefault.FastScroll' : 16974313,
        'Widget.DeviceDefault.GridView' : 16974156,
        'Widget.DeviceDefault.HorizontalScrollView' : 16974171,
        'Widget.DeviceDefault.ImageButton' : 16974157,
        'Widget.DeviceDefault.Light' : 16974196,
        'Widget.DeviceDefault.Light.ActionBar' : 16974243,
        'Widget.DeviceDefault.Light.ActionBar.Solid' : 16974247,
        'Widget.DeviceDefault.Light.ActionBar.Solid.Inverse' : 16974248,
        'Widget.DeviceDefault.Light.ActionBar.TabBar' : 16974246,
        'Widget.DeviceDefault.Light.ActionBar.TabBar.Inverse' : 16974249,
        'Widget.DeviceDefault.Light.ActionBar.TabText' : 16974245,
        'Widget.DeviceDefault.Light.ActionBar.TabText.Inverse' : 16974251,
        'Widget.DeviceDefault.Light.ActionBar.TabView' : 16974244,
        'Widget.DeviceDefault.Light.ActionBar.TabView.Inverse' : 16974250,
        'Widget.DeviceDefault.Light.ActionButton' : 16974239,
        'Widget.DeviceDefault.Light.ActionButton.CloseMode' : 16974242,
        'Widget.DeviceDefault.Light.ActionButton.Overflow' : 16974240,
        'Widget.DeviceDefault.Light.ActionMode' : 16974241,
        'Widget.DeviceDefault.Light.ActionMode.Inverse' : 16974252,
        'Widget.DeviceDefault.Light.AutoCompleteTextView' : 16974203,
        'Widget.DeviceDefault.Light.Button' : 16974197,
        'Widget.DeviceDefault.Light.Button.Borderless.Small' : 16974201,
        'Widget.DeviceDefault.Light.Button.Inset' : 16974199,
        'Widget.DeviceDefault.Light.Button.Small' : 16974198,
        'Widget.DeviceDefault.Light.Button.Toggle' : 16974200,
        'Widget.DeviceDefault.Light.CalendarView' : 16974238,
        'Widget.DeviceDefault.Light.CheckedTextView' : 16974300,
        'Widget.DeviceDefault.Light.CompoundButton.CheckBox' : 16974204,
        'Widget.DeviceDefault.Light.CompoundButton.RadioButton' : 16974224,
        'Widget.DeviceDefault.Light.CompoundButton.Star' : 16974228,
        'Widget.DeviceDefault.Light.DropDownItem' : 16974232,
        'Widget.DeviceDefault.Light.DropDownItem.Spinner' : 16974233,
        'Widget.DeviceDefault.Light.EditText' : 16974206,
        'Widget.DeviceDefault.Light.ExpandableListView' : 16974207,
        'Widget.DeviceDefault.Light.FastScroll' : 16974315,
        'Widget.DeviceDefault.Light.GridView' : 16974208,
        'Widget.DeviceDefault.Light.HorizontalScrollView' : 16974226,
        'Widget.DeviceDefault.Light.ImageButton' : 16974209,
        'Widget.DeviceDefault.Light.ListPopupWindow' : 16974235,
        'Widget.DeviceDefault.Light.ListView' : 16974210,
        'Widget.DeviceDefault.Light.ListView.DropDown' : 16974205,
        'Widget.DeviceDefault.Light.MediaRouteButton' : 16974296,
        'Widget.DeviceDefault.Light.PopupMenu' : 16974236,
        'Widget.DeviceDefault.Light.PopupWindow' : 16974211,
        'Widget.DeviceDefault.Light.ProgressBar' : 16974212,
        'Widget.DeviceDefault.Light.ProgressBar.Horizontal' : 16974213,
        'Widget.DeviceDefault.Light.ProgressBar.Inverse' : 16974217,
        'Widget.DeviceDefault.Light.ProgressBar.Large' : 16974216,
        'Widget.DeviceDefault.Light.ProgressBar.Large.Inverse' : 16974219,
        'Widget.DeviceDefault.Light.ProgressBar.Small' : 16974214,
        'Widget.DeviceDefault.Light.ProgressBar.Small.Inverse' : 16974218,
        'Widget.DeviceDefault.Light.ProgressBar.Small.Title' : 16974215,
        'Widget.DeviceDefault.Light.RatingBar' : 16974221,
        'Widget.DeviceDefault.Light.RatingBar.Indicator' : 16974222,
        'Widget.DeviceDefault.Light.RatingBar.Small' : 16974223,
        'Widget.DeviceDefault.Light.ScrollView' : 16974225,
        'Widget.DeviceDefault.Light.SeekBar' : 16974220,
        'Widget.DeviceDefault.Light.Spinner' : 16974227,
        'Widget.DeviceDefault.Light.StackView' : 16974316,
        'Widget.DeviceDefault.Light.Tab' : 16974237,
        'Widget.DeviceDefault.Light.TabWidget' : 16974229,
        'Widget.DeviceDefault.Light.TextView' : 16974202,
        'Widget.DeviceDefault.Light.TextView.SpinnerItem' : 16974234,
        'Widget.DeviceDefault.Light.WebTextView' : 16974230,
        'Widget.DeviceDefault.Light.WebView' : 16974231,
        'Widget.DeviceDefault.ListPopupWindow' : 16974180,
        'Widget.DeviceDefault.ListView' : 16974158,
        'Widget.DeviceDefault.ListView.DropDown' : 16974153,
        'Widget.DeviceDefault.MediaRouteButton' : 16974295,
        'Widget.DeviceDefault.PopupMenu' : 16974181,
        'Widget.DeviceDefault.PopupWindow' : 16974159,
        'Widget.DeviceDefault.ProgressBar' : 16974160,
        'Widget.DeviceDefault.ProgressBar.Horizontal' : 16974161,
        'Widget.DeviceDefault.ProgressBar.Large' : 16974164,
        'Widget.DeviceDefault.ProgressBar.Small' : 16974162,
        'Widget.DeviceDefault.ProgressBar.Small.Title' : 16974163,
        'Widget.DeviceDefault.RatingBar' : 16974166,
        'Widget.DeviceDefault.RatingBar.Indicator' : 16974167,
        'Widget.DeviceDefault.RatingBar.Small' : 16974168,
        'Widget.DeviceDefault.ScrollView' : 16974170,
        'Widget.DeviceDefault.SeekBar' : 16974165,
        'Widget.DeviceDefault.Spinner' : 16974172,
        'Widget.DeviceDefault.StackView' : 16974314,
        'Widget.DeviceDefault.Tab' : 16974189,
        'Widget.DeviceDefault.TabWidget' : 16974174,
        'Widget.DeviceDefault.TextView' : 16974150,
        'Widget.DeviceDefault.TextView.SpinnerItem' : 16974179,
        'Widget.DeviceDefault.WebTextView' : 16974175,
        'Widget.DeviceDefault.WebView' : 16974176,
        'Widget.DropDownItem' : 16973867,
        'Widget.DropDownItem.Spinner' : 16973868,
        'Widget.EditText' : 16973859,
        'Widget.ExpandableListView' : 16973860,
        'Widget.FastScroll' : 16974309,
        'Widget.FragmentBreadCrumbs' : 16973961,
        'Widget.Gallery' : 16973877,
        'Widget.GridView' : 16973874,
        'Widget.Holo' : 16973962,
        'Widget.Holo.ActionBar' : 16974004,
        'Widget.Holo.ActionBar.Solid' : 16974113,
        'Widget.Holo.ActionBar.TabBar' : 16974071,
        'Widget.Holo.ActionBar.TabText' : 16974070,
        'Widget.Holo.ActionBar.TabView' : 16974069,
        'Widget.Holo.ActionButton' : 16973999,
        'Widget.Holo.ActionButton.CloseMode' : 16974003,
        'Widget.Holo.ActionButton.Overflow' : 16974000,
        'Widget.Holo.ActionButton.TextButton' : 16974001,
        'Widget.Holo.ActionMode' : 16974002,
        'Widget.Holo.AutoCompleteTextView' : 16973968,
        'Widget.Holo.Button' : 16973963,
        'Widget.Holo.Button.Borderless' : 16974050,
        'Widget.Holo.Button.Borderless.Small' : 16974106,
        'Widget.Holo.Button.Inset' : 16973965,
        'Widget.Holo.Button.Small' : 16973964,
        'Widget.Holo.Button.Toggle' : 16973966,
        'Widget.Holo.CalendarView' : 16974060,
        'Widget.Holo.CheckedTextView' : 16974297,
        'Widget.Holo.CompoundButton.CheckBox' : 16973969,
        'Widget.Holo.CompoundButton.RadioButton' : 16973986,
        'Widget.Holo.CompoundButton.Star' : 16973990,
        'Widget.Holo.DatePicker' : 16974063,
        'Widget.Holo.DropDownItem' : 16973994,
        'Widget.Holo.DropDownItem.Spinner' : 16973995,
        'Widget.Holo.EditText' : 16973971,
        'Widget.Holo.ExpandableListView' : 16973972,
        'Widget.Holo.GridView' : 16973973,
        'Widget.Holo.HorizontalScrollView' : 16973988,
        'Widget.Holo.ImageButton' : 16973974,
        'Widget.Holo.Light' : 16974005,
        'Widget.Holo.Light.ActionBar' : 16974049,
        'Widget.Holo.Light.ActionBar.Solid' : 16974114,
        'Widget.Holo.Light.ActionBar.Solid.Inverse' : 16974115,
        'Widget.Holo.Light.ActionBar.TabBar' : 16974074,
        'Widget.Holo.Light.ActionBar.TabBar.Inverse' : 16974116,
        'Widget.Holo.Light.ActionBar.TabText' : 16974073,
        'Widget.Holo.Light.ActionBar.TabText.Inverse' : 16974118,
        'Widget.Holo.Light.ActionBar.TabView' : 16974072,
        'Widget.Holo.Light.ActionBar.TabView.Inverse' : 16974117,
        'Widget.Holo.Light.ActionButton' : 16974045,
        'Widget.Holo.Light.ActionButton.CloseMode' : 16974048,
        'Widget.Holo.Light.ActionButton.Overflow' : 16974046,
        'Widget.Holo.Light.ActionMode' : 16974047,
        'Widget.Holo.Light.ActionMode.Inverse' : 16974119,
        'Widget.Holo.Light.AutoCompleteTextView' : 16974011,
        'Widget.Holo.Light.Button' : 16974006,
        'Widget.Holo.Light.Button.Borderless.Small' : 16974107,
        'Widget.Holo.Light.Button.Inset' : 16974008,
        'Widget.Holo.Light.Button.Small' : 16974007,
        'Widget.Holo.Light.Button.Toggle' : 16974009,
        'Widget.Holo.Light.CalendarView' : 16974061,
        'Widget.Holo.Light.CheckedTextView' : 16974298,
        'Widget.Holo.Light.CompoundButton.CheckBox' : 16974012,
        'Widget.Holo.Light.CompoundButton.RadioButton' : 16974032,
        'Widget.Holo.Light.CompoundButton.Star' : 16974036,
        'Widget.Holo.Light.DropDownItem' : 16974040,
        'Widget.Holo.Light.DropDownItem.Spinner' : 16974041,
        'Widget.Holo.Light.EditText' : 16974014,
        'Widget.Holo.Light.ExpandableListView' : 16974015,
        'Widget.Holo.Light.GridView' : 16974016,
        'Widget.Holo.Light.HorizontalScrollView' : 16974034,
        'Widget.Holo.Light.ImageButton' : 16974017,
        'Widget.Holo.Light.ListPopupWindow' : 16974043,
        'Widget.Holo.Light.ListView' : 16974018,
        'Widget.Holo.Light.ListView.DropDown' : 16974013,
        'Widget.Holo.Light.MediaRouteButton' : 16974294,
        'Widget.Holo.Light.PopupMenu' : 16974044,
        'Widget.Holo.Light.PopupWindow' : 16974019,
        'Widget.Holo.Light.ProgressBar' : 16974020,
        'Widget.Holo.Light.ProgressBar.Horizontal' : 16974021,
        'Widget.Holo.Light.ProgressBar.Inverse' : 16974025,
        'Widget.Holo.Light.ProgressBar.Large' : 16974024,
        'Widget.Holo.Light.ProgressBar.Large.Inverse' : 16974027,
        'Widget.Holo.Light.ProgressBar.Small' : 16974022,
        'Widget.Holo.Light.ProgressBar.Small.Inverse' : 16974026,
        'Widget.Holo.Light.ProgressBar.Small.Title' : 16974023,
        'Widget.Holo.Light.RatingBar' : 16974029,
        'Widget.Holo.Light.RatingBar.Indicator' : 16974030,
        'Widget.Holo.Light.RatingBar.Small' : 16974031,
        'Widget.Holo.Light.ScrollView' : 16974033,
        'Widget.Holo.Light.SeekBar' : 16974028,
        'Widget.Holo.Light.Spinner' : 16974035,
        'Widget.Holo.Light.Tab' : 16974052,
        'Widget.Holo.Light.TabWidget' : 16974037,
        'Widget.Holo.Light.TextView' : 16974010,
        'Widget.Holo.Light.TextView.SpinnerItem' : 16974042,
        'Widget.Holo.Light.WebTextView' : 16974038,
        'Widget.Holo.Light.WebView' : 16974039,
        'Widget.Holo.ListPopupWindow' : 16973997,
        'Widget.Holo.ListView' : 16973975,
        'Widget.Holo.ListView.DropDown' : 16973970,
        'Widget.Holo.MediaRouteButton' : 16974293,
        'Widget.Holo.PopupMenu' : 16973998,
        'Widget.Holo.PopupWindow' : 16973976,
        'Widget.Holo.ProgressBar' : 16973977,
        'Widget.Holo.ProgressBar.Horizontal' : 16973978,
        'Widget.Holo.ProgressBar.Large' : 16973981,
        'Widget.Holo.ProgressBar.Small' : 16973979,
        'Widget.Holo.ProgressBar.Small.Title' : 16973980,
        'Widget.Holo.RatingBar' : 16973983,
        'Widget.Holo.RatingBar.Indicator' : 16973984,
        'Widget.Holo.RatingBar.Small' : 16973985,
        'Widget.Holo.ScrollView' : 16973987,
        'Widget.Holo.SeekBar' : 16973982,
        'Widget.Holo.Spinner' : 16973989,
        'Widget.Holo.Tab' : 16974051,
        'Widget.Holo.TabWidget' : 16973991,
        'Widget.Holo.TextView' : 16973967,
        'Widget.Holo.TextView.SpinnerItem' : 16973996,
        'Widget.Holo.WebTextView' : 16973992,
        'Widget.Holo.WebView' : 16973993,
        'Widget.ImageButton' : 16973862,
        'Widget.ImageWell' : 16973861,
        'Widget.KeyboardView' : 16973911,
        'Widget.ListPopupWindow' : 16973957,
        'Widget.ListView' : 16973870,
        'Widget.ListView.DropDown' : 16973872,
        'Widget.ListView.Menu' : 16973873,
        'Widget.ListView.White' : 16973871,
        'Widget.Material' : 16974413,
        'Widget.Material.ActionBar' : 16974414,
        'Widget.Material.ActionBar.Solid' : 16974415,
        'Widget.Material.ActionBar.TabBar' : 16974416,
        'Widget.Material.ActionBar.TabText' : 16974417,
        'Widget.Material.ActionBar.TabView' : 16974418,
        'Widget.Material.ActionButton' : 16974419,
        'Widget.Material.ActionButton.CloseMode' : 16974420,
        'Widget.Material.ActionButton.Overflow' : 16974421,
        'Widget.Material.ActionMode' : 16974422,
        'Widget.Material.AutoCompleteTextView' : 16974423,
        'Widget.Material.Button' : 16974424,
        'Widget.Material.ButtonBar' : 16974431,
        'Widget.Material.ButtonBar.AlertDialog' : 16974432,
        'Widget.Material.Button.Borderless' : 16974425,
        'Widget.Material.Button.Borderless.Colored' : 16974426,
        'Widget.Material.Button.Borderless.Small' : 16974427,
        'Widget.Material.Button.Inset' : 16974428,
        'Widget.Material.Button.Small' : 16974429,
        'Widget.Material.Button.Toggle' : 16974430,
        'Widget.Material.CalendarView' : 16974433,
        'Widget.Material.CheckedTextView' : 16974434,
        'Widget.Material.CompoundButton.CheckBox' : 16974435,
        'Widget.Material.CompoundButton.RadioButton' : 16974436,
        'Widget.Material.CompoundButton.Star' : 16974437,
        'Widget.Material.DatePicker' : 16974438,
        'Widget.Material.DropDownItem' : 16974439,
        'Widget.Material.DropDownItem.Spinner' : 16974440,
        'Widget.Material.EditText' : 16974441,
        'Widget.Material.ExpandableListView' : 16974442,
        'Widget.Material.FastScroll' : 16974443,
        'Widget.Material.GridView' : 16974444,
        'Widget.Material.HorizontalScrollView' : 16974445,
        'Widget.Material.ImageButton' : 16974446,
        'Widget.Material.Light' : 16974478,
        'Widget.Material.Light.ActionBar' : 16974479,
        'Widget.Material.Light.ActionBar.Solid' : 16974480,
        'Widget.Material.Light.ActionBar.TabBar' : 16974481,
        'Widget.Material.Light.ActionBar.TabText' : 16974482,
        'Widget.Material.Light.ActionBar.TabView' : 16974483,
        'Widget.Material.Light.ActionButton' : 16974484,
        'Widget.Material.Light.ActionButton.CloseMode' : 16974485,
        'Widget.Material.Light.ActionButton.Overflow' : 16974486,
        'Widget.Material.Light.ActionMode' : 16974487,
        'Widget.Material.Light.AutoCompleteTextView' : 16974488,
        'Widget.Material.Light.Button' : 16974489,
        'Widget.Material.Light.ButtonBar' : 16974496,
        'Widget.Material.Light.ButtonBar.AlertDialog' : 16974497,
        'Widget.Material.Light.Button.Borderless' : 16974490,
        'Widget.Material.Light.Button.Borderless.Colored' : 16974491,
        'Widget.Material.Light.Button.Borderless.Small' : 16974492,
        'Widget.Material.Light.Button.Inset' : 16974493,
        'Widget.Material.Light.Button.Small' : 16974494,
        'Widget.Material.Light.Button.Toggle' : 16974495,
        'Widget.Material.Light.CalendarView' : 16974498,
        'Widget.Material.Light.CheckedTextView' : 16974499,
        'Widget.Material.Light.CompoundButton.CheckBox' : 16974500,
        'Widget.Material.Light.CompoundButton.RadioButton' : 16974501,
        'Widget.Material.Light.CompoundButton.Star' : 16974502,
        'Widget.Material.Light.DatePicker' : 16974503,
        'Widget.Material.Light.DropDownItem' : 16974504,
        'Widget.Material.Light.DropDownItem.Spinner' : 16974505,
        'Widget.Material.Light.EditText' : 16974506,
        'Widget.Material.Light.ExpandableListView' : 16974507,
        'Widget.Material.Light.FastScroll' : 16974508,
        'Widget.Material.Light.GridView' : 16974509,
        'Widget.Material.Light.HorizontalScrollView' : 16974510,
        'Widget.Material.Light.ImageButton' : 16974511,
        'Widget.Material.Light.ListPopupWindow' : 16974512,
        'Widget.Material.Light.ListView' : 16974513,
        'Widget.Material.Light.ListView.DropDown' : 16974514,
        'Widget.Material.Light.MediaRouteButton' : 16974515,
        'Widget.Material.Light.PopupMenu' : 16974516,
        'Widget.Material.Light.PopupMenu.Overflow' : 16974517,
        'Widget.Material.Light.PopupWindow' : 16974518,
        'Widget.Material.Light.ProgressBar' : 16974519,
        'Widget.Material.Light.ProgressBar.Horizontal' : 16974520,
        'Widget.Material.Light.ProgressBar.Inverse' : 16974521,
        'Widget.Material.Light.ProgressBar.Large' : 16974522,
        'Widget.Material.Light.ProgressBar.Large.Inverse' : 16974523,
        'Widget.Material.Light.ProgressBar.Small' : 16974524,
        'Widget.Material.Light.ProgressBar.Small.Inverse' : 16974525,
        'Widget.Material.Light.ProgressBar.Small.Title' : 16974526,
        'Widget.Material.Light.RatingBar' : 16974527,
        'Widget.Material.Light.RatingBar.Indicator' : 16974528,
        'Widget.Material.Light.RatingBar.Small' : 16974529,
        'Widget.Material.Light.ScrollView' : 16974530,
        'Widget.Material.Light.SearchView' : 16974531,
        'Widget.Material.Light.SeekBar' : 16974532,
        'Widget.Material.Light.SegmentedButton' : 16974533,
        'Widget.Material.Light.Spinner' : 16974535,
        'Widget.Material.Light.Spinner.Underlined' : 16974536,
        'Widget.Material.Light.StackView' : 16974534,
        'Widget.Material.Light.Tab' : 16974537,
        'Widget.Material.Light.TabWidget' : 16974538,
        'Widget.Material.Light.TextView' : 16974539,
        'Widget.Material.Light.TextView.SpinnerItem' : 16974540,
        'Widget.Material.Light.TimePicker' : 16974541,
        'Widget.Material.Light.WebTextView' : 16974542,
        'Widget.Material.Light.WebView' : 16974543,
        'Widget.Material.ListPopupWindow' : 16974447,
        'Widget.Material.ListView' : 16974448,
        'Widget.Material.ListView.DropDown' : 16974449,
        'Widget.Material.MediaRouteButton' : 16974450,
        'Widget.Material.PopupMenu' : 16974451,
        'Widget.Material.PopupMenu.Overflow' : 16974452,
        'Widget.Material.PopupWindow' : 16974453,
        'Widget.Material.ProgressBar' : 16974454,
        'Widget.Material.ProgressBar.Horizontal' : 16974455,
        'Widget.Material.ProgressBar.Large' : 16974456,
        'Widget.Material.ProgressBar.Small' : 16974457,
        'Widget.Material.ProgressBar.Small.Title' : 16974458,
        'Widget.Material.RatingBar' : 16974459,
        'Widget.Material.RatingBar.Indicator' : 16974460,
        'Widget.Material.RatingBar.Small' : 16974461,
        'Widget.Material.ScrollView' : 16974462,
        'Widget.Material.SearchView' : 16974463,
        'Widget.Material.SeekBar' : 16974464,
        'Widget.Material.SegmentedButton' : 16974465,
        'Widget.Material.Spinner' : 16974467,
        'Widget.Material.Spinner.Underlined' : 16974468,
        'Widget.Material.StackView' : 16974466,
        'Widget.Material.Tab' : 16974469,
        'Widget.Material.TabWidget' : 16974470,
        'Widget.Material.TextView' : 16974471,
        'Widget.Material.TextView.SpinnerItem' : 16974472,
        'Widget.Material.TimePicker' : 16974473,
        'Widget.Material.Toolbar' : 16974474,
        'Widget.Material.Toolbar.Button.Navigation' : 16974475,
        'Widget.Material.WebTextView' : 16974476,
        'Widget.Material.WebView' : 16974477,
        'Widget.PopupMenu' : 16973958,
        'Widget.PopupWindow' : 16973878,
        'Widget.ProgressBar' : 16973852,
        'Widget.ProgressBar.Horizontal' : 16973855,
        'Widget.ProgressBar.Inverse' : 16973915,
        'Widget.ProgressBar.Large' : 16973853,
        'Widget.ProgressBar.Large.Inverse' : 16973916,
        'Widget.ProgressBar.Small' : 16973854,
        'Widget.ProgressBar.Small.Inverse' : 16973917,
        'Widget.RatingBar' : 16973857,
        'Widget.ScrollView' : 16973869,
        'Widget.SeekBar' : 16973856,
        'Widget.Spinner' : 16973864,
        'Widget.Spinner.DropDown' : 16973955,
        'Widget.StackView' : 16974310,
        'Widget.TabWidget' : 16973876,
        'Widget.TextView' : 16973858,
        'Widget.TextView.PopupMenu' : 16973865,
        'Widget.TextView.SpinnerItem' : 16973866,
        'Widget.Toolbar' : 16974311,
        'Widget.Toolbar.Button.Navigation' : 16974312,
        'Widget.WebView' : 16973875,
},
    'attr': {
        'theme' : 16842752,
        'label' : 16842753,
        'icon' : 16842754,
        'name' : 16842755,
        'manageSpaceActivity' : 16842756,
        'allowClearUserData' : 16842757,
        'permission' : 16842758,
        'readPermission' : 16842759,
        'writePermission' : 16842760,
        'protectionLevel' : 16842761,
        'permissionGroup' : 16842762,
        'sharedUserId' : 16842763,
        'hasCode' : 16842764,
        'persistent' : 16842765,
        'enabled' : 16842766,
        'debuggable' : 16842767,
        'exported' : 16842768,
        'process' : 16842769,
        'taskAffinity' : 16842770,
        'multiprocess' : 16842771,
        'finishOnTaskLaunch' : 16842772,
        'clearTaskOnLaunch' : 16842773,
        'stateNotNeeded' : 16842774,
        'excludeFromRecents' : 16842775,
        'authorities' : 16842776,
        'syncable' : 16842777,
        'initOrder' : 16842778,
        'grantUriPermissions' : 16842779,
        'priority' : 16842780,
        'launchMode' : 16842781,
        'screenOrientation' : 16842782,
        'configChanges' : 16842783,
        'description' : 16842784,
        'targetPackage' : 16842785,
        'handleProfiling' : 16842786,
        'functionalTest' : 16842787,
        'value' : 16842788,
        'resource' : 16842789,
        'mimeType' : 16842790,
        'scheme' : 16842791,
        'host' : 16842792,
        'port' : 16842793,
        'path' : 16842794,
        'pathPrefix' : 16842795,
        'pathPattern' : 16842796,
        'action' : 16842797,
        'data' : 16842798,
        'targetClass' : 16842799,
        'colorForeground' : 16842800,
        'colorBackground' : 16842801,
        'backgroundDimAmount' : 16842802,
        'disabledAlpha' : 16842803,
        'textAppearance' : 16842804,
        'textAppearanceInverse' : 16842805,
        'textColorPrimary' : 16842806,
        'textColorPrimaryDisableOnly' : 16842807,
        'textColorSecondary' : 16842808,
        'textColorPrimaryInverse' : 16842809,
        'textColorSecondaryInverse' : 16842810,
        'textColorPrimaryNoDisable' : 16842811,
        'textColorSecondaryNoDisable' : 16842812,
        'textColorPrimaryInverseNoDisable' : 16842813,
        'textColorSecondaryInverseNoDisable' : 16842814,
        'textColorHintInverse' : 16842815,
        'textAppearanceLarge' : 16842816,
        'textAppearanceMedium' : 16842817,
        'textAppearanceSmall' : 16842818,
        'textAppearanceLargeInverse' : 16842819,
        'textAppearanceMediumInverse' : 16842820,
        'textAppearanceSmallInverse' : 16842821,
        'textCheckMark' : 16842822,
        'textCheckMarkInverse' : 16842823,
        'buttonStyle' : 16842824,
        'buttonStyleSmall' : 16842825,
        'buttonStyleInset' : 16842826,
        'buttonStyleToggle' : 16842827,
        'galleryItemBackground' : 16842828,
        'listPreferredItemHeight' : 16842829,
        'expandableListPreferredItemPaddingLeft' : 16842830,
        'expandableListPreferredChildPaddingLeft' : 16842831,
        'expandableListPreferredItemIndicatorLeft' : 16842832,
        'expandableListPreferredItemIndicatorRight' : 16842833,
        'expandableListPreferredChildIndicatorLeft' : 16842834,
        'expandableListPreferredChildIndicatorRight' : 16842835,
        'windowBackground' : 16842836,
        'windowFrame' : 16842837,
        'windowNoTitle' : 16842838,
        'windowIsFloating' : 16842839,
        'windowIsTranslucent' : 16842840,
        'windowContentOverlay' : 16842841,
        'windowTitleSize' : 16842842,
        'windowTitleStyle' : 16842843,
        'windowTitleBackgroundStyle' : 16842844,
        'alertDialogStyle' : 16842845,
        'panelBackground' : 16842846,
        'panelFullBackground' : 16842847,
        'panelColorForeground' : 16842848,
        'panelColorBackground' : 16842849,
        'panelTextAppearance' : 16842850,
        'scrollbarSize' : 16842851,
        'scrollbarThumbHorizontal' : 16842852,
        'scrollbarThumbVertical' : 16842853,
        'scrollbarTrackHorizontal' : 16842854,
        'scrollbarTrackVertical' : 16842855,
        'scrollbarAlwaysDrawHorizontalTrack' : 16842856,
        'scrollbarAlwaysDrawVerticalTrack' : 16842857,
        'absListViewStyle' : 16842858,
        'autoCompleteTextViewStyle' : 16842859,
        'checkboxStyle' : 16842860,
        'dropDownListViewStyle' : 16842861,
        'editTextStyle' : 16842862,
        'expandableListViewStyle' : 16842863,
        'galleryStyle' : 16842864,
        'gridViewStyle' : 16842865,
        'imageButtonStyle' : 16842866,
        'imageWellStyle' : 16842867,
        'listViewStyle' : 16842868,
        'listViewWhiteStyle' : 16842869,
        'popupWindowStyle' : 16842870,
        'progressBarStyle' : 16842871,
        'progressBarStyleHorizontal' : 16842872,
        'progressBarStyleSmall' : 16842873,
        'progressBarStyleLarge' : 16842874,
        'seekBarStyle' : 16842875,
        'ratingBarStyle' : 16842876,
        'ratingBarStyleSmall' : 16842877,
        'radioButtonStyle' : 16842878,
        'scrollbarStyle' : 16842879,
        'scrollViewStyle' : 16842880,
        'spinnerStyle' : 16842881,
        'starStyle' : 16842882,
        'tabWidgetStyle' : 16842883,
        'textViewStyle' : 16842884,
        'webViewStyle' : 16842885,
        'dropDownItemStyle' : 16842886,
        'spinnerDropDownItemStyle' : 16842887,
        'dropDownHintAppearance' : 16842888,
        'spinnerItemStyle' : 16842889,
        'mapViewStyle' : 16842890,
        'preferenceScreenStyle' : 16842891,
        'preferenceCategoryStyle' : 16842892,
        'preferenceInformationStyle' : 16842893,
        'preferenceStyle' : 16842894,
        'checkBoxPreferenceStyle' : 16842895,
        'yesNoPreferenceStyle' : 16842896,
        'dialogPreferenceStyle' : 16842897,
        'editTextPreferenceStyle' : 16842898,
        'ringtonePreferenceStyle' : 16842899,
        'preferenceLayoutChild' : 16842900,
        'textSize' : 16842901,
        'typeface' : 16842902,
        'textStyle' : 16842903,
        'textColor' : 16842904,
        'textColorHighlight' : 16842905,
        'textColorHint' : 16842906,
        'textColorLink' : 16842907,
        'state_focused' : 16842908,
        'state_window_focused' : 16842909,
        'state_enabled' : 16842910,
        'state_checkable' : 16842911,
        'state_checked' : 16842912,
        'state_selected' : 16842913,
        'state_active' : 16842914,
        'state_single' : 16842915,
        'state_first' : 16842916,
        'state_middle' : 16842917,
        'state_last' : 16842918,
        'state_pressed' : 16842919,
        'state_expanded' : 16842920,
        'state_empty' : 16842921,
        'state_above_anchor' : 16842922,
        'ellipsize' : 16842923,
        'x' : 16842924,
        'y' : 16842925,
        'windowAnimationStyle' : 16842926,
        'gravity' : 16842927,
        'autoLink' : 16842928,
        'linksClickable' : 16842929,
        'entries' : 16842930,
        'layout_gravity' : 16842931,
        'windowEnterAnimation' : 16842932,
        'windowExitAnimation' : 16842933,
        'windowShowAnimation' : 16842934,
        'windowHideAnimation' : 16842935,
        'activityOpenEnterAnimation' : 16842936,
        'activityOpenExitAnimation' : 16842937,
        'activityCloseEnterAnimation' : 16842938,
        'activityCloseExitAnimation' : 16842939,
        'taskOpenEnterAnimation' : 16842940,
        'taskOpenExitAnimation' : 16842941,
        'taskCloseEnterAnimation' : 16842942,
        'taskCloseExitAnimation' : 16842943,
        'taskToFrontEnterAnimation' : 16842944,
        'taskToFrontExitAnimation' : 16842945,
        'taskToBackEnterAnimation' : 16842946,
        'taskToBackExitAnimation' : 16842947,
        'orientation' : 16842948,
        'keycode' : 16842949,
        'fullDark' : 16842950,
        'topDark' : 16842951,
        'centerDark' : 16842952,
        'bottomDark' : 16842953,
        'fullBright' : 16842954,
        'topBright' : 16842955,
        'centerBright' : 16842956,
        'bottomBright' : 16842957,
        'bottomMedium' : 16842958,
        'centerMedium' : 16842959,
        'id' : 16842960,
        'tag' : 16842961,
        'scrollX' : 16842962,
        'scrollY' : 16842963,
        'background' : 16842964,
        'padding' : 16842965,
        'paddingLeft' : 16842966,
        'paddingTop' : 16842967,
        'paddingRight' : 16842968,
        'paddingBottom' : 16842969,
        'focusable' : 16842970,
        'focusableInTouchMode' : 16842971,
        'visibility' : 16842972,
        'fitsSystemWindows' : 16842973,
        'scrollbars' : 16842974,
        'fadingEdge' : 16842975,
        'fadingEdgeLength' : 16842976,
        'nextFocusLeft' : 16842977,
        'nextFocusRight' : 16842978,
        'nextFocusUp' : 16842979,
        'nextFocusDown' : 16842980,
        'clickable' : 16842981,
        'longClickable' : 16842982,
        'saveEnabled' : 16842983,
        'drawingCacheQuality' : 16842984,
        'duplicateParentState' : 16842985,
        'clipChildren' : 16842986,
        'clipToPadding' : 16842987,
        'layoutAnimation' : 16842988,
        'animationCache' : 16842989,
        'persistentDrawingCache' : 16842990,
        'alwaysDrawnWithCache' : 16842991,
        'addStatesFromChildren' : 16842992,
        'descendantFocusability' : 16842993,
        'layout' : 16842994,
        'inflatedId' : 16842995,
        'layout_width' : 16842996,
        'layout_height' : 16842997,
        'layout_margin' : 16842998,
        'layout_marginLeft' : 16842999,
        'layout_marginTop' : 16843000,
        'layout_marginRight' : 16843001,
        'layout_marginBottom' : 16843002,
        'listSelector' : 16843003,
        'drawSelectorOnTop' : 16843004,
        'stackFromBottom' : 16843005,
        'scrollingCache' : 16843006,
        'textFilterEnabled' : 16843007,
        'transcriptMode' : 16843008,
        'cacheColorHint' : 16843009,
        'dial' : 16843010,
        'hand_hour' : 16843011,
        'hand_minute' : 16843012,
        'format' : 16843013,
        'checked' : 16843014,
        'button' : 16843015,
        'checkMark' : 16843016,
        'foreground' : 16843017,
        'measureAllChildren' : 16843018,
        'groupIndicator' : 16843019,
        'childIndicator' : 16843020,
        'indicatorLeft' : 16843021,
        'indicatorRight' : 16843022,
        'childIndicatorLeft' : 16843023,
        'childIndicatorRight' : 16843024,
        'childDivider' : 16843025,
        'animationDuration' : 16843026,
        'spacing' : 16843027,
        'horizontalSpacing' : 16843028,
        'verticalSpacing' : 16843029,
        'stretchMode' : 16843030,
        'columnWidth' : 16843031,
        'numColumns' : 16843032,
        'src' : 16843033,
        'antialias' : 16843034,
        'filter' : 16843035,
        'dither' : 16843036,
        'scaleType' : 16843037,
        'adjustViewBounds' : 16843038,
        'maxWidth' : 16843039,
        'maxHeight' : 16843040,
        'tint' : 16843041,
        'baselineAlignBottom' : 16843042,
        'cropToPadding' : 16843043,
        'textOn' : 16843044,
        'textOff' : 16843045,
        'baselineAligned' : 16843046,
        'baselineAlignedChildIndex' : 16843047,
        'weightSum' : 16843048,
        'divider' : 16843049,
        'dividerHeight' : 16843050,
        'choiceMode' : 16843051,
        'itemTextAppearance' : 16843052,
        'horizontalDivider' : 16843053,
        'verticalDivider' : 16843054,
        'headerBackground' : 16843055,
        'itemBackground' : 16843056,
        'itemIconDisabledAlpha' : 16843057,
        'rowHeight' : 16843058,
        'maxRows' : 16843059,
        'maxItemsPerRow' : 16843060,
        'moreIcon' : 16843061,
        'max' : 16843062,
        'progress' : 16843063,
        'secondaryProgress' : 16843064,
        'indeterminate' : 16843065,
        'indeterminateOnly' : 16843066,
        'indeterminateDrawable' : 16843067,
        'progressDrawable' : 16843068,
        'indeterminateDuration' : 16843069,
        'indeterminateBehavior' : 16843070,
        'minWidth' : 16843071,
        'minHeight' : 16843072,
        'interpolator' : 16843073,
        'thumb' : 16843074,
        'thumbOffset' : 16843075,
        'numStars' : 16843076,
        'rating' : 16843077,
        'stepSize' : 16843078,
        'isIndicator' : 16843079,
        'checkedButton' : 16843080,
        'stretchColumns' : 16843081,
        'shrinkColumns' : 16843082,
        'collapseColumns' : 16843083,
        'layout_column' : 16843084,
        'layout_span' : 16843085,
        'bufferType' : 16843086,
        'text' : 16843087,
        'hint' : 16843088,
        'textScaleX' : 16843089,
        'cursorVisible' : 16843090,
        'maxLines' : 16843091,
        'lines' : 16843092,
        'height' : 16843093,
        'minLines' : 16843094,
        'maxEms' : 16843095,
        'ems' : 16843096,
        'width' : 16843097,
        'minEms' : 16843098,
        'scrollHorizontally' : 16843099,
        'password' : 16843100,
        'singleLine' : 16843101,
        'selectAllOnFocus' : 16843102,
        'includeFontPadding' : 16843103,
        'maxLength' : 16843104,
        'shadowColor' : 16843105,
        'shadowDx' : 16843106,
        'shadowDy' : 16843107,
        'shadowRadius' : 16843108,
        'numeric' : 16843109,
        'digits' : 16843110,
        'phoneNumber' : 16843111,
        'inputMethod' : 16843112,
        'capitalize' : 16843113,
        'autoText' : 16843114,
        'editable' : 16843115,
        'freezesText' : 16843116,
        'drawableTop' : 16843117,
        'drawableBottom' : 16843118,
        'drawableLeft' : 16843119,
        'drawableRight' : 16843120,
        'drawablePadding' : 16843121,
        'completionHint' : 16843122,
        'completionHintView' : 16843123,
        'completionThreshold' : 16843124,
        'dropDownSelector' : 16843125,
        'popupBackground' : 16843126,
        'inAnimation' : 16843127,
        'outAnimation' : 16843128,
        'flipInterval' : 16843129,
        'fillViewport' : 16843130,
        'prompt' : 16843131,
        'startYear' : 16843132,
        'endYear' : 16843133,
        'mode' : 16843134,
        'layout_x' : 16843135,
        'layout_y' : 16843136,
        'layout_weight' : 16843137,
        'layout_toLeftOf' : 16843138,
        'layout_toRightOf' : 16843139,
        'layout_above' : 16843140,
        'layout_below' : 16843141,
        'layout_alignBaseline' : 16843142,
        'layout_alignLeft' : 16843143,
        'layout_alignTop' : 16843144,
        'layout_alignRight' : 16843145,
        'layout_alignBottom' : 16843146,
        'layout_alignParentLeft' : 16843147,
        'layout_alignParentTop' : 16843148,
        'layout_alignParentRight' : 16843149,
        'layout_alignParentBottom' : 16843150,
        'layout_centerInParent' : 16843151,
        'layout_centerHorizontal' : 16843152,
        'layout_centerVertical' : 16843153,
        'layout_alignWithParentIfMissing' : 16843154,
        'layout_scale' : 16843155,
        'visible' : 16843156,
        'variablePadding' : 16843157,
        'constantSize' : 16843158,
        'oneshot' : 16843159,
        'duration' : 16843160,
        'drawable' : 16843161,
        'shape' : 16843162,
        'innerRadiusRatio' : 16843163,
        'thicknessRatio' : 16843164,
        'startColor' : 16843165,
        'endColor' : 16843166,
        'useLevel' : 16843167,
        'angle' : 16843168,
        'type' : 16843169,
        'centerX' : 16843170,
        'centerY' : 16843171,
        'gradientRadius' : 16843172,
        'color' : 16843173,
        'dashWidth' : 16843174,
        'dashGap' : 16843175,
        'radius' : 16843176,
        'topLeftRadius' : 16843177,
        'topRightRadius' : 16843178,
        'bottomLeftRadius' : 16843179,
        'bottomRightRadius' : 16843180,
        'left' : 16843181,
        'top' : 16843182,
        'right' : 16843183,
        'bottom' : 16843184,
        'minLevel' : 16843185,
        'maxLevel' : 16843186,
        'fromDegrees' : 16843187,
        'toDegrees' : 16843188,
        'pivotX' : 16843189,
        'pivotY' : 16843190,
        'insetLeft' : 16843191,
        'insetRight' : 16843192,
        'insetTop' : 16843193,
        'insetBottom' : 16843194,
        'shareInterpolator' : 16843195,
        'fillBefore' : 16843196,
        'fillAfter' : 16843197,
        'startOffset' : 16843198,
        'repeatCount' : 16843199,
        'repeatMode' : 16843200,
        'zAdjustment' : 16843201,
        'fromXScale' : 16843202,
        'toXScale' : 16843203,
        'fromYScale' : 16843204,
        'toYScale' : 16843205,
        'fromXDelta' : 16843206,
        'toXDelta' : 16843207,
        'fromYDelta' : 16843208,
        'toYDelta' : 16843209,
        'fromAlpha' : 16843210,
        'toAlpha' : 16843211,
        'delay' : 16843212,
        'animation' : 16843213,
        'animationOrder' : 16843214,
        'columnDelay' : 16843215,
        'rowDelay' : 16843216,
        'direction' : 16843217,
        'directionPriority' : 16843218,
        'factor' : 16843219,
        'cycles' : 16843220,
        'searchMode' : 16843221,
        'searchSuggestAuthority' : 16843222,
        'searchSuggestPath' : 16843223,
        'searchSuggestSelection' : 16843224,
        'searchSuggestIntentAction' : 16843225,
        'searchSuggestIntentData' : 16843226,
        'queryActionMsg' : 16843227,
        'suggestActionMsg' : 16843228,
        'suggestActionMsgColumn' : 16843229,
        'menuCategory' : 16843230,
        'orderInCategory' : 16843231,
        'checkableBehavior' : 16843232,
        'title' : 16843233,
        'titleCondensed' : 16843234,
        'alphabeticShortcut' : 16843235,
        'numericShortcut' : 16843236,
        'checkable' : 16843237,
        'selectable' : 16843238,
        'orderingFromXml' : 16843239,
        'key' : 16843240,
        'summary' : 16843241,
        'order' : 16843242,
        'widgetLayout' : 16843243,
        'dependency' : 16843244,
        'defaultValue' : 16843245,
        'shouldDisableView' : 16843246,
        'summaryOn' : 16843247,
        'summaryOff' : 16843248,
        'disableDependentsState' : 16843249,
        'dialogTitle' : 16843250,
        'dialogMessage' : 16843251,
        'dialogIcon' : 16843252,
        'positiveButtonText' : 16843253,
        'negativeButtonText' : 16843254,
        'dialogLayout' : 16843255,
        'entryValues' : 16843256,
        'ringtoneType' : 16843257,
        'showDefault' : 16843258,
        'showSilent' : 16843259,
        'scaleWidth' : 16843260,
        'scaleHeight' : 16843261,
        'scaleGravity' : 16843262,
        'ignoreGravity' : 16843263,
        'foregroundGravity' : 16843264,
        'tileMode' : 16843265,
        'targetActivity' : 16843266,
        'alwaysRetainTaskState' : 16843267,
        'allowTaskReparenting' : 16843268,
        'searchButtonText' : 16843269,
        'colorForegroundInverse' : 16843270,
        'textAppearanceButton' : 16843271,
        'listSeparatorTextViewStyle' : 16843272,
        'streamType' : 16843273,
        'clipOrientation' : 16843274,
        'centerColor' : 16843275,
        'minSdkVersion' : 16843276,
        'windowFullscreen' : 16843277,
        'unselectedAlpha' : 16843278,
        'progressBarStyleSmallTitle' : 16843279,
        'ratingBarStyleIndicator' : 16843280,
        'apiKey' : 16843281,
        'textColorTertiary' : 16843282,
        'textColorTertiaryInverse' : 16843283,
        'listDivider' : 16843284,
        'soundEffectsEnabled' : 16843285,
        'keepScreenOn' : 16843286,
        'lineSpacingExtra' : 16843287,
        'lineSpacingMultiplier' : 16843288,
        'listChoiceIndicatorSingle' : 16843289,
        'listChoiceIndicatorMultiple' : 16843290,
        'versionCode' : 16843291,
        'versionName' : 16843292,
        'marqueeRepeatLimit' : 16843293,
        'windowNoDisplay' : 16843294,
        'backgroundDimEnabled' : 16843295,
        'inputType' : 16843296,
        'isDefault' : 16843297,
        'windowDisablePreview' : 16843298,
        'privateImeOptions' : 16843299,
        'editorExtras' : 16843300,
        'settingsActivity' : 16843301,
        'fastScrollEnabled' : 16843302,
        'reqTouchScreen' : 16843303,
        'reqKeyboardType' : 16843304,
        'reqHardKeyboard' : 16843305,
        'reqNavigation' : 16843306,
        'windowSoftInputMode' : 16843307,
        'imeFullscreenBackground' : 16843308,
        'noHistory' : 16843309,
        'headerDividersEnabled' : 16843310,
        'footerDividersEnabled' : 16843311,
        'candidatesTextStyleSpans' : 16843312,
        'smoothScrollbar' : 16843313,
        'reqFiveWayNav' : 16843314,
        'keyBackground' : 16843315,
        'keyTextSize' : 16843316,
        'labelTextSize' : 16843317,
        'keyTextColor' : 16843318,
        'keyPreviewLayout' : 16843319,
        'keyPreviewOffset' : 16843320,
        'keyPreviewHeight' : 16843321,
        'verticalCorrection' : 16843322,
        'popupLayout' : 16843323,
        'state_long_pressable' : 16843324,
        'keyWidth' : 16843325,
        'keyHeight' : 16843326,
        'horizontalGap' : 16843327,
        'verticalGap' : 16843328,
        'rowEdgeFlags' : 16843329,
        'codes' : 16843330,
        'popupKeyboard' : 16843331,
        'popupCharacters' : 16843332,
        'keyEdgeFlags' : 16843333,
        'isModifier' : 16843334,
        'isSticky' : 16843335,
        'isRepeatable' : 16843336,
        'iconPreview' : 16843337,
        'keyOutputText' : 16843338,
        'keyLabel' : 16843339,
        'keyIcon' : 16843340,
        'keyboardMode' : 16843341,
        'isScrollContainer' : 16843342,
        'fillEnabled' : 16843343,
        'updatePeriodMillis' : 16843344,
        'initialLayout' : 16843345,
        'voiceSearchMode' : 16843346,
        'voiceLanguageModel' : 16843347,
        'voicePromptText' : 16843348,
        'voiceLanguage' : 16843349,
        'voiceMaxResults' : 16843350,
        'bottomOffset' : 16843351,
        'topOffset' : 16843352,
        'allowSingleTap' : 16843353,
        'handle' : 16843354,
        'content' : 16843355,
        'animateOnClick' : 16843356,
        'configure' : 16843357,
        'hapticFeedbackEnabled' : 16843358,
        'innerRadius' : 16843359,
        'thickness' : 16843360,
        'sharedUserLabel' : 16843361,
        'dropDownWidth' : 16843362,
        'dropDownAnchor' : 16843363,
        'imeOptions' : 16843364,
        'imeActionLabel' : 16843365,
        'imeActionId' : 16843366,
        'imeExtractEnterAnimation' : 16843368,
        'imeExtractExitAnimation' : 16843369,
        'tension' : 16843370,
        'extraTension' : 16843371,
        'anyDensity' : 16843372,
        'searchSuggestThreshold' : 16843373,
        'includeInGlobalSearch' : 16843374,
        'onClick' : 16843375,
        'targetSdkVersion' : 16843376,
        'maxSdkVersion' : 16843377,
        'testOnly' : 16843378,
        'contentDescription' : 16843379,
        'gestureStrokeWidth' : 16843380,
        'gestureColor' : 16843381,
        'uncertainGestureColor' : 16843382,
        'fadeOffset' : 16843383,
        'fadeDuration' : 16843384,
        'gestureStrokeType' : 16843385,
        'gestureStrokeLengthThreshold' : 16843386,
        'gestureStrokeSquarenessThreshold' : 16843387,
        'gestureStrokeAngleThreshold' : 16843388,
        'eventsInterceptionEnabled' : 16843389,
        'fadeEnabled' : 16843390,
        'backupAgent' : 16843391,
        'allowBackup' : 16843392,
        'glEsVersion' : 16843393,
        'queryAfterZeroResults' : 16843394,
        'dropDownHeight' : 16843395,
        'smallScreens' : 16843396,
        'normalScreens' : 16843397,
        'largeScreens' : 16843398,
        'progressBarStyleInverse' : 16843399,
        'progressBarStyleSmallInverse' : 16843400,
        'progressBarStyleLargeInverse' : 16843401,
        'searchSettingsDescription' : 16843402,
        'textColorPrimaryInverseDisableOnly' : 16843403,
        'autoUrlDetect' : 16843404,
        'resizeable' : 16843405,
        'required' : 16843406,
        'accountType' : 16843407,
        'contentAuthority' : 16843408,
        'userVisible' : 16843409,
        'windowShowWallpaper' : 16843410,
        'wallpaperOpenEnterAnimation' : 16843411,
        'wallpaperOpenExitAnimation' : 16843412,
        'wallpaperCloseEnterAnimation' : 16843413,
        'wallpaperCloseExitAnimation' : 16843414,
        'wallpaperIntraOpenEnterAnimation' : 16843415,
        'wallpaperIntraOpenExitAnimation' : 16843416,
        'wallpaperIntraCloseEnterAnimation' : 16843417,
        'wallpaperIntraCloseExitAnimation' : 16843418,
        'supportsUploading' : 16843419,
        'killAfterRestore' : 16843420,
        'restoreNeedsApplication' : 16843421,
        'smallIcon' : 16843422,
        'accountPreferences' : 16843423,
        'textAppearanceSearchResultSubtitle' : 16843424,
        'textAppearanceSearchResultTitle' : 16843425,
        'summaryColumn' : 16843426,
        'detailColumn' : 16843427,
        'detailSocialSummary' : 16843428,
        'thumbnail' : 16843429,
        'detachWallpaper' : 16843430,
        'finishOnCloseSystemDialogs' : 16843431,
        'scrollbarFadeDuration' : 16843432,
        'scrollbarDefaultDelayBeforeFade' : 16843433,
        'fadeScrollbars' : 16843434,
        'colorBackgroundCacheHint' : 16843435,
        'dropDownHorizontalOffset' : 16843436,
        'dropDownVerticalOffset' : 16843437,
        'quickContactBadgeStyleWindowSmall' : 16843438,
        'quickContactBadgeStyleWindowMedium' : 16843439,
        'quickContactBadgeStyleWindowLarge' : 16843440,
        'quickContactBadgeStyleSmallWindowSmall' : 16843441,
        'quickContactBadgeStyleSmallWindowMedium' : 16843442,
        'quickContactBadgeStyleSmallWindowLarge' : 16843443,
        'author' : 16843444,
        'autoStart' : 16843445,
        'expandableListViewWhiteStyle' : 16843446,
        'installLocation' : 16843447,
        'vmSafeMode' : 16843448,
        'webTextViewStyle' : 16843449,
        'restoreAnyVersion' : 16843450,
        'tabStripLeft' : 16843451,
        'tabStripRight' : 16843452,
        'tabStripEnabled' : 16843453,
        'logo' : 16843454,
        'xlargeScreens' : 16843455,
        'immersive' : 16843456,
        'overScrollMode' : 16843457,
        'overScrollHeader' : 16843458,
        'overScrollFooter' : 16843459,
        'filterTouchesWhenObscured' : 16843460,
        'textSelectHandleLeft' : 16843461,
        'textSelectHandleRight' : 16843462,
        'textSelectHandle' : 16843463,
        'textSelectHandleWindowStyle' : 16843464,
        'popupAnimationStyle' : 16843465,
        'screenSize' : 16843466,
        'screenDensity' : 16843467,
        'allContactsName' : 16843468,
        'windowActionBar' : 16843469,
        'actionBarStyle' : 16843470,
        'navigationMode' : 16843471,
        'displayOptions' : 16843472,
        'subtitle' : 16843473,
        'customNavigationLayout' : 16843474,
        'hardwareAccelerated' : 16843475,
        'measureWithLargestChild' : 16843476,
        'animateFirstView' : 16843477,
        'dropDownSpinnerStyle' : 16843478,
        'actionDropDownStyle' : 16843479,
        'actionButtonStyle' : 16843480,
        'showAsAction' : 16843481,
        'previewImage' : 16843482,
        'actionModeBackground' : 16843483,
        'actionModeCloseDrawable' : 16843484,
        'windowActionModeOverlay' : 16843485,
        'valueFrom' : 16843486,
        'valueTo' : 16843487,
        'valueType' : 16843488,
        'propertyName' : 16843489,
        'ordering' : 16843490,
        'fragment' : 16843491,
        'windowActionBarOverlay' : 16843492,
        'fragmentOpenEnterAnimation' : 16843493,
        'fragmentOpenExitAnimation' : 16843494,
        'fragmentCloseEnterAnimation' : 16843495,
        'fragmentCloseExitAnimation' : 16843496,
        'fragmentFadeEnterAnimation' : 16843497,
        'fragmentFadeExitAnimation' : 16843498,
        'actionBarSize' : 16843499,
        'imeSubtypeLocale' : 16843500,
        'imeSubtypeMode' : 16843501,
        'imeSubtypeExtraValue' : 16843502,
        'splitMotionEvents' : 16843503,
        'listChoiceBackgroundIndicator' : 16843504,
        'spinnerMode' : 16843505,
        'animateLayoutChanges' : 16843506,
        'actionBarTabStyle' : 16843507,
        'actionBarTabBarStyle' : 16843508,
        'actionBarTabTextStyle' : 16843509,
        'actionOverflowButtonStyle' : 16843510,
        'actionModeCloseButtonStyle' : 16843511,
        'titleTextStyle' : 16843512,
        'subtitleTextStyle' : 16843513,
        'iconifiedByDefault' : 16843514,
        'actionLayout' : 16843515,
        'actionViewClass' : 16843516,
        'activatedBackgroundIndicator' : 16843517,
        'state_activated' : 16843518,
        'listPopupWindowStyle' : 16843519,
        'popupMenuStyle' : 16843520,
        'textAppearanceLargePopupMenu' : 16843521,
        'textAppearanceSmallPopupMenu' : 16843522,
        'breadCrumbTitle' : 16843523,
        'breadCrumbShortTitle' : 16843524,
        'listDividerAlertDialog' : 16843525,
        'textColorAlertDialogListItem' : 16843526,
        'loopViews' : 16843527,
        'dialogTheme' : 16843528,
        'alertDialogTheme' : 16843529,
        'dividerVertical' : 16843530,
        'homeAsUpIndicator' : 16843531,
        'enterFadeDuration' : 16843532,
        'exitFadeDuration' : 16843533,
        'selectableItemBackground' : 16843534,
        'autoAdvanceViewId' : 16843535,
        'useIntrinsicSizeAsMinimum' : 16843536,
        'actionModeCutDrawable' : 16843537,
        'actionModeCopyDrawable' : 16843538,
        'actionModePasteDrawable' : 16843539,
        'textEditPasteWindowLayout' : 16843540,
        'textEditNoPasteWindowLayout' : 16843541,
        'textIsSelectable' : 16843542,
        'windowEnableSplitTouch' : 16843543,
        'indeterminateProgressStyle' : 16843544,
        'progressBarPadding' : 16843545,
        'animationResolution' : 16843546,
        'state_accelerated' : 16843547,
        'baseline' : 16843548,
        'homeLayout' : 16843549,
        'opacity' : 16843550,
        'alpha' : 16843551,
        'transformPivotX' : 16843552,
        'transformPivotY' : 16843553,
        'translationX' : 16843554,
        'translationY' : 16843555,
        'scaleX' : 16843556,
        'scaleY' : 16843557,
        'rotation' : 16843558,
        'rotationX' : 16843559,
        'rotationY' : 16843560,
        'showDividers' : 16843561,
        'dividerPadding' : 16843562,
        'borderlessButtonStyle' : 16843563,
        'dividerHorizontal' : 16843564,
        'itemPadding' : 16843565,
        'buttonBarStyle' : 16843566,
        'buttonBarButtonStyle' : 16843567,
        'segmentedButtonStyle' : 16843568,
        'staticWallpaperPreview' : 16843569,
        'allowParallelSyncs' : 16843570,
        'isAlwaysSyncable' : 16843571,
        'verticalScrollbarPosition' : 16843572,
        'fastScrollAlwaysVisible' : 16843573,
        'fastScrollThumbDrawable' : 16843574,
        'fastScrollPreviewBackgroundLeft' : 16843575,
        'fastScrollPreviewBackgroundRight' : 16843576,
        'fastScrollTrackDrawable' : 16843577,
        'fastScrollOverlayPosition' : 16843578,
        'customTokens' : 16843579,
        'nextFocusForward' : 16843580,
        'firstDayOfWeek' : 16843581,
        'showWeekNumber' : 16843582,
        'minDate' : 16843583,
        'maxDate' : 16843584,
        'shownWeekCount' : 16843585,
        'selectedWeekBackgroundColor' : 16843586,
        'focusedMonthDateColor' : 16843587,
        'unfocusedMonthDateColor' : 16843588,
        'weekNumberColor' : 16843589,
        'weekSeparatorLineColor' : 16843590,
        'selectedDateVerticalBar' : 16843591,
        'weekDayTextAppearance' : 16843592,
        'dateTextAppearance' : 16843593,
        'solidColor' : 16843594,
        'spinnersShown' : 16843595,
        'calendarViewShown' : 16843596,
        'state_multiline' : 16843597,
        'detailsElementBackground' : 16843598,
        'textColorHighlightInverse' : 16843599,
        'textColorLinkInverse' : 16843600,
        'editTextColor' : 16843601,
        'editTextBackground' : 16843602,
        'horizontalScrollViewStyle' : 16843603,
        'layerType' : 16843604,
        'alertDialogIcon' : 16843605,
        'windowMinWidthMajor' : 16843606,
        'windowMinWidthMinor' : 16843607,
        'queryHint' : 16843608,
        'fastScrollTextColor' : 16843609,
        'largeHeap' : 16843610,
        'windowCloseOnTouchOutside' : 16843611,
        'datePickerStyle' : 16843612,
        'calendarViewStyle' : 16843613,
        'textEditSidePasteWindowLayout' : 16843614,
        'textEditSideNoPasteWindowLayout' : 16843615,
        'actionMenuTextAppearance' : 16843616,
        'actionMenuTextColor' : 16843617,
        'textCursorDrawable' : 16843618,
        'resizeMode' : 16843619,
        'requiresSmallestWidthDp' : 16843620,
        'compatibleWidthLimitDp' : 16843621,
        'largestWidthLimitDp' : 16843622,
        'state_hovered' : 16843623,
        'state_drag_can_accept' : 16843624,
        'state_drag_hovered' : 16843625,
        'stopWithTask' : 16843626,
        'switchTextOn' : 16843627,
        'switchTextOff' : 16843628,
        'switchPreferenceStyle' : 16843629,
        'switchTextAppearance' : 16843630,
        'track' : 16843631,
        'switchMinWidth' : 16843632,
        'switchPadding' : 16843633,
        'thumbTextPadding' : 16843634,
        'textSuggestionsWindowStyle' : 16843635,
        'textEditSuggestionItemLayout' : 16843636,
        'rowCount' : 16843637,
        'rowOrderPreserved' : 16843638,
        'columnCount' : 16843639,
        'columnOrderPreserved' : 16843640,
        'useDefaultMargins' : 16843641,
        'alignmentMode' : 16843642,
        'layout_row' : 16843643,
        'layout_rowSpan' : 16843644,
        'layout_columnSpan' : 16843645,
        'actionModeSelectAllDrawable' : 16843646,
        'isAuxiliary' : 16843647,
        'accessibilityEventTypes' : 16843648,
        'packageNames' : 16843649,
        'accessibilityFeedbackType' : 16843650,
        'notificationTimeout' : 16843651,
        'accessibilityFlags' : 16843652,
        'canRetrieveWindowContent' : 16843653,
        'listPreferredItemHeightLarge' : 16843654,
        'listPreferredItemHeightSmall' : 16843655,
        'actionBarSplitStyle' : 16843656,
        'actionProviderClass' : 16843657,
        'backgroundStacked' : 16843658,
        'backgroundSplit' : 16843659,
        'textAllCaps' : 16843660,
        'colorPressedHighlight' : 16843661,
        'colorLongPressedHighlight' : 16843662,
        'colorFocusedHighlight' : 16843663,
        'colorActivatedHighlight' : 16843664,
        'colorMultiSelectHighlight' : 16843665,
        'drawableStart' : 16843666,
        'drawableEnd' : 16843667,
        'actionModeStyle' : 16843668,
        'minResizeWidth' : 16843669,
        'minResizeHeight' : 16843670,
        'actionBarWidgetTheme' : 16843671,
        'uiOptions' : 16843672,
        'subtypeLocale' : 16843673,
        'subtypeExtraValue' : 16843674,
        'actionBarDivider' : 16843675,
        'actionBarItemBackground' : 16843676,
        'actionModeSplitBackground' : 16843677,
        'textAppearanceListItem' : 16843678,
        'textAppearanceListItemSmall' : 16843679,
        'targetDescriptions' : 16843680,
        'directionDescriptions' : 16843681,
        'overridesImplicitlyEnabledSubtype' : 16843682,
        'listPreferredItemPaddingLeft' : 16843683,
        'listPreferredItemPaddingRight' : 16843684,
        'requiresFadingEdge' : 16843685,
        'publicKey' : 16843686,
        'parentActivityName' : 16843687,
        'isolatedProcess' : 16843689,
        'importantForAccessibility' : 16843690,
        'keyboardLayout' : 16843691,
        'fontFamily' : 16843692,
        'mediaRouteButtonStyle' : 16843693,
        'mediaRouteTypes' : 16843694,
        'supportsRtl' : 16843695,
        'textDirection' : 16843696,
        'textAlignment' : 16843697,
        'layoutDirection' : 16843698,
        'paddingStart' : 16843699,
        'paddingEnd' : 16843700,
        'layout_marginStart' : 16843701,
        'layout_marginEnd' : 16843702,
        'layout_toStartOf' : 16843703,
        'layout_toEndOf' : 16843704,
        'layout_alignStart' : 16843705,
        'layout_alignEnd' : 16843706,
        'layout_alignParentStart' : 16843707,
        'layout_alignParentEnd' : 16843708,
        'listPreferredItemPaddingStart' : 16843709,
        'listPreferredItemPaddingEnd' : 16843710,
        'singleUser' : 16843711,
        'presentationTheme' : 16843712,
        'subtypeId' : 16843713,
        'initialKeyguardLayout' : 16843714,
        'widgetCategory' : 16843716,
        'permissionGroupFlags' : 16843717,
        'labelFor' : 16843718,
        'permissionFlags' : 16843719,
        'checkedTextViewStyle' : 16843720,
        'showOnLockScreen' : 16843721,
        'format12Hour' : 16843722,
        'format24Hour' : 16843723,
        'timeZone' : 16843724,
        'mipMap' : 16843725,
        'mirrorForRtl' : 16843726,
        'windowOverscan' : 16843727,
        'requiredForAllUsers' : 16843728,
        'indicatorStart' : 16843729,
        'indicatorEnd' : 16843730,
        'childIndicatorStart' : 16843731,
        'childIndicatorEnd' : 16843732,
        'restrictedAccountType' : 16843733,
        'requiredAccountType' : 16843734,
        'canRequestTouchExplorationMode' : 16843735,
        'canRequestEnhancedWebAccessibility' : 16843736,
        'canRequestFilterKeyEvents' : 16843737,
        'layoutMode' : 16843738,
        'keySet' : 16843739,
        'targetId' : 16843740,
        'fromScene' : 16843741,
        'toScene' : 16843742,
        'transition' : 16843743,
        'transitionOrdering' : 16843744,
        'fadingMode' : 16843745,
        'startDelay' : 16843746,
        'ssp' : 16843747,
        'sspPrefix' : 16843748,
        'sspPattern' : 16843749,
        'addPrintersActivity' : 16843750,
        'vendor' : 16843751,
        'category' : 16843752,
        'isAsciiCapable' : 16843753,
        'autoMirrored' : 16843754,
        'supportsSwitchingToNextInputMethod' : 16843755,
        'requireDeviceUnlock' : 16843756,
        'apduServiceBanner' : 16843757,
        'accessibilityLiveRegion' : 16843758,
        'windowTranslucentStatus' : 16843759,
        'windowTranslucentNavigation' : 16843760,
        'advancedPrintOptionsActivity' : 16843761,
        'banner' : 16843762,
        'windowSwipeToDismiss' : 16843763,
        'isGame' : 16843764,
        'allowEmbedded' : 16843765,
        'setupActivity' : 16843766,
        'fastScrollStyle' : 16843767,
        'windowContentTransitions' : 16843768,
        'windowContentTransitionManager' : 16843769,
        'translationZ' : 16843770,
        'tintMode' : 16843771,
        'controlX1' : 16843772,
        'controlY1' : 16843773,
        'controlX2' : 16843774,
        'controlY2' : 16843775,
        'transitionName' : 16843776,
        'transitionGroup' : 16843777,
        'viewportWidth' : 16843778,
        'viewportHeight' : 16843779,
        'fillColor' : 16843780,
        'pathData' : 16843781,
        'strokeColor' : 16843782,
        'strokeWidth' : 16843783,
        'trimPathStart' : 16843784,
        'trimPathEnd' : 16843785,
        'trimPathOffset' : 16843786,
        'strokeLineCap' : 16843787,
        'strokeLineJoin' : 16843788,
        'strokeMiterLimit' : 16843789,
        'colorControlNormal' : 16843817,
        'colorControlActivated' : 16843818,
        'colorButtonNormal' : 16843819,
        'colorControlHighlight' : 16843820,
        'persistableMode' : 16843821,
        'titleTextAppearance' : 16843822,
        'subtitleTextAppearance' : 16843823,
        'slideEdge' : 16843824,
        'actionBarTheme' : 16843825,
        'textAppearanceListItemSecondary' : 16843826,
        'colorPrimary' : 16843827,
        'colorPrimaryDark' : 16843828,
        'colorAccent' : 16843829,
        'nestedScrollingEnabled' : 16843830,
        'windowEnterTransition' : 16843831,
        'windowExitTransition' : 16843832,
        'windowSharedElementEnterTransition' : 16843833,
        'windowSharedElementExitTransition' : 16843834,
        'windowAllowReturnTransitionOverlap' : 16843835,
        'windowAllowEnterTransitionOverlap' : 16843836,
        'sessionService' : 16843837,
        'stackViewStyle' : 16843838,
        'switchStyle' : 16843839,
        'elevation' : 16843840,
        'excludeId' : 16843841,
        'excludeClass' : 16843842,
        'hideOnContentScroll' : 16843843,
        'actionOverflowMenuStyle' : 16843844,
        'documentLaunchMode' : 16843845,
        'maxRecents' : 16843846,
        'autoRemoveFromRecents' : 16843847,
        'stateListAnimator' : 16843848,
        'toId' : 16843849,
        'fromId' : 16843850,
        'reversible' : 16843851,
        'splitTrack' : 16843852,
        'targetName' : 16843853,
        'excludeName' : 16843854,
        'matchOrder' : 16843855,
        'windowDrawsSystemBarBackgrounds' : 16843856,
        'statusBarColor' : 16843857,
        'navigationBarColor' : 16843858,
        'contentInsetStart' : 16843859,
        'contentInsetEnd' : 16843860,
        'contentInsetLeft' : 16843861,
        'contentInsetRight' : 16843862,
        'paddingMode' : 16843863,
        'layout_rowWeight' : 16843864,
        'layout_columnWeight' : 16843865,
        'translateX' : 16843866,
        'translateY' : 16843867,
        'selectableItemBackgroundBorderless' : 16843868,
        'elegantTextHeight' : 16843869,
        'searchKeyphraseId' : 16843870,
        'searchKeyphrase' : 16843871,
        'searchKeyphraseSupportedLocales' : 16843872,
        'windowTransitionBackgroundFadeDuration' : 16843873,
        'overlapAnchor' : 16843874,
        'progressTint' : 16843875,
        'progressTintMode' : 16843876,
        'progressBackgroundTint' : 16843877,
        'progressBackgroundTintMode' : 16843878,
        'secondaryProgressTint' : 16843879,
        'secondaryProgressTintMode' : 16843880,
        'indeterminateTint' : 16843881,
        'indeterminateTintMode' : 16843882,
        'backgroundTint' : 16843883,
        'backgroundTintMode' : 16843884,
        'foregroundTint' : 16843885,
        'foregroundTintMode' : 16843886,
        'buttonTint' : 16843887,
        'buttonTintMode' : 16843888,
        'thumbTint' : 16843889,
        'thumbTintMode' : 16843890,
        'fullBackupOnly' : 16843891,
        'propertyXName' : 16843892,
        'propertyYName' : 16843893,
        'relinquishTaskIdentity' : 16843894,
        'tileModeX' : 16843895,
        'tileModeY' : 16843896,
        'actionModeShareDrawable' : 16843897,
        'actionModeFindDrawable' : 16843898,
        'actionModeWebSearchDrawable' : 16843899,
        'transitionVisibilityMode' : 16843900,
        'minimumHorizontalAngle' : 16843901,
        'minimumVerticalAngle' : 16843902,
        'maximumAngle' : 16843903,
        'searchViewStyle' : 16843904,
        'closeIcon' : 16843905,
        'goIcon' : 16843906,
        'searchIcon' : 16843907,
        'voiceIcon' : 16843908,
        'commitIcon' : 16843909,
        'suggestionRowLayout' : 16843910,
        'queryBackground' : 16843911,
        'submitBackground' : 16843912,
        'buttonBarPositiveButtonStyle' : 16843913,
        'buttonBarNeutralButtonStyle' : 16843914,
        'buttonBarNegativeButtonStyle' : 16843915,
        'popupElevation' : 16843916,
        'actionBarPopupTheme' : 16843917,
        'multiArch' : 16843918,
        'touchscreenBlocksFocus' : 16843919,
        'windowElevation' : 16843920,
        'launchTaskBehindTargetAnimation' : 16843921,
        'launchTaskBehindSourceAnimation' : 16843922,
        'restrictionType' : 16843923,
        'dayOfWeekBackground' : 16843924,
        'dayOfWeekTextAppearance' : 16843925,
        'headerMonthTextAppearance' : 16843926,
        'headerDayOfMonthTextAppearance' : 16843927,
        'headerYearTextAppearance' : 16843928,
        'yearListItemTextAppearance' : 16843929,
        'yearListSelectorColor' : 16843930,
        'calendarTextColor' : 16843931,
        'recognitionService' : 16843932,
        'timePickerStyle' : 16843933,
        'timePickerDialogTheme' : 16843934,
        'headerTimeTextAppearance' : 16843935,
        'headerAmPmTextAppearance' : 16843936,
        'numbersTextColor' : 16843937,
        'numbersBackgroundColor' : 16843938,
        'numbersSelectorColor' : 16843939,
        'amPmTextColor' : 16843940,
        'amPmBackgroundColor' : 16843941,
        'searchKeyphraseRecognitionFlags' : 16843942,
        'checkMarkTint' : 16843943,
        'checkMarkTintMode' : 16843944,
        'popupTheme' : 16843945,
        'toolbarStyle' : 16843946,
        'windowClipToOutline' : 16843947,
        'datePickerDialogTheme' : 16843948,
        'showText' : 16843949,
        'windowReturnTransition' : 16843950,
        'windowReenterTransition' : 16843951,
        'windowSharedElementReturnTransition' : 16843952,
        'windowSharedElementReenterTransition' : 16843953,
        'resumeWhilePausing' : 16843954,
        'datePickerMode' : 16843955,
        'timePickerMode' : 16843956,
        'inset' : 16843957,
        'letterSpacing' : 16843958,
        'fontFeatureSettings' : 16843959,
        'outlineProvider' : 16843960,
        'contentAgeHint' : 16843961,
        'country' : 16843962,
        'windowSharedElementsUseOverlay' : 16843963,
        'reparent' : 16843964,
        'reparentWithOverlay' : 16843965,
        'ambientShadowAlpha' : 16843966,
        'spotShadowAlpha' : 16843967,
        'navigationIcon' : 16843968,
        'navigationContentDescription' : 16843969,
        'fragmentExitTransition' : 16843970,
        'fragmentEnterTransition' : 16843971,
        'fragmentSharedElementEnterTransition' : 16843972,
        'fragmentReturnTransition' : 16843973,
        'fragmentSharedElementReturnTransition' : 16843974,
        'fragmentReenterTransition' : 16843975,
        'fragmentAllowEnterTransitionOverlap' : 16843976,
        'fragmentAllowReturnTransitionOverlap' : 16843977,
        'patternPathData' : 16843978,
        'strokeAlpha' : 16843979,
        'fillAlpha' : 16843980,
        'windowActivityTransitions' : 16843981,
        'colorEdgeEffect' : 16843982
    }
}

SYSTEM_RESOURCES = {
        "attributes": {
            "forward": {k: v for k, v in resources['attr'].iteritems()},
            "inverse": {v: k for k, v in resources['attr'].iteritems()}
        },
        "styles": {
            "forward": {k: v for k, v in resources['style'].iteritems()},
            "inverse": {v: k for k, v in resources['style'].iteritems()}
        }
}
