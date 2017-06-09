package com.mcxiaoke.packer.common;

import java.io.IOException;
import java.io.InputStream;
import java.nio.ByteBuffer;

/**
 * https://store.fmi.uni-sofia.bg/fmi/logic/vboutchkova/sources/KMPMatch.java
 * User: mcxiaoke
 * Date: 2017/6/9
 * Time: 12:21
 */

class KMPMatch {

    private byte[] pattern;
    private int[] failure;

    public KMPMatch(byte[] pattern) {
        this.pattern = pattern;
        computeFailure();
    }

    public int find(InputStream is) throws IOException {
        int i = 0;
        int j = 0;
        int b;
        while ((b = is.read()) != -1) {
            i++;
            while (j > 0 && pattern[j] != b) {
                j = failure[j - 1];
            }
            if (pattern[j] == b) {
                j++;
            }
            if (j == pattern.length) {
                return i;
            }
        }
        return -1;
    }

    public int find(ByteBuffer buf) {
        int j = 0;
        int p = buf.position();
        while (buf.hasRemaining()) {
            byte b = buf.get();
            while (j > 0 && pattern[j] != b) {
                j = failure[j - 1];
            }
            if (pattern[j] == b) {
                j++;
            }
            if (j == pattern.length) {
                int q = buf.position() - p;
                return q - pattern.length + 1;
            }
        }
        return -1;
    }

    public int find(byte[] data) {
        int j = 0;
        if (data.length == 0) return -1;
        if (data.length < pattern.length) return -1;

        for (int i = 0; i < data.length; i++) {
            while (j > 0 && pattern[j] != data[i]) {
                j = failure[j - 1];
            }
            if (pattern[j] == data[i]) {
                j++;
            }
            if (j == pattern.length) {
                return i - pattern.length + 1;
            }
        }
        return -1;
    }

    private void computeFailure() {
        failure = new int[pattern.length];
        int j = 0;
        for (int i = 1; i < pattern.length; i++) {
            while (j > 0 && pattern[j] != pattern[i]) {
                j = failure[j - 1];
            }
            if (pattern[j] == pattern[i]) {
                j++;
            }
            failure[i] = j;
        }
    }

}
