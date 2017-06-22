package com.mcxiaoke.packer.common;

import com.mcxiaoke.packer.support.walle.Support;

import java.io.File;
import java.io.IOException;
import java.io.UnsupportedEncodingException;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.util.Arrays;
import java.util.HashMap;
import java.util.Map;
import java.util.Map.Entry;

/**
 * User: mcxiaoke
 * Date: 2017/5/26
 * Time: 13:18
 */
public class PackerCommon {
    public static final String SEP_KV = "∘";//\u2218
    public static final String SEP_LINE = "∙";//\u2219
    // charset utf8
    public static final String UTF8 = "UTF-8";
    // plugin block magic
    public static final String BLOCK_MAGIC = "Packer Ng Sig V2"; // magic

    // channel block id
    public static final int CHANNEL_BLOCK_ID = 0x7a786b21; // "zxk!"
    // channel info key
    public static final String CHANNEL_KEY = "CHANNEL";

    public static String readChannel(File file) throws IOException {
        return readValue(file, CHANNEL_KEY, CHANNEL_BLOCK_ID);
    }

    public static void writeChannel(File file, String channel)
            throws IOException {
        writeValue(file, CHANNEL_KEY, channel, CHANNEL_BLOCK_ID);
    }

    // package visible for test
    static String readValue(File file,
                            String key,
                            int blockId)
            throws IOException {
        final Map<String, String> map = readValues(file, blockId);
        if (map == null || map.isEmpty()) {
            return null;
        }
        return map.get(key);
    }

    // package visible for test
    static void writeValue(File file,
                           String key,
                           String value,
                           int blockId)
            throws IOException {
        final Map<String, String> values = new HashMap<>();
        values.put(key, value);
        writeValues(file, values, blockId);
    }

    public static Map<String, String> readValues(File file, int blockId)
            throws IOException {
        final String content = readString(file, blockId);
        return mapFromString(content);
    }

    public static String readString(File file, int blockId)
            throws IOException {
        final byte[] bytes = readBytes(file, blockId);
        if (bytes == null || bytes.length == 0) {
            return null;
        }
        return new String(bytes, UTF8);
    }

    public static byte[] readBytes(File file, int blockId)
            throws IOException {
        return readPayloadImpl(file, blockId);
    }

    public static void writeValues(File file,
                                   Map<String, String> values,
                                   int blockId)
            throws IOException {
        if (values == null || values.isEmpty()) {
            return;
        }
        final Map<String, String> newValues = new HashMap<>();
        final Map<String, String> oldValues = readValues(file, blockId);
        if (oldValues != null) {
            newValues.putAll(oldValues);
        }
        newValues.putAll(values);
        writeString(file, mapToString(newValues), blockId);
    }

    public static void writeString(File file,
                                   String content,
                                   int blockId)
            throws IOException {
        writeBytes(file, content.getBytes(UTF8), blockId);
    }

    public static void writeBytes(File file,
                                  byte[] payload,
                                  int blockId)
            throws IOException {
        writePayloadImpl(file, payload, blockId);
    }

    // package visible for test
    static void writePayloadImpl(File file,
                                 byte[] payload,
                                 int blockId)
            throws IOException {
        ByteBuffer buffer = wrapPayload(payload);
        Support.writeBlock(file, blockId, buffer);
    }

    // package visible for test
    static byte[] readPayloadImpl(File file, int blockId)
            throws IOException {
        ByteBuffer buffer = Support.readBlock(file, blockId);
        if (buffer == null) {
            return null;
        }
        byte[] magic = BLOCK_MAGIC.getBytes(UTF8);
        byte[] actual = new byte[magic.length];
        buffer.get(actual);
        if (Arrays.equals(magic, actual)) {
            int payloadLength1 = buffer.getInt();
            if (payloadLength1 > 0) {
                byte[] payload = new byte[payloadLength1];
                buffer.get(payload);
                int payloadLength2 = buffer.getInt();
                if (payloadLength2 == payloadLength1) {
                    return payload;
                }
            }
        }
        return null;
    }

    // package visible for test
    static ByteBuffer wrapPayload(byte[] payload)
            throws UnsupportedEncodingException {
        /*
          PLUGIN BLOCK LAYOUT
          OFFSET    DATA TYPE           DESCRIPTION
          @+0       magic string        magic string 16 bytes
          @+16      payload length      payload length int 4 bytes
          @+20      payload             payload data bytes
          @-4      payload length      same as @+16 4 bytes
         */
        byte[] magic = BLOCK_MAGIC.getBytes(UTF8);
        int magicLen = magic.length;
        int payloadLen = payload.length;
        int length = (magicLen + 4) * 2 + payloadLen;
        ByteBuffer buffer = ByteBuffer.allocate(length);
        buffer.order(ByteOrder.LITTLE_ENDIAN);
        buffer.put(magic); //16
        buffer.putInt(payloadLen); //4 payload length
        buffer.put(payload); // payload
        buffer.putInt(payloadLen); // 4
        buffer.flip();
        return buffer;
    }

    public static String mapToString(Map<String, String> map)
            throws IOException {
        final StringBuilder builder = new StringBuilder();
        for (Entry<String, String> entry : map.entrySet()) {
            builder.append(entry.getKey()).append(SEP_KV)
                    .append(entry.getValue()).append(SEP_LINE);
        }
        return builder.toString();
    }

    public static Map<String, String> mapFromString(final String string) {
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
