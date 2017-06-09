package com.mcxiaoke.packer.common;

import com.android.apksig.ApkVerifier;
import com.android.apksig.ApkVerifier.Builder;
import com.android.apksig.ApkVerifier.Result;
import com.android.apksig.apk.ApkFormatException;
import org.apache.commons.io.FileUtils;

import java.io.File;
import java.io.IOException;
import java.nio.ByteBuffer;
import java.security.NoSuchAlgorithmException;
import java.util.Arrays;

/**
 * User: mcxiaoke
 * Date: 2017/5/18
 * Time: 16:59
 */
public class TestUtils {
    private final static char[] CHARS = "0123456789ABCDEF".toCharArray();

    public static boolean sameBytes(byte[] a, byte[] b) {
        if (a == null || b == null) {
            return false;
        }
        if (a.length != b.length) {
            return false;
        }
        for (int i = 0; i < a.length; i++) {
            if (a[i] != b[i]) {
                return false;
            }
        }
        return true;
    }

    public static String toHex(ByteBuffer buffer) {
        final byte[] array = buffer.array();
        final int arrayOffset = buffer.arrayOffset();
        byte[] data = Arrays.copyOfRange(array, arrayOffset + buffer.position(),
                arrayOffset + buffer.limit());
        return toHex(data);
    }

    public static String toHex(byte[] bytes) {
        char[] hexChars = new char[bytes.length * 2];
        for (int j = 0; j < bytes.length; j++) {
            int v = bytes[j] & 0xFF;
            hexChars[j * 2] = CHARS[v >>> 4];
            hexChars[j * 2 + 1] = CHARS[v & 0x0F];
        }
        return new String(hexChars);
    }

    public static File newTestFile() throws IOException {
        File dir = new File("../tools/");
        File file = new File(dir, "test.apk");
        File tf = new File(dir, System.currentTimeMillis() + "-test.apk");
        FileUtils.copyFile(file, tf);
        return tf;
    }

    private static int counter = 0;

    public static void showBuffer(ByteBuffer b) {
        StringBuilder s = new StringBuilder();
        s.append("------").append(++counter).append("------\n");
        s.append("capacity=").append(b.capacity());
        s.append(" position=").append(b.position());
        s.append(" limit=").append(b.limit());
        s.append(" remaining=").append(b.remaining());
        s.append(" arrayOffset=").append(b.arrayOffset());
        s.append(" arrayLength=").append(b.array().length).append("\n");
        s.append("array=").append(toHex(b)).append("\n");
        System.out.println(s.toString());
    }

    public static void showBuffer2(final ByteBuffer buffer) {
        System.out.println("showBuffer capacity=" + buffer.capacity()
                + " position=" + buffer.position()
                + " limit=" + buffer.limit()
                + " remaining=" + buffer.remaining()
                + " arrayOffset=" + buffer.arrayOffset()
                + " arrayLength=" + buffer.array().length);
//        byte[] all = buffer.array();
//        int offset = buffer.arrayOffset();
//        int start = offset + buffer.position();
//        int end = offset + buffer.limit();
//        byte[] bytes = Arrays.copyOfRange(all, start, end);
//        System.out.println(Utils.toHex(bytes));
    }

    public static boolean apkVerified(File f) throws ApkFormatException,
            NoSuchAlgorithmException,
            IOException {
        ApkVerifier verifier = new Builder(f).build();
        Result result = verifier.verify();
        return result.isVerified()
                && result.isVerifiedUsingV1Scheme()
                && result.isVerifiedUsingV2Scheme()
                && !result.containsErrors();
    }
}
