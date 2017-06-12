package com.mcxiaoke.packer.common;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileChannel.MapMode;
import java.util.Map;

/**
 * User: mcxiaoke
 * Date: 2017/6/9
 * Time: 14:47
 */

class KMPReader {

    // zip block size max
    public static final int BLOCK_SIZE_MAX = 0x100000; // 1M

    public static String readChannel(File file) throws IOException {
        String payload = readPayload(file);
        Map<String, String> values = PackerCommon.mapFromString(payload);
        return values == null ? null : values.get(PackerCommon.CHANNEL_KEY);
    }

    public static String readPayload(File file) throws IOException {
        RandomAccessFile raf = null;
        FileChannel fc = null;
        try {
            long fileSize = file.length();
            long blockSize = BLOCK_SIZE_MAX;
            long offset = Math.max(0, fileSize - blockSize);
            raf = new RandomAccessFile(file, "r");
            fc = raf.getChannel();
            byte[] magic = PackerCommon.BLOCK_MAGIC.getBytes(PackerCommon.UTF8);
            MappedByteBuffer buffer = fc.map(MapMode.READ_ONLY, offset, blockSize);
            buffer.order(ByteOrder.LITTLE_ENDIAN);
            KMPMatch kmp = new KMPMatch(magic);
            int index = kmp.find(buffer);
            if (index < 0) {
                return null;
            }
//            System.out.println("index=" + index + " offset="
//                    + (size - blockSize + index));
            byte[] actual = new byte[magic.length];
            buffer.position(index - 1);
            buffer.get(actual);
//            System.out.println("actual=" + new String(actual, "UTF-8"));
            int len = buffer.getInt();
//            System.out.println("payload length=" + len);
            if (len < 0 || len > blockSize) {
                return null;
            }
            byte[] payload = new byte[len];
            buffer.get(payload);
//            System.out.println("payload=" + payloadStr);
            return new String(payload, PackerCommon.UTF8);
        } finally {
            if (fc != null) {
                fc.close();
            }
            if (raf != null) {
                raf.close();
            }
        }
    }
}
