package com.mcxiaoke.packer.support.walle;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;

/**
 * bridge class between support and common
 * User: mcxiaoke
 * Date: 2017/6/13
 * Time: 14:06
 */

public class Support {

    public static ByteBuffer readBlock(final File apkFile, final int id)
            throws IOException {
        return PayloadReader.readBlock(apkFile, id);
    }

    public static byte[] readBytes(final File apkFile, final int id)
            throws IOException {
        return PayloadReader.readBytes(apkFile, id);
    }

    public static void writeBlock(final File apkFile, final int id,
                                  final ByteBuffer buffer) throws IOException {
        PayloadWriter.writeBlock(apkFile, id, buffer);
    }

    public static void writeBlock(final File apkFile, final int id,
                                  final byte[] bytes) throws IOException {
        PayloadWriter.writeBlock(apkFile, id, bytes);
    }
}
