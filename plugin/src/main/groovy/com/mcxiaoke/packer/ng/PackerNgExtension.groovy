package com.mcxiaoke.packer.ng

import org.gradle.api.Project

// Android Packer Plugin Extension
class PackerNgExtension {
    static final String DEFAULT_NAME_TEMPLATE = '${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}'

    /**
     *  archive task output dir
     */
    File archiveOutput

    File tempOutput

    boolean checkSigningConfig

    boolean checkZipAlign

    /**
     * file name template string
     *
     * Available vars:
     * 1. projectName
     * 2. appName
     * 3. appPkg
     * 4. buildType
     * 5. flavorName
     * 6. versionName
     * 7. versionCode
     * 8. buildTime
     * 9. fileMD5
     * 10. fileSHA1
     *
     * default value: '${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}'
     */
    String archiveNameFormat

    PackerNgExtension(Project project) {
        archiveOutput = new File(project.rootProject.buildDir, "archives")
        tempOutput = new File(project.rootProject.buildDir, "temp")
        archiveNameFormat = DEFAULT_NAME_TEMPLATE
        checkSigningConfig = false
        checkZipAlign = false
    }


}
