package com.mcxiaoke.packer.ng

class GradleExtension {
    File archiveOutput
    String archiveNameFormat
    List<String> channelList;
    File channelFile;

    @Override
    String toString() {
        return "{" +
                "archiveOutput=" + archiveOutput +
                "\narchiveNameFormat='" + archiveNameFormat + '\'' +
                "\nchannelList=" + channelList +
                "\nchannelFile=" + channelFile +
                '}';
    }
}
