package com.mcxiaoke.packer.helper;

import java.io.BufferedReader;
import java.io.DataInput;
import java.io.DataOutput;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FileReader;
import java.io.IOException;
import java.io.RandomAccessFile;
import java.lang.reflect.Field;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.nio.ByteBuffer;
import java.nio.ByteOrder;
import java.nio.MappedByteBuffer;
import java.nio.channels.FileChannel;
import java.nio.channels.FileChannel.MapMode;
import java.util.ArrayList;
import java.util.List;

/**
 * User: mcxiaoke
 * Date: 15/11/23
 * Time: 13:12
 */
public final class PackerNg {
    private static final String TAG = PackerNg.class.getSimpleName();
    private static final String EMPTY_STRING = "";
    private static String sCachedMarket;

    public static String getMarket(final Object context) {
        return getMarket(context, EMPTY_STRING);
    }

    public static synchronized String getMarket(final Object context, final String defaultValue) {
        if (sCachedMarket == null) {
            sCachedMarket = getMarketInternal(context, defaultValue).market;
        }
        return sCachedMarket;
    }

    public static MarketInfo getMarketInfo(final Object context) {
        return getMarketInfo(context, EMPTY_STRING);
    }

    public static synchronized MarketInfo getMarketInfo(final Object context, final String defaultValue) {
        return getMarketInternal(context, defaultValue);
    }

    private static MarketInfo getMarketInternal(final Object context, final String defaultValue) {
        String market;
        Exception error;
        try {
            final String sourceDir = Helper.getSourceDir(context);
            market = Helper.readMarket(new File(sourceDir));
            error = null;
        } catch (Exception e) {
            market = null;
            error = e;
        }
        return new MarketInfo(market == null ? defaultValue : market, error);
    }

    public static final class MarketInfo {
        public final String market;
        public final Exception error;

        public MarketInfo(final String market, final Exception error) {
            this.market = market;
            this.error = error;
        }

        @Override
        public String toString() {
            return "MarketInfo{" +
                    "market='" + market + '\'' +
                    ", error=" + error +
                    '}';
        }
    }

    public static class MarketExistsException extends IOException {
        public MarketExistsException() {
            super();
        }

        public MarketExistsException(final String message) {
            super(message);
        }
    }

    public static class MarketNotFoundException extends IOException {
        public MarketNotFoundException() {
            super();
        }

        public MarketNotFoundException(final String message) {
            super(message);
        }
    }

    public static class Helper {
        static final String UTF_8 = "UTF-8";
        static final int ZIP_COMMENT_MAX_LENGTH = 65535;
        static final int SHORT_LENGTH = 2;
        static final byte[] MAGIC = new byte[]{0x21, 0x5a, 0x58, 0x4b, 0x21}; //!ZXK!

        // for android code
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
            // try ApplicationInfo.sourceDir
            Field sourceDirField = applicationInfoClass.getField("sourceDir");
            String sourceDir = (String) sourceDirField.get(appInfo);
            if (sourceDir == null) {
                // try ApplicationInfo.publicSourceDir
                sourceDirField = applicationInfoClass.getField("publicSourceDir");
                sourceDir = (String) sourceDirField.get(appInfo);
            }
            if (sourceDir == null) {
                // try Context.getPackageCodePath()
                final Method getPackageCodePathMethod = contextClass.getMethod("getPackageCodePath");
                sourceDir = (String) getPackageCodePathMethod.invoke(context);
            }
            return sourceDir;

        }

        private static boolean isMagicMatched(byte[] buffer) {
            if (buffer.length != MAGIC.length) {
                return false;
            }
            for (int i = 0; i < MAGIC.length; ++i) {
                if (buffer[i] != MAGIC[i]) {
                    return false;
                }
            }
            return true;
        }

        private static void writeBytes(byte[] data, DataOutput out) throws IOException {
            out.write(data);
        }

        private static void writeShort(int i, DataOutput out) throws IOException {
            ByteBuffer bb = ByteBuffer.allocate(SHORT_LENGTH).order(ByteOrder.LITTLE_ENDIAN);
            bb.putShort((short) i);
            out.write(bb.array());
        }

        private static short readShort(DataInput input) throws IOException {
            byte[] buf = new byte[SHORT_LENGTH];
            input.readFully(buf);
            ByteBuffer bb = ByteBuffer.wrap(buf).order(ByteOrder.LITTLE_ENDIAN);
            return bb.getShort(0);
        }


        public static void writeZipComment(File file, String comment) throws IOException {
            if (hasZipCommentMagic(file)) {
                throw new MarketExistsException("Zip comment already exists, ignore.");
            }
            // {@see java.util.zip.ZipOutputStream.writeEND}
            byte[] data = comment.getBytes(UTF_8);
            final RandomAccessFile raf = new RandomAccessFile(file, "rw");
            raf.seek(file.length() - SHORT_LENGTH);
            // write zip comment length
            // (content field length + length field length + magic field length)
            writeShort(data.length + SHORT_LENGTH + MAGIC.length, raf);
            // write content
            writeBytes(data, raf);
            // write content length
            writeShort(data.length, raf);
            // write magic bytes
            writeBytes(MAGIC, raf);
            raf.close();
        }

        public static boolean hasZipCommentMagic(File file) throws IOException {
            RandomAccessFile raf = null;
            try {
                raf = new RandomAccessFile(file, "r");
                long index = raf.length();
                byte[] buffer = new byte[MAGIC.length];
                index -= MAGIC.length;
                // read magic bytes
                raf.seek(index);
                raf.readFully(buffer);
                // check magic bytes matched
                return isMagicMatched(buffer);
            } finally {
                if (raf != null) {
                    raf.close();
                }
            }
        }

        public static String readZipComment(File file) throws IOException {
            RandomAccessFile raf = null;
            try {
                raf = new RandomAccessFile(file, "r");
                long index = raf.length();
                byte[] buffer = new byte[MAGIC.length];
                index -= MAGIC.length;
                // read magic bytes
                raf.seek(index);
                raf.readFully(buffer);
                // if magic bytes matched
                if (isMagicMatched(buffer)) {
                    index -= SHORT_LENGTH;
                    raf.seek(index);
                    // read content length field
                    int length = readShort(raf);
                    if (length > 0) {
                        index -= length;
                        raf.seek(index);
                        // read content bytes
                        byte[] bytesComment = new byte[length];
                        raf.readFully(bytesComment);
                        return new String(bytesComment, UTF_8);
                    } else {
                        throw new MarketNotFoundException("Zip comment content not found");
                    }
                } else {
                    throw new MarketNotFoundException("Zip comment magic bytes not found");
                }
            } finally {
                if (raf != null) {
                    raf.close();
                }
            }
        }

        private static String readZipCommentMmp(File file) throws IOException {
            final int mappedSize = 10240;
            final long fz = file.length();
            RandomAccessFile raf = null;
            MappedByteBuffer map = null;
            try {
                raf = new RandomAccessFile(file, "r");
                map = raf.getChannel().map(MapMode.READ_ONLY, fz - mappedSize, mappedSize);
                map.order(ByteOrder.LITTLE_ENDIAN);
                int index = mappedSize;
                byte[] buffer = new byte[MAGIC.length];
                index -= MAGIC.length;
                // read magic bytes
                map.position(index);
                map.get(buffer);
                // if magic bytes matched
                if (isMagicMatched(buffer)) {
                    index -= SHORT_LENGTH;
                    map.position(index);
                    // read content length field
                    int length = map.getShort();
                    if (length > 0) {
                        index -= length;
                        map.position(index);
                        // read content bytes
                        byte[] bytesComment = new byte[length];
                        map.get(bytesComment);
                        return new String(bytesComment, UTF_8);
                    }
                }
            } finally {
                if (map != null) {
                    map.clear();
                }
                if (raf != null) {
                    raf.close();
                }
            }
            return null;
        }


        public static void writeMarket(final File file, final String market) throws IOException {
            writeZipComment(file, market);
        }

        public static String readMarket(final File file) throws IOException {
            return readZipComment(file);
        }

        public static boolean verifyMarket(final File file, final String market) throws IOException {
            return market.equals(readMarket(file));
        }

        public static void println(String msg) {
            System.out.println(msg);
        }

        public static void printErr(String msg) {
            System.err.println(msg);
        }

        public static List<String> parseMarkets(final File file) throws IOException {
            final List<String> markets = new ArrayList<String>();
            FileReader fr = new FileReader(file);
            BufferedReader br = new BufferedReader(fr);
            String line = null;
            int lineNo = 1;
            while ((line = br.readLine()) != null) {
                String parts[] = line.split("#");
                if (parts.length > 0) {
                    final String market = parts[0].trim();
                    if (market.length() > 0) {
                        markets.add(market);
                    }
                }
                ++lineNo;
            }
            br.close();
            fr.close();
            return markets;
        }

        public static void copyFile(File src, File dest) throws IOException {
            if (!dest.exists()) {
                dest.createNewFile();
            }
            FileChannel source = null;
            FileChannel destination = null;
            try {
                source = new FileInputStream(src).getChannel();
                destination = new FileOutputStream(dest).getChannel();
                destination.transferFrom(source, 0, source.size());
            } finally {
                if (source != null) {
                    source.close();
                }
                if (destination != null) {
                    destination.close();
                }
            }
        }

        public static boolean deleteDir(File dir) {
            File[] files = dir.listFiles();
            if (files == null || files.length == 0) {
                return false;
            }
            for (File file : files) {
                if (file.isDirectory()) {
                    deleteDir(file);
                } else {
                    file.delete();
                }
            }
            return true;
        }

        public static String getExtension(final String fileName) {
            int dot = fileName.lastIndexOf(".");
            if (dot > 0) {
                return fileName.substring(dot + 1);
            } else {
                return null;
            }
        }

        public static String getBaseName(final String fileName) {
            int dot = fileName.lastIndexOf(".");
            if (dot > 0) {
                return fileName.substring(0, dot);
            } else {
                return fileName;
            }
        }
    }

    private static final String USAGE_TEXT =
            "Usage: java -jar PackerNg-x.x.x.jar apkFile marketFile [outputDir] ";
    private static final String INTRO_TEXT =
            "\nAttention: if your app using Android gradle plugin 2.2.0 or later, " +
                    "be sure to install one of the generated Apks to device or emulator, " +
                    "to ensure the apk can be installed without errors. " +
                    "More details please go to github " +
                    "https://github.com/mcxiaoke/packer-ng-plugin .\n";

    public static void main(String[] args) {
        if (args.length < 2) {
            Helper.println(USAGE_TEXT);
            Helper.println(INTRO_TEXT);
            System.exit(1);
        }
        File apkFile = new File(args[0]);
        File marketFile = new File(args[1]);
        File outputDir = new File(args.length >= 3 ? args[2] : "apks");
        if (!apkFile.exists()) {
            Helper.printErr("Apk file '" + apkFile.getAbsolutePath() +
                    "' is not exists or not readable.");
            Helper.println(USAGE_TEXT);
            System.exit(1);
            return;
        }
        if (!marketFile.exists()) {
            Helper.printErr("Market file '" + marketFile.getAbsolutePath() +
                    "' is not exists or not readable.");
            Helper.println(USAGE_TEXT);
            System.exit(1);
            return;
        }
        if (!outputDir.exists()) {
            outputDir.mkdirs();
        }
        Helper.println("Apk File: " + apkFile.getAbsolutePath());
        Helper.println("Market File: " + marketFile.getAbsolutePath());
        Helper.println("Output Dir: " + outputDir.getAbsolutePath());
        List<String> markets = null;
        try {
            markets = Helper.parseMarkets(marketFile);
        } catch (IOException e) {
            Helper.printErr("Market file parse failed.");
            System.exit(1);
        }
        if (markets == null || markets.isEmpty()) {
            Helper.printErr("No markets found.");
            System.exit(1);
            return;
        }
        final String baseName = Helper.getBaseName(apkFile.getName());
        final String extName = Helper.getExtension(apkFile.getName());
        int processed = 0;
        try {
            for (final String market : markets) {
                final String apkName = baseName + "-" + market + "." + extName;
                File destFile = new File(outputDir, apkName);
                Helper.copyFile(apkFile, destFile);
                Helper.writeMarket(destFile, market);
                if (Helper.verifyMarket(destFile, market)) {
                    ++processed;
                    Helper.println("Generating apk " + apkName);
                } else {
                    destFile.delete();
                    Helper.printErr("Failed to generate " + apkName);
                }
            }
            Helper.println("[Success] All " + processed
                    + " apks saved to " + outputDir.getAbsolutePath());
            Helper.println(INTRO_TEXT);
        } catch (MarketExistsException ex) {
            Helper.printErr("Market info exists in '" + apkFile
                    + "', please using a clean apk.");
            System.exit(1);
        } catch (IOException ex) {
            Helper.printErr("" + ex);
            System.exit(1);
        }
    }

}
