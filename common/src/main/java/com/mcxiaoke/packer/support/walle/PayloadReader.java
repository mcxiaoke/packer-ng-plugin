package com.mcxiaoke.packer.support.walle;

import java.io.File;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.channels.FileChannel;
import java.util.Map;

final class PayloadReader {
    private PayloadReader() {
        super();
    }

    public static byte[] readBytes(final File apkFile, final int id)
            throws IOException {
        final ByteBuffer buf = readBlock(apkFile, id);
        return buf == null ? null : V2Utils.getBytes(buf);
    }

    public static ByteBuffer readBlock(final File apkFile, final int id)
            throws IOException {
        final Map<Integer, ByteBuffer> blocks = readAllBlocks(apkFile);
        if (blocks == null) {
            return null;
        }
        return blocks.get(id);
    }

    private static Map<Integer, ByteBuffer> readAllBlocks(final File apkFile)
            throws IOException {
        Map<Integer, ByteBuffer> blocks = null;

        RandomAccessFile raf = null;
        FileChannel fc = null;
        try {
            raf = new RandomAccessFile(apkFile, "r");
            fc = raf.getChannel();
            final ByteBuffer apkSigningBlock = ApkUtil.findApkSigningBlock(fc).getFirst();
            blocks = ApkUtil.findIdValues(apkSigningBlock);
        } finally {
            V2Utils.close(fc);
            V2Utils.close(raf);
        }
        return blocks;
    }


}
