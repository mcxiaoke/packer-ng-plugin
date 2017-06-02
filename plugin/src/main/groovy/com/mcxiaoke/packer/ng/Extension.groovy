package com.mcxiaoke.packer.ng

import org.gradle.api.Project

// Android Packer Plugin Extension
class Extension {
    static final String DEFAULT_NAME_TEMPLATE = '${appPkg}-${channel}-${buildType}-v${versionName}-${versionCode}'

    File archiveOutput

    /**
     * file name template string
     *
     * Available vars:
     * 1. projectName
     * 2. appName
     * 3. appPkg
     * 4. buildType
     * 5. channel
     * 6. versionName
     * 7. versionCode
     * 8. buildTime
     * 9. fileMD5
     * 10. fileSHA1
     *
     * default value: '${appPkg}-${channel}-${buildType}-v${versionName}-${versionCode}'
     */
    String archiveNameFormat

    List<String> channelList;

    File channelFile;

    Extension(Project project) {
        archiveOutput = new File(project.rootProject.buildDir, "archives")
        archiveNameFormat = DEFAULT_NAME_TEMPLATE
        channelList = null
        channelFile = null
    }


}
