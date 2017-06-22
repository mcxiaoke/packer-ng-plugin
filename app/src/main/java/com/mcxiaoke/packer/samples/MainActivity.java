package com.mcxiaoke.packer.samples;

import android.app.Activity;
import android.content.pm.ApplicationInfo;
import android.content.pm.PackageManager;
import android.os.Bundle;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.ViewGroup.LayoutParams;
import android.widget.TextView;
import com.mcxiaoke.packer.helper.PackerNg;

import java.io.File;
import java.util.List;


public class MainActivity extends Activity {
    private static final String TAG = "PackerNg";

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        TextView v = new TextView(this);
        LayoutParams p = new LayoutParams(-1, -1);
        setContentView(v, p);
        v.setTextSize(TypedValue.COMPLEX_UNIT_SP, 40);
        v.setGravity(Gravity.CENTER);
        v.setPadding(40, 40, 40, 40);
        v.setText(PackerNg.getChannel(this));

        PackageManager pm = getPackageManager();
        List<ApplicationInfo> apps = pm.getInstalledApplications(PackageManager.GET_META_DATA);
        for (ApplicationInfo app : apps) {
            if (app.packageName.startsWith("com.douban.")) {
                Log.d("TAG", "app=" + app.packageName + ", channel="
                        + PackerNg.getChannel(new File(app.sourceDir)));
            }
        }

    }

}
