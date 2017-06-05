package com.mcxiaoke.packer.common;

import java.io.File;
import java.io.IOException;

/**
 * User: mcxiaoke
 * Date: 2017/5/17
 * Time: 15:39
 */
public class Parser {


    public static Parser create(File apkFile) {
        return new Parser(apkFile);
    }

    public static Parser create(File apkFile, String channelKey) {
        return new Parser(apkFile, channelKey);
    }

    public static Parser create(File apkFile, String channelKey, int channelBlockId) {
        return new Parser(apkFile, channelKey, channelBlockId);
    }

    // channel info key
    public static final String DEFAULT_CHANNEL_KEY = "0x4d6975";
    // channel info id
    public static final int DEFAULT_CHANNEL_BLOCK_ID = 0x717a786b;


    private File apkFile;
    private String channelKey;
    private int channelBlockId;

    Parser(final File apkFile) {
        this(apkFile, DEFAULT_CHANNEL_KEY, DEFAULT_CHANNEL_BLOCK_ID);
    }

    Parser(final File apkFile, final String channelKey) {
        this(apkFile, channelKey, DEFAULT_CHANNEL_BLOCK_ID);
    }

    Parser(final File apkFile,
           final String channelKey,
           final int channelBlockId) {
        this.apkFile = apkFile;
        this.channelKey = channelKey;
        this.channelBlockId = channelBlockId;
    }

    public String readChannel() throws IOException {
        return Payload.readChannel(apkFile, channelKey, channelBlockId);
    }

    public void writeChannel(final String channel) throws IOException {
        Payload.writeChannel(apkFile, channel, channelKey, channelBlockId);
    }


}
