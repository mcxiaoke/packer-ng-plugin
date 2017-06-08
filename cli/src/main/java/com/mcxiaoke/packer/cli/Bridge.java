package com.mcxiaoke.packer.cli;

import com.android.apksig.ApkVerifier;
import com.android.apksig.ApkVerifier.Builder;
import com.android.apksig.ApkVerifier.Result;
import com.android.apksig.apk.ApkFormatException;
import com.mcxiaoke.packer.common.PackerCommon;

import java.io.File;
import java.io.IOException;
import java.security.NoSuchAlgorithmException;

/**
 * User: mcxiaoke
 * Date: 2017/5/26
 * Time: 16:21
 */
public class Bridge {

    public static void writeChannel(File file, String channel) throws IOException {
        PackerCommon.writeChannel(file, channel);
    }

    public static String readChannel(File file) throws IOException {
        return PackerCommon.readChannel(file);
    }

    public static boolean verifyChannel(File file, String channel) throws IOException {
        return verifyApk(file) && (channel.equals(readChannel(file)));
    }

    public static boolean verifyApk(File file) throws IOException {
        ApkVerifier verifier = new Builder(file).build();
        try {
            Result result = verifier.verify();
            return result.isVerified()
                    && result.isVerifiedUsingV1Scheme()
                    && result.isVerifiedUsingV2Scheme();
        } catch (ApkFormatException e) {
            throw new IOException(e);
        } catch (NoSuchAlgorithmException e) {
            throw new IOException(e);
        }

    }

}
