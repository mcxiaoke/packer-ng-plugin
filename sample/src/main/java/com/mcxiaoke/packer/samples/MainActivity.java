package com.mcxiaoke.packer.samples;

import android.app.Activity;
import android.os.Bundle;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.ViewGroup.LayoutParams;
import android.widget.TextView;
import com.mcxiaoke.packer.helper.PackerNg;


public class MainActivity extends Activity {
    private static final String TAG = MainActivity.class.getSimpleName();

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
    }

}
