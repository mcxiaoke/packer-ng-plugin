package com.mcxiaoke.packer.cli;

import com.mcxiaoke.packer.cli.Options.OptionsException;

import java.io.File;
import java.io.IOException;
import java.util.Arrays;
import java.util.Collection;
import java.util.List;
import java.util.Locale;

/**
 * User: mcxiaoke
 * Date: 2017/5/26
 * Time: 15:56
 */
public class Main {

    public static final String OUTPUT = "output";

    public static void main(String[] args) {
        if ((args.length == 0)
                || ("--help".equals(args[0]))
                || ("-h".equals(args[0]))
                || "-v".equals(args[0])
                || "--version".equals(args[0])) {
            printUsage();
            return;
        }
        final String cmd = args[0];
        final String[] params = Arrays.copyOfRange(args, 1, args.length);
        try {
            if ("generate".equals(cmd)) {
                generate(params);
            } else if ("verify".equals(cmd)) {
                verify(params);
            } else if ("help".equals(cmd)) {
                printUsage();
            } else if ("version".equals(cmd)) {
                printUsage();
            } else {
                System.err.println(
                        "Unsupported command: " + cmd);
                printUsage();
            }
        } catch (Exception e) {
            System.err.println("Error: " + e.getMessage());
            System.exit(1);
        }
    }

    public static void printUsage() {
        Helper.printUsage();
    }

    private static void generate(String[] params) throws Exception {
        if (params.length == 0) {
            printUsage();
            return;
        }
        System.out.println("========== APK Packer ==========");
        // --channels=a,b,c, -c (list mode)
        // --channels=@list.txt -c (file mode)
        Collection<String> channels = null;
        // --input, -i (input apk file)
        File apkFile = null;
        // --output, -o (output directory)
        File outputDir = null;
        Options optionsParser = new Options(params);
        String name;
        String form = null;
        while ((name = optionsParser.nextOption()) != null) {
            form = optionsParser.getOptionOriginalForm();
            if (("help".equals(name)) || ("h".equals(name))) {
                printUsage();
                return;
            } else if ("channels".equals(name)
                    || "c".equals(name)) {
                String value = optionsParser.getRequiredValue("Channels file(@) or list(,).");
                if (value.startsWith("@")) {
                    channels = Helper.parseChannels(new File(value.substring(1)));
                } else {
                    channels = Helper.parseChannels(value);
                }
            } else if ("input".equals(name)
                    || "i".equals(name)) {
                String value = optionsParser.getRequiredValue("Input APK file");
                apkFile = new File(value);
            } else if ("output".equals(name)
                    || "o".equals(name)) {
                String value = optionsParser.getRequiredValue("Output Directory");
                outputDir = new File(value);
            } else {
                System.err.println(
                        "Unsupported option: " + form);
                printUsage();
            }
        }
        params = optionsParser.getRemainingParams();
        if (apkFile == null) {
            if (params.length < 1) {
                throw new OptionsException("Missing Input APK");
            }
            apkFile = new File(params[0]);
        }
        if (outputDir == null) {
            outputDir = new File(OUTPUT);
        }
        doGenerate(apkFile, channels, outputDir);
    }

    private static void doGenerate(File apkFile, Collection<String> channels, File outputDir)
            throws IOException {
        if (apkFile == null
                || !apkFile.exists()
                || !apkFile.isFile()) {
            throw new IOException("Invalid Input APK: " + apkFile);
        }
        if (!Bridge.verifyApk(apkFile)) {
            throw new IOException("Invalid Signature: " + apkFile);
        }
        if (outputDir.exists()) {
            Helper.deleteAPKs(outputDir);
        } else {
            outputDir.mkdirs();
        }
        System.out.println("Input: " + apkFile.getAbsolutePath());
        System.out.println("Output:" + outputDir.getAbsolutePath());
        System.out.println("Channels:" + Arrays.toString(channels.toArray()));
        final String fileName = apkFile.getName();
        final String baseName = Helper.getBaseName(fileName);
        final String extName = Helper.getExtName(fileName);
        for (final String channel : channels) {
            final String apkName = String.format(Locale.US,
                    "%s-%s.%s", baseName, channel, extName);
            File destFile = new File(outputDir, apkName);
            Helper.copyFile(apkFile, destFile);
            Bridge.writeChannel(destFile, channel);
            if (Bridge.verifyChannel(destFile, channel)) {
                System.out.println("Generating " + apkName);
            } else {
                destFile.delete();
                throw new IOException("Failed to verify APK: " + apkName);
            }
        }
    }

    private static void verify(String[] params) throws Exception {
        if (params.length == 0) {
            printUsage();
            return;
        }
        System.out.println("========== APK Verify ==========");
        if (params.length < 1) {
            throw new IllegalArgumentException("Missing Input APK");
        }
        File apkFile = new File(params[0]);
        doVerify(apkFile);
    }

    private static void doVerify(File apkFile) throws IOException {
        if (apkFile == null
                || !apkFile.exists()
                || !apkFile.isFile()) {
            throw new IOException("Invalid Input APK: " + apkFile);
        }
        final boolean verified = Bridge.verifyApk(apkFile);
        final String channel = Bridge.readChannel(apkFile);
        System.out.println("File: " + apkFile.getName());
        System.out.println("Signed: " + verified);
        System.out.println("Channel: " + channel);
    }


}
