package com.mcxiaoke.packer.common;

import com.mcxiaoke.packer.support.walle.PayloadReader;
import com.mcxiaoke.packer.support.walle.PayloadWriter;

import java.io.File;
import java.io.IOException;
import java.text.DateFormat;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.HashMap;
import java.util.Locale;
import java.util.Map;
import java.util.Map.Entry;

/**
 * User: mcxiaoke
 * Date: 2017/5/26
 * Time: 13:18
 */
public class CPayload {
    // charset utf8
    private static final String UTF8 = "UTF-8";

    public static String readValue(File apkFile,
                                   String key,
                                   int blockId) throws IOException {
        final Map<String, String> map = readValues(apkFile, blockId);
        if (map == null || map.isEmpty()) {
            return null;
        }
        return map.get(key);
    }

    public static void writeValue(File apkFile,
                                  String key,
                                  String value,
                                  int blockId) throws IOException {
        final Map<String, String> values = new HashMap<>();
        values.put(key, value);
        writeValues(apkFile, values, blockId);
    }

    public static Map<String, String> readValues(File apkFile, int blockId)
            throws IOException {
        final String content = readString(apkFile, blockId);
        return mapFromString(content);
    }

    public static String readString(File apkFile, int blockId) throws IOException {
        final byte[] bytes = readBytes(apkFile, blockId);
        if (bytes == null || bytes.length == 0) {
            return null;
        }
        return new String(bytes, UTF8);
    }

    public static byte[] readBytes(File apkFile, int blockId) throws IOException {
        return PayloadReader.readBlock(apkFile, blockId);
    }

    public static void writeValues(File apkFile, Map<String, String> values, int blockId)
            throws IOException {
        if (values == null || values.isEmpty()) {
            return;
        }
        final Map<String, String> newValues = new HashMap<>();
        final Map<String, String> oldValues = readValues(apkFile, blockId);
        if (oldValues != null) {
            newValues.putAll(oldValues);
        }
        newValues.putAll(values);
        writeString(apkFile, mapToString(newValues), blockId);
    }

    public static void writeString(File apkFile, final String content, int blockId)
            throws IOException {
        PayloadWriter.writeBlock(apkFile, blockId, content.getBytes(UTF8));
    }

    public static void writeBytes(File apkFile, final byte[] bytes, int blockId)
            throws IOException {
        PayloadWriter.writeBlock(apkFile, blockId, bytes);
    }

    public static final String SEP_KV = "∘";//\u2218
    public static final String SEP_LINE = "∙";//\u2219

    private static String mapToString(final Map<String, String> map) throws IOException {
        if (map == null || map.isEmpty()) {
            return null;
        }

        final StringBuilder builder = new StringBuilder();
        for (Entry<String, String> entry : map.entrySet()) {
            builder.append(entry.getKey()).append(SEP_KV)
                    .append(entry.getValue()).append(SEP_LINE);
        }
        return builder.toString();
    }

    private static Map<String, String> mapFromString(final String string) {
        if (string == null || string.length() == 0) {
            return null;
        }
        final Map<String, String> map = new HashMap<>();
        final String[] entries = string.split(SEP_LINE);
        for (String entry : entries) {
            final String[] kv = entry.split(SEP_KV);
            if (kv.length == 2) {
                map.put(kv[0], kv[1]);
            }
        }
        return map;
    }

    private static final String DATE_FORMAT = "yyyy/MM/dd HH:mm:ss Z";

    private static String getDateString() {
        final DateFormat df = new SimpleDateFormat(DATE_FORMAT, Locale.US);
        return df.format(new Date());
    }
}
