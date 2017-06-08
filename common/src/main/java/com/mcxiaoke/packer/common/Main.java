package com.mcxiaoke.packer.common;

import java.io.UnsupportedEncodingException;

/**
 * User: mcxiaoke
 * Date: 2017/6/8
 * Time: 16:21
 */

class Main {
    public static void main(String[] args) throws UnsupportedEncodingException {
        System.out.println("magic string length="
                + PackerCommon.BLOCK_MAGIC.length());
        System.out.println("magic bytes length="
                + PackerCommon.BLOCK_MAGIC.getBytes(PackerCommon.UTF8).length);
        System.out.println("channel key string length="
                + PackerCommon.CHANNEL_KEY.length());
        System.out.println("channel key bytes length="
                + PackerCommon.CHANNEL_KEY.getBytes(PackerCommon.UTF8).length);
    }
}
