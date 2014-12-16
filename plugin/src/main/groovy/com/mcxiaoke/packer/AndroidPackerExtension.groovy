package com.mcxiaoke.packer

import org.gradle.api.Project

// Android Packer Plugin Extension
class AndroidPackerExtension {

    /**
     *  archive task output dir
     */
    File archiveOutput

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
     *
     * default value: '${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}'
     */
    String archiveNameFormat

    /**
     *  manifest meta-data key list
     */
    List<String> manifestMatcher

    /**
     * support build number auto increment
     *
     * store in file: packer.properties
     */
    boolean buildNumberAuto
    /**
     *  auto build number build type list
     */
    List<String> buildNumberTypeMatcher


    AndroidPackerExtension(Project project) {
        archiveOutput = new File(project.rootProject.buildDir, "archives")
    }


}
