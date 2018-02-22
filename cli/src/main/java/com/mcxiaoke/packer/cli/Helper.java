package com.mcxiaoke.packer.cli;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.FileOutputStream;
import java.io.FilenameFilter;
import java.io.IOException;
import java.io.InputStreamReader;
import java.nio.channels.FileChannel;
import java.nio.charset.StandardCharsets;
import java.util.LinkedHashMap;
import java.util.Map;
import java.util.regex.Pattern;

/**
 * User: mcxiaoke
 * Date: 2017/5/31
 * Time: 16:52
 */

public class Helper {

    public static Map<String, String> readChannels(String value) throws IOException {
        if (value.startsWith("@")) {
            return parseChannels(new File(value.substring(1)));
        } else {
            return parseChannels(value);
        }
    }

    public static Map<String, String> parseChannels(final File file) throws IOException {
        final Map<String, String> channels = new LinkedHashMap<>();
        InputStreamReader fr=new InputStreamReader(new FileInputStream(file),"UTF-8");
        BufferedReader br = new BufferedReader(fr);
        String line;
        while ((line = br.readLine()) != null) {
            String parts[] = line.split("#");
            if (parts.length > 0) {
                final String ch = escape(parts[0].trim());
                String name = null;
                if (parts.length > 1) {
                    name = parts[1].trim();
                }
                if (name == null || name.length() == 0) {
                    name = ch;
                }
                if (ch.length() > 0) {
                    channels.put(ch, name);
                }
            }
        }
        br.close();
        fr.close();
        return channels;
    }

    public static Map<String, String> parseChannels(String text) {
        String[] lines = text.split(",");
        Map<String, String> channels = new LinkedHashMap<>();
        for (String line : lines) {
            String parts[] = line.split("#");
            if (parts.length > 0) {
                final String ch = escape(parts[0].trim());
                String name = null;
                if (parts.length > 1) {
                    name = parts[1].trim();
                }
                if (name == null || name.length() == 0) {
                    name = ch;
                }
                if (ch.length() > 0) {
                    channels.put(ch, name);
                }
            }
        }
        return channels;
    }

    public static String escape(String key) {
        // filter invalid chars for filename
        Pattern p = Pattern.compile("[\\\\/:*?\"'<>|]");
        return p.matcher(key).replaceAll("_");
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

    public static void deleteAPKs(File dir) {
        FilenameFilter filter = new FilenameFilter() {
            @Override
            public boolean accept(final File dir, final String name) {
                return name.toLowerCase().endsWith(".apk");
            }
        };
        File[] files = dir.listFiles(filter);
        if (files == null || files.length == 0) {
            return;
        }
        for (File file : files) {
            file.delete();
        }
    }

    public static String getExtName(final String fileName) {
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

    public static void printUsage() {
        try {
            BufferedReader in = new BufferedReader(new InputStreamReader(
                    Main.class.getResourceAsStream("help.txt"),
                    StandardCharsets.UTF_8));
            String line;
            while ((line = in.readLine()) != null) {
                System.out.println(line);
            }
        } catch (IOException e) {
            throw new RuntimeException("Failed to read help resource");
        }
    }


}
