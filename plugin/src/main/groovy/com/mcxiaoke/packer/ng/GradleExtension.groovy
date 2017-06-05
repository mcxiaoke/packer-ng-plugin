package com.mcxiaoke.packer.ng

class GradleExtension {
    File archiveOutput
    String archiveNameFormat
    List<String> channelList;
    File channelFile;
    Map<String, File> channelMap;

    @Override
    String toString() {
        return "{" +
                "archiveOutput=" + archiveOutput +
                "\narchiveNameFormat='" + archiveNameFormat + '\'' +
                "\nchannelList=" + channelList +
                "\nchannelFile=" + channelFile +
                "\nchannelMap=" + channelMap +
                '}';
    }
}
