package com.mcxiaoke.packer.zip;

import java.io.DataInput;
import java.io.DataOutput;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.channels.FileChannel;
import java.util.zip.ZipFile;

/**
 * User: mcxiaoke
 * Date: 15/11/23
 * Time: 13:12
 */
public final class ZipHelper {
    private static final String UTF_8 = "UTF-8";
    private static final int SHORT_LENGTH = 2;
    private static final String PREFIX = "MARKET=";
    private static final byte[] MAGIC = new byte[]{0x21, 0x5a, 0x58, 0x4b, 0x21}; //!ZXK!

    private static boolean isMagicMatched(byte[] buffer) {
        if (buffer.length != MAGIC.length) {
            return false;
        }
        for (int i = 0; i < MAGIC.length; ++i) {
            if (buffer[i] != MAGIC[i]) {
                return false;
            }
        }
        return true;
    }

    private static void writeBytes(byte[] data, DataOutput out) throws IOException {
        out.write(data);
    }

    private static void writeShort(int i, DataOutput out) throws IOException {
        ByteBuffer bb = ByteBuffer.allocate(SHORT_LENGTH).order(ByteOrder.LITTLE_ENDIAN);
        bb.putShort((short) i);
        out.write(bb.array());
    }

    private static short readShort(DataInput input) throws IOException {
        byte[] buf = new byte[SHORT_LENGTH];
        input.readFully(buf);
        ByteBuffer bb = ByteBuffer.wrap(buf).order(ByteOrder.LITTLE_ENDIAN);
        return bb.getShort(0);
    }


    public static void writeZipComment(File file, String comment) throws IOException {
        final ZipFile zipFile = new ZipFile(file);
        boolean hasComment = (zipFile.getComment() != null);
        zipFile.close();
        if (hasComment) {
            throw new IllegalStateException("comment already exists, ignore.");
        }
        // {@see java.util.zip.ZipOutputStream.writeEND}
        byte[] data = comment.getBytes(UTF_8);
        final RandomAccessFile raf = new RandomAccessFile(file, "rw");
        raf.seek(file.length() - SHORT_LENGTH);
        // write zip comment length
        // (content field length + length field length + magic field length)
        writeShort(data.length + SHORT_LENGTH + MAGIC.length, raf);
        // write content
        writeBytes(data, raf);
        // write content length
        writeShort(data.length, raf);
        // write magic bytes
        writeBytes(MAGIC, raf);
        raf.close();
    }

    public static String readZipComment(File file) throws IOException {
        final RandomAccessFile raf = new RandomAccessFile(file, "rw");
        try {
            long index = raf.length();
            byte[] buffer = new byte[MAGIC.length];
            index -= MAGIC.length;
            // read magic bytes
            raf.seek(index);
            raf.readFully(buffer);
            // if magic bytes matched
            if (isMagicMatched(buffer)) {
                index -= SHORT_LENGTH;
                raf.seek(index);
                // read content length field
                int length = readShort(raf);
                if (length > 0) {
                    index -= length;
                    raf.seek(index);
                    // read content bytes
                    byte[] bytesComment = new byte[length];
                    raf.readFully(bytesComment);
                    return new String(bytesComment, UTF_8);
                }
            }
        } finally {
            raf.close();
        }
        return null;
    }

    public static boolean writeMarket(final File file, final String market) throws IOException {
        if (market == null || market.length() == 0) {
            return false;
        }
        writeZipComment(file, PREFIX + market);
        return true;
    }

    public static String readMarket(final File file) throws IOException {
        final String comment = readZipComment(file);
        if (comment == null) {
            return null;
        }
        return comment.replace(PREFIX, "");
    }

    public static boolean verifyMarket(final File file, final String market) throws IOException {
        return market.equals(readMarket(file));
    }

    public static void copyFile(File src, File dest) throws IOException {
        if (!dest.exists()) {
            dest.createNewFile();
        }
        FileChannel source = null;
        FileChannel destination = null;
        try {
            source = new FileInputStream(src).getChannel();
            destination = new FileOutputStream(dest).getChannel();
            destination.transferFrom(source, 0, source.size());
        } finally {
            if (source != null) {
                source.close();
            }
            if (destination != null) {
                destination.close();
            }
        }
    }

    public static void deleteDir(File dir) {
        if (dir == null || !dir.exists()) {
            return;
        }
        final File[] files = dir.listFiles();
        if (files == null || files.length == 0) {
            return;
        }
        for (File file : files) {
            file.delete();
        }
        dir.delete();
    }

    public static void main(String[] args) throws Exception {
        if (args.length != 2) {
            System.err.println("Usage: packer your_apk_file market_name");
        }
        ZipHelper.writeMarket(new File(args[0]), args[1]);
        System.out.println(ZipHelper.readMarket(new File(args[0])));
    }

}
