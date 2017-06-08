package com.mcxiaoke.packer.helper;

import android.content.Context;
import android.content.pm.ApplicationInfo;
import com.mcxiaoke.packer.common.PackerCommon;

import java.io.File;

/**
 * User: mcxiaoke
 * Date: 15/11/23
 * Time: 13:12
 */
public final class PackerNg {
    private static final String TAG = "PackerNg";
    private static final String EMPTY_STRING = "";
    private static String sCachedChannel;

    public static String getChannel(final Context context) {
        return getChannel(context, EMPTY_STRING);
    }

    public static synchronized String getChannel(final Context context,
                                                 final String defValue) {
        if (sCachedChannel == null) {
            sCachedChannel = getMarketInternal(context, defValue).channel;
        }
        return sCachedChannel;
    }

    public static ChannelInfo getChannelInfo(final Context context) {
        return getChannelInfo(context, EMPTY_STRING);
    }

    public static synchronized ChannelInfo getChannelInfo(final Context context,
                                                          final String defValue) {
        return getMarketInternal(context, defValue);
    }

    private static ChannelInfo getMarketInternal(final Context context,
                                                 final String defValue) {
        String market = null;
        Exception error = null;
        try {
            final ApplicationInfo info = context.getApplicationInfo();
            final File apkFile = new File(info.sourceDir);
            market = PackerCommon.readChannel(apkFile);
        } catch (Exception e) {
            error = e;
        }
        return new ChannelInfo(market == null ? defValue : market, error);
    }

    public static final class ChannelInfo {
        public final String channel;
        public final Exception error;

        public ChannelInfo(final String channel, final Exception error) {
            this.channel = channel;
            this.error = error;
        }

        @Override
        public String toString() {
            return "ChannelInfo{" +
                    "market='" + channel + '\'' +
                    ", error=" + error +
                    '}';
        }
    }
}
