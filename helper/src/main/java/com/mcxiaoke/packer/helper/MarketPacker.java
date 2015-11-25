package com.mcxiaoke.packer.helper;

import java.io.File;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;

/**
 * User: mcxiaoke
 * Date: 15/11/25
 * Time: 15:03
 */
public final class MarketPacker {

    public static String getMarket(final Object context) {
        try {
            final String sourceDir = getSourceDir(context);
            return PackerNg.readMarket(new File(sourceDir));
        } catch (Exception e) {
            return null;
        }
    }

    private static String getSourceDir(final Object context)
            throws ClassNotFoundException,
            InvocationTargetException,
            IllegalAccessException,
            NoSuchFieldException,
            NoSuchMethodException {
        final Class<?> contextClass = Class.forName("android.content.Context");
        final Class<?> applicationInfoClass = Class.forName("android.content.pm.ApplicationInfo");
        final Method getApplicationInfoMethod = contextClass.getMethod("getApplicationInfo");
        final Object appInfo = getApplicationInfoMethod.invoke(context);
        final Field sourceDirField = applicationInfoClass.getField("sourceDir");
        return (String) sourceDirField.get(appInfo);
    }
}
