package com.mcxiaoke.packer.helper;

import android.content.Context;
import android.content.SharedPreferences;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.NameNotFoundException;
import com.mcxiaoke.packer.zip.ZipHelper;

import java.io.File;
import java.io.IOException;

/**
 * User: mcxiaoke
 * Date: 15/11/24
 * Time: 14:09
 */
public class PackerNg {
    public static interface InitCallback {
        void onInitComplete(final String market);
    }

    private static final String TAG = PackerNg.class.getSimpleName();
    private static final String DEFAULT_MARKET = "DEFAULT";

    private Context mContext;
    private SharedPreferences mPreferences;
    private volatile String mMarket;
    private boolean mIgnoreNew;
    private String mVersionName;
    private int mVersionCode;

    public PackerNg(final Context context) {
        mContext = context;
        mPreferences = context.getSharedPreferences("packer-ng", Context.MODE_PRIVATE);
        mIgnoreNew = false;
        setup(context);
    }

    private void setup(final Context context) {
        try {
            final PackageManager pm = context.getPackageManager();
            final PackageInfo info = pm.getPackageInfo(context.getPackageName(), 0);
            mVersionName = info.versionName;
            mVersionCode = info.versionCode;
        } catch (NameNotFoundException ignored) {
        }
    }

    public void init() {
        loadMarket();
    }

    public void init(final InitCallback callback) {
        final Runnable runnable = new Runnable() {
            @Override
            public void run() {
                loadMarket();
                if (callback != null) {
                    callback.onInitComplete(mMarket);
                }
            }
        };
        new Thread(runnable).start();
    }

    public void test(int times) {
        long start = System.nanoTime();
        for (int i = 0; i < times; ++i) {
            loadApkMarket();
        }
        long end = System.nanoTime();
        System.out.println(TAG + " run " + times + " using " + (end - start) / 1000 + "ms");
    }

    public String getMarket() {
        if (mMarket == null) {
            loadMarket();
        }
        return mMarket;
    }

    private synchronized void loadMarket() {
        String market = loadSpMarket();
        if (market == null) {
            market = loadApkMarket();
            if (market == null) {
                market = DEFAULT_MARKET;
                System.err.println("Warning: market not set, using default " + market);
            }
            saveSpMarket(market);
        }
        mMarket = market;
    }

    private String getSpMarketKey() {
        return mIgnoreNew ? ("market") : ("market_" + mVersionCode);
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
        } catch (IOException ignored) {
            return null;
        }
    }
}
