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
    public static int getMarketDrawableId(Context context, String iconName) {
        String market = PackerNg.getMarket(context);
        return getDrawableResourceId(context, iconName + "_" + market);
    }

    public static int getDrawableResourceId(Context context, String iconName) {
        final String packageName = context.getPackageName();
        return context.getResources().getIdentifier(iconName, "drawable", packageName);
    }

}
