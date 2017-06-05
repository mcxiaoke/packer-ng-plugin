package com.mcxiaoke.packer.common;

import com.mcxiaoke.packer.support.walle.PayloadReader;
import com.mcxiaoke.packer.support.walle.PayloadWriter;

import java.io.File;
import java.io.IOException;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;

/**
 * User: mcxiaoke
 * Date: 2017/5/26
 * Time: 13:18
 */
public class Payload {
    // charset utf8
    public static final String UTF8 = "UTF-8";

    public static String readChannel(File apkFile,
                                     String channelKey,
                                     int blockId) throws IOException {
        final Map<String, String> map = readValues(apkFile, blockId);
        if (map == null || map.isEmpty()) {
            return null;
        }
        return map.get(channelKey);
    }

    public static void writeChannel(File apkFile,
                                    String channel,
                                    String channelKey,
                                    int blockId) throws IOException {
        final Map<String, String> values = new HashMap<>();
        values.put(channelKey, channel);
        writeValues(apkFile, values, blockId);
    }

    public static Map<String, String> readValues(File apkFile, int blockId)
            throws IOException {
        final String content = readRaw(apkFile, blockId);
        return mapFromString(content);
    }

    public static String readRaw(File apkFile, int blockId) throws IOException {
        final byte[] bytes = PayloadReader.readBlock(apkFile, blockId);
        if (bytes == null || bytes.length == 0) {
            return null;
        }
        return new String(bytes, UTF8);
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
        writeRaw(apkFile, mapToString(newValues), blockId);
    }

    public static void writeRaw(File apkFile, final String content, int blockId)
            throws IOException {
        PayloadWriter.writeBlock(apkFile, blockId, content.getBytes(UTF8));
    }

    private static final String SEP_KV = "\u2218";
    private static final String SEP_LINE = "\u2219";

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
}
