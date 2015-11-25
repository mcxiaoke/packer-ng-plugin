package com.mcxiaoke.packer.helper;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.NameNotFoundException;
import android.util.Log;
import com.mcxiaoke.packer.zip.ZipHelper;

import java.io.File;

/**
 * User: mcxiaoke
 * Date: 15/11/24
 * Time: 14:09
 */
public class MarketPacker {

    private static final String TAG = MarketPacker.class.getSimpleName();

    private Context mContext;
    private SharedPreferences mPreferences;
    private boolean mIgnoreNew;
    private int mVersionCode;
    private boolean mDebugMode;

    private static MarketPacker sInstance;

    // using first parsed market, ignore market change in newer version
    public static void setIgnoreNew(final Context context, boolean ignoreNew) {
        getInstance(context).setIgnoreNew(ignoreNew);
    }

    // enable debug mode, print logs
    public static void setDebug(final Context context, boolean debug) {
        getInstance(context).setDebugMode(debug);
    }

    // get current market
    public static String getMarket(final Context context) {
        return getInstance(context).loadMarket();
    }

    private static synchronized MarketPacker getInstance(final Context context) {
        if (sInstance == null) {
            sInstance = new MarketPacker(context);
        }
        return sInstance;
    }

    private MarketPacker(final Context context) {
        mContext = context;
        mPreferences = context.getSharedPreferences("packer-ng", Context.MODE_PRIVATE);
        mIgnoreNew = false;
        setup(context);
    }

    private void setup(final Context context) {
        try {
            final PackageManager pm = context.getPackageManager();
            final PackageInfo info = pm.getPackageInfo(context.getPackageName(), 0);
            mVersionCode = info.versionCode;
            if (mDebugMode) {
                Log.d(TAG, "setup() versionCode=" + mVersionCode);
            }
        } catch (NameNotFoundException e) {
            if (mDebugMode) {
                e.printStackTrace();
            }
        }
    }

    private void setIgnoreNew(boolean ignoreNew) {
        mIgnoreNew = ignoreNew;
    }

    private void setDebugMode(boolean debugMode) {
        mDebugMode = debugMode;
    }

    private synchronized String loadMarket() {
        String market = loadSpMarket();
        if (market == null) {
            long start = System.nanoTime();
            market = loadApkMarket();
            if (mDebugMode) {
                long duration = (System.nanoTime() - start);
                Log.d(TAG, "loadMarket() from apk, market=" + market + " using " + duration + "ns");
                if (market == null) {
                    Log.w(TAG, "loadMarket()  could not find market from apk file");
                }
            }
            if (market != null) {
                saveSpMarket(market);
            }
        } else {
            if (mDebugMode) {
                Log.d(TAG, "loadMarket() from sp, market=" + market);
            }
        }
        return market;
    }

    private String getSpMarketKey() {
        return mIgnoreNew ? "market" : "market_" + mVersionCode;
    }

    private synchronized void saveSpMarket(final String market) {
        mPreferences.edit().clear().putString(getSpMarketKey(), market).apply();
    }

    private String loadSpMarket() {
        return mPreferences.getString(getSpMarketKey(), null);
    }

    private String loadApkMarket() {
        final ApplicationInfo app = mContext.getApplicationInfo();
        try {
            return ZipHelper.readMarket(new File(app.sourceDir));
        } catch (Exception e) {
            if (mDebugMode) {
                e.printStackTrace();
            }
            return null;
        }
    }
}
