package com.mcxiaoke.packer.common;

import java.io.File;
import java.io.IOException;

/**
 * User: mcxiaoke
 * Date: 2017/5/17
 * Time: 15:39
 */
public class CPacker {


    public static CPacker of(File apkFile) {
        return new CPacker(apkFile, PLUGIN_CHANNEL_KEY, PLUGIN_BLOCK_ID);
    }

    // channel info key
    public static final String PLUGIN_CHANNEL_KEY = "zKey"; // 0x7a4b6579
    // channel extra key
    public static final String PLUGIN_EXTRA_KEY = "zExt"; // 0x7a457874
    // plugin block id
    public static final int PLUGIN_BLOCK_ID = 0x7a786b21; // "zxk!"


    private File apkFile;
    private String key;
    private int blockId;

    CPacker(final File apkFile,
            final String key,
            final int blockId) {
        this.apkFile = apkFile;
        this.key = key;
        this.blockId = blockId;
    }

    public String readChannel() throws IOException {
        return CPayload.readValue(apkFile, key, blockId);
    }

    public void writeChannel(final String channel) throws IOException {
        CPayload.writeValue(apkFile, key, channel, blockId);
    }


}
