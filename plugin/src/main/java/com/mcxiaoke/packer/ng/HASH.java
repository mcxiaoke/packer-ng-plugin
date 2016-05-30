package com.mcxiaoke.packer.ng;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.io.UnsupportedEncodingException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;

/**
 * User: mcxiaoke
 * Date: 16/5/30
 * Time: 10:53
 */
public final class HASH {
    private static final String ENC_UTF8 = "UTF-8";
    private static final String MD5 = "MD5";
    private static final String SHA_1 = "SHA-1";
    private static final String SHA_256 = "SHA-256";
    private static final char[] DIGITS_LOWER = {'0', '1', '2', '3', '4',
            '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f'};
    private static final char[] DIGITS_UPPER = {'0', '1', '2', '3', '4',
            '5', '6', '7', '8', '9', 'A', 'B', 'C', 'D', 'E', 'F'};

    private static final int IO_BUF_SIZE = 0x1000; // 4K

    private static long copy(InputStream in, OutputStream out)
            throws IOException {
        byte[] buf = new byte[IO_BUF_SIZE];
        long total = 0;
        while (true) {
            int r = in.read(buf);
            if (r == -1) {
                break;
            }
            out.write(buf, 0, r);
            total += r;
        }
        return total;
    }

    private static byte[] getRawBytes(String text) {
        try {
            return text.getBytes(ENC_UTF8);
        } catch (UnsupportedEncodingException e) {
            return text.getBytes();
        }
    }

    private static byte[] getRawBytes(File file) throws IOException {
        FileInputStream fis = null;
        ByteArrayOutputStream bos = new ByteArrayOutputStream();
        ;
        try {
            fis = new FileInputStream(file);
            copy(fis, bos);
        } finally {
            bos.close();
            if (fis != null) {
                fis.close();
            }
        }
        return bos.toByteArray();
    }

    private static String getString(byte[] data) {
        try {
            return new String(data, ENC_UTF8);
        } catch (UnsupportedEncodingException e) {
            return new String(data);
        }
    }

    public static String md5(File file) throws IOException {
        return md5(getRawBytes(file));
    }

    public static String md5(byte[] data) {
        return new String(encodeHex(md5Bytes(data)));
    }

    public static String md5(String text) {
        return new String(encodeHex(md5Bytes(getRawBytes(text))));
    }

    public static byte[] md5Bytes(byte[] data) {
        return getDigest(MD5).digest(data);
    }

    public static String sha1(File file) throws IOException {
        return sha1(getRawBytes(file));
    }

    public static String sha1(byte[] data) {
        return new String(encodeHex(sha1Bytes(data)));
    }

    public static String sha1(String text) {
        return new String(encodeHex(sha1Bytes(getRawBytes(text))));
    }

    public static byte[] sha1Bytes(byte[] data) {
        return getDigest(SHA_1).digest(data);
    }

    public static String sha256(File file) throws IOException {
        return sha256(getRawBytes(file));
    }

    public static String sha256(byte[] data) {
        return new String(encodeHex(sha256Bytes(data)));
    }

    public static String sha256(String text) {
        return new String(encodeHex(sha256Bytes(getRawBytes(text))));
    }

    public static byte[] sha256Bytes(byte[] data) {
        return getDigest(SHA_256).digest(data);
    }

    private static MessageDigest getDigest(String algorithm) {
        try {
            return MessageDigest.getInstance(algorithm);
        } catch (NoSuchAlgorithmException e) {
            throw new IllegalArgumentException(e);
        }
    }

    private static char[] encodeHex(byte[] data) {
        return encodeHex(data, true);
    }

    private static char[] encodeHex(byte[] data, boolean toLowerCase) {
        return encodeHex(data, toLowerCase ? DIGITS_LOWER : DIGITS_UPPER);
    }

    private static char[] encodeHex(byte[] data, char[] toDigits) {
        int l = data.length;
        char[] out = new char[l << 1];
        for (int i = 0, j = 0; i < l; i++) {
            out[j++] = toDigits[(0xF0 & data[i]) >>> 4];
            out[j++] = toDigits[0x0F & data[i]];
        }
        return out;
    }

}
