package com.mcxiaoke.packer.support.walle;

import java.io.Closeable;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.util.Arrays;

/**
 * User: mcxiaoke
 * Date: 2017/5/26
 * Time: 12:10
 */
final class V2Utils {

    static byte[] getBytes(final ByteBuffer buf) {
        final byte[] array = buf.array();
        final int arrayOffset = buf.arrayOffset();
        return Arrays.copyOfRange(array, arrayOffset + buf.position(),
                arrayOffset + buf.limit());
    }

    static void close(final Closeable c) {
        if (c == null) return;
        try {
            c.close();
        } catch (IOException ignored) {
        }
    }
}
