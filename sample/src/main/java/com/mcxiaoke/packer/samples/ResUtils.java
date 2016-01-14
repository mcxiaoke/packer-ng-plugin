package com.mcxiaoke.packer.samples;

import android.content.Context;
import com.mcxiaoke.packer.helper.PackerNg;

/**
 * User: mcxiaoke
 * Date: 16/1/13
 * Time: 15:11
 */
public class ResUtils {


    // for icon R.drawable.ic_search for market Google
    // you should name it ic_search_Google.png
    public static int getMarketDrawableId(Context context, String resName) {
        return getDrawableResId(context, resName + "_" + PackerNg.getMarket(context).toLowerCase());
    }

    public static int getMarketLayoutId(Context context, String resName) {
        return getLayoutResId(context, resName + "_" + PackerNg.getMarket(context).toLowerCase());
    }

    public static int getMarketStringId(Context context, String resName) {
        return getStringResId(context, resName + "_" + PackerNg.getMarket(context).toLowerCase());
    }

    public static int getMarketResourceId(Context context, String resName) {
        return getResourceId(context, resName + "_" + PackerNg.getMarket(context).toLowerCase());
    }

    public static int getDrawableResId(Context context, String resName) {
        return getResId(context, "drawable", resName);
    }

    public static int getMenuResId(Context context, String resName) {
        return getResId(context, "layout", resName);
    }

    public static int getLayoutResId(Context context, String resName) {
        return getResId(context, "layout", resName);
    }

    public static int getAnimResId(Context context, String resName) {
        return getResId(context, "anim", resName);
    }

    public static int getAttrResId(Context context, String resName) {
        return getResId(context, "attr", resName);
    }

    public static int getStyleResId(Context context, String resName) {
        return getResId(context, "style", resName);
    }

    public static int getDimenResId(Context context, String resName) {
        return getResId(context, "dimen", resName);
    }

    public static int getColorResId(Context context, String resName) {
        return getResId(context, "color", resName);
    }

    public static int getRawResId(Context context, String resName) {
        return getResId(context, "raw", resName);
    }

    public static int getStringResId(Context context, String resName) {
        return getResId(context, "string", resName);
    }

    public static int getResourceId(Context context, String resName) {
        return getResId(context, "id", resName);
    }

    public static int getResId(Context context, String type, String resName) {
        final String packageName = context.getPackageName();
        return context.getResources().getIdentifier(resName, type, packageName);
    }

}
