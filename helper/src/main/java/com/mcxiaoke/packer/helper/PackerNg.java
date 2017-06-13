package com.mcxiaoke.packer.helper;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import com.mcxiaoke.packer.common.PackerCommon;

import java.io.File;
import java.io.IOException;

/**
 * User: mcxiaoke
 * Date: 15/11/23
 * Time: 13:12
 */
public final class PackerNg {
    private static final String TAG = "PackerNg";
    private static final String EMPTY_STRING = "";
    private static String sCachedChannel;

    public static String getChannel(final File file) {
        try {
            return PackerCommon.readChannel(file);
        } catch (Exception e) {
            return EMPTY_STRING;
        }
    }

    public static String getChannel(final Context context) {
        try {
            return getChannelOrThrow(context);
        } catch (Exception e) {
            return EMPTY_STRING;
        }
    }

    public static synchronized String getChannelOrThrow(final Context context)
            throws IOException {
        final ApplicationInfo info = context.getApplicationInfo();
        return PackerCommon.readChannel(new File(info.sourceDir));
    }

}
