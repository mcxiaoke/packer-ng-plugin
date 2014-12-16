package com.mcxiaoke.packer.samples;

import android.annotation.SuppressLint;
import android.app.ActivityManager;
import android.app.ActivityManager.MemoryInfo;
import android.content.Context;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageInfo;
import android.content.pm.PackageManager;
import android.content.pm.PackageManager.NameNotFoundException;
import android.graphics.Point;
import android.net.ConnectivityManager;
import android.net.NetworkInfo;
import android.os.Build;
import android.os.Build.VERSION_CODES;
import android.os.Bundle;
import android.support.v7.app.ActionBarActivity;
import android.util.DisplayMetrics;
import android.view.Display;
import android.view.ViewGroup;
import android.view.ViewGroup.LayoutParams;
import android.widget.TextView;
import butterknife.ButterKnife;
import butterknife.InjectView;
import com.mcxiaoke.next.utils.AndroidUtils;
import com.mcxiaoke.next.utils.LogUtils;
import com.mcxiaoke.next.utils.StringUtils;
import com.mcxiaoke.packer.sample.BuildConfig;
import com.mcxiaoke.packer.sample.R;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.lang.reflect.Modifier;
import java.util.Set;


public class MainActivity extends ActionBarActivity {
    private static final String TAG = MainActivity.class.getSimpleName();

    @InjectView(R.id.container)
    ViewGroup mContainer;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.act_main);
        ButterKnife.inject(this);
        addBuildConfigSection();
        addMetaDataSection();
        addAppInfoSection();
        addNetworkInfoSection();
        addDeviceInfoSection();
        addBuildPropsSection();

    }

    private void addAppInfoSection() {
        try {
            final PackageInfo pi = getPackageManager().getPackageInfo(getPackageName(), 0);
            final ApplicationInfo info = pi.applicationInfo;
            StringBuilder builder = new StringBuilder();
            builder.append("[AppInfo]\n");
            builder.append("Name: ").append(getString(info.labelRes)).append("\n");
            builder.append("Package: ").append(BuildConfig.APPLICATION_ID).append("\n");
            builder.append("VersionCode: ").append(BuildConfig.VERSION_CODE).append("\n");
            builder.append("VersionName: ").append(BuildConfig.VERSION_NAME).append("\n");
            builder.append("ProcessName: ").append(info.processName).append("\n");
            builder.append("SourceDir: ").append(info.sourceDir).append("\n");
            builder.append("DataDir: ").append(info.dataDir).append("\n");
            builder.append("Signature:\n");
            builder.append(AndroidUtils.getSignatureInfo(this)).append("\n");
            builder.append("\n");
            addSection(builder.toString());
        } catch (Exception e) {
        }


    }

    private void addMetaDataSection() {
        final PackageManager pm = getPackageManager();
        final String packageName = getPackageName();
        try {
            final ApplicationInfo info = pm.getApplicationInfo(packageName,
                    PackageManager.GET_SIGNATURES | PackageManager.GET_META_DATA);
            final Bundle bundle = info.metaData;
            final StringBuilder builder = new StringBuilder();
            builder.append("[MetaData]\n");
            if (bundle != null) {
                final Set<String> keySet = bundle.keySet();
                for (final String key : keySet) {
                    builder.append(key).append("=").append(bundle.get(key)).append("\n");
                }
            }
            addSection(builder.toString());
        } catch (NameNotFoundException e) {
            e.printStackTrace();
        }
    }

    private void addNetworkInfoSection() {
        StringBuilder builder = new StringBuilder();
        builder.append("[Network]\n");
        ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
        NetworkInfo info = cm.getActiveNetworkInfo();
        if (info != null) {
            builder.append(info);
        }
        builder.append("\n\n");
        addSection(builder.toString());
    }

    @SuppressLint("NewApi")
    private void addDeviceInfoSection() {
        StringBuilder builder = new StringBuilder();
        builder.append("[Device]\n");

        ActivityManager am = (ActivityManager) getSystemService(Context.ACTIVITY_SERVICE);
        final MemoryInfo memoryInfo = new MemoryInfo();
        am.getMemoryInfo(memoryInfo);
        if (AndroidUtils.hasJellyBean()) {
            builder.append("Mem Total: ").append(StringUtils.getHumanReadableByteCount(memoryInfo.totalMem)).append("\n");
        }
        builder.append("Mem Free: ").append(StringUtils.getHumanReadableByteCount(memoryInfo.availMem)).append("\n");
        builder.append("Mem Heap: ").append(am.getMemoryClass()).append("M\n");
        builder.append("Mem Low: ").append(memoryInfo.lowMemory).append("\n");
        Display display = getWindowManager().getDefaultDisplay();
        DisplayMetrics dm = new DisplayMetrics();
        //DisplayMetrics dm = getResources().getDisplayMetrics();
        display.getMetrics(dm);

        int statusBarHeightDp = ViewUtils.getStatusBarHeightInDp(this);
        int systemBarHeightDp = ViewUtils.getSystemBarHeightInDp(this);
        int statusBarHeight = ViewUtils.getStatusBarHeight(this);
        int systemBarHeight = ViewUtils.getSystemBarHeight(this);
        Point point = getScreenRawSize(display);
        builder.append("statusBarHeightDp: ").append(statusBarHeightDp).append("\n");
        builder.append("systemBarHeightDp: ").append(systemBarHeightDp).append("\n");
        builder.append("statusBarHeightPx: ").append(statusBarHeight).append("\n");
        builder.append("systemBarHeightPx: ").append(systemBarHeight).append("\n");
        builder.append("screenWidth: ").append(point.x).append("\n");
        builder.append("screenHeight: ").append(point.y).append("\n");
        builder.append("WindowWidth: ").append(dm.widthPixels).append("\n");
        builder.append("WindowHeight: ").append(dm.heightPixels).append("\n");
        builder.append(toString2(dm));
        builder.append("\n");
        addSection(builder.toString());
    }

    private void addBuildConfigSection() {
        StringBuilder builder = new StringBuilder();
        builder.append("[BuildConfig]\n");
        builder.append(toString(BuildConfig.class));
        builder.append("\n");
        addSection(builder.toString());
    }

    private void addBuildPropsSection() {
        StringBuilder builder = new StringBuilder();
        builder.append("[System]\n");
        builder.append(toString(Build.VERSION.class));
        builder.append(toString(Build.class));
        builder.append("\n");
        addSection(builder.toString());
    }

    private LayoutParams TEXT_VIEW_LP = new LayoutParams(LayoutParams.MATCH_PARENT,
            LayoutParams.WRAP_CONTENT);

    private void addSection(CharSequence text) {
        TextView tv = new TextView(this);
        tv.setLayoutParams(TEXT_VIEW_LP);
        tv.setText(text);
        tv.setTextIsSelectable(true);
        mContainer.addView(tv);
    }


    @SuppressLint("NewApi")
    public static Point getScreenRawSize(Display display) {
        if (Build.VERSION.SDK_INT >= VERSION_CODES.JELLY_BEAN_MR1) {
            Point outPoint = new Point();
            DisplayMetrics metrics = new DisplayMetrics();
            display.getRealMetrics(metrics);
            outPoint.x = metrics.widthPixels;
            outPoint.y = metrics.heightPixels;
            return outPoint;
        } else {
            Point outPoint = new Point();
            Method mGetRawH;
            try {
                mGetRawH = Display.class.getMethod("getRawHeight");
                Method mGetRawW = Display.class.getMethod("getRawWidth");
                outPoint.x = (Integer) mGetRawW.invoke(display);
                outPoint.y = (Integer) mGetRawH.invoke(display);
                return outPoint;
            } catch (Throwable e) {
                return new Point(0, 0);
            }
        }
    }

    public static String toString(Class<?> clazz) {
        StringBuilder builder = new StringBuilder();
        final String newLine = System.getProperty("line.separator");
        Field[] fields = clazz.getDeclaredFields();
        for (Field field : fields) {
            field.setAccessible(true);
            String fieldName = field.getName();
            if (Modifier.isStatic(field.getModifiers())) {
                LogUtils.v(TAG, "filed:" + fieldName);
                try {
                    Object fieldValue = field.get(null);
                    builder.append(fieldName).append(": ").append(fieldValue).append(newLine);
                } catch (Exception ex) {
                    ex.printStackTrace();
                }
            }
        }
        return builder.toString();
    }

    public static String toString2(Object object) {
        Class<?> clazz = object.getClass();
        StringBuilder builder = new StringBuilder();
        final String newLine = System.getProperty("line.separator");
        Field[] fields = clazz.getDeclaredFields();
        for (Field field : fields) {
            field.setAccessible(true);
            String fieldName = field.getName();
            if (!Modifier.isStatic(field.getModifiers())) {
                LogUtils.v(TAG, "filed:" + fieldName);
                try {
                    Object fieldValue = field.get(object);
                    builder.append(fieldName).append(": ").append(fieldValue).append(newLine);
                } catch (Exception ex) {
                    ex.printStackTrace();
                }
            }
        }
        return builder.toString();
    }

}
