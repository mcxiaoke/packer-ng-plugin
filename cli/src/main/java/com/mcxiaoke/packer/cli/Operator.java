package com.mcxiaoke.packer.cli;

import com.android.apksig.ApkVerifier;
import com.android.apksig.ApkVerifier.Builder;
import com.android.apksig.ApkVerifier.Result;
import com.android.apksig.apk.ApkFormatException;
import com.mcxiaoke.packer.common.PackerParser;

import java.io.File;
import java.io.IOException;
import java.security.NoSuchAlgorithmException;

/**
 * User: mcxiaoke
 * Date: 2017/5/26
 * Time: 16:21
 */
public class Operator {

    public static void writeChannel(File apkFile, String channel) throws IOException {
        PackerParser.create(apkFile).writeChannel(channel);
    }

    public static String readChannel(File apkFile) throws IOException {
        return PackerParser.create(apkFile).readChannel();
    }

    public static boolean verifyChannel(File apkFile, String channel) throws IOException {
        return verifyApk(apkFile) && (channel.equals(readChannel(apkFile)));
    }

    public static boolean verifyApk(File apkFile) throws IOException {
        ApkVerifier verifier = new Builder(apkFile).build();
        try {
            Result result = verifier.verify();
            return result.isVerified()
                    && result.isVerifiedUsingV1Scheme()
                    && result.isVerifiedUsingV2Scheme()
                    && !result.containsErrors();
        } catch (ApkFormatException e) {
            throw new IOException(e);
        } catch (NoSuchAlgorithmException e) {
            throw new IOException(e);
        }

    }

}
