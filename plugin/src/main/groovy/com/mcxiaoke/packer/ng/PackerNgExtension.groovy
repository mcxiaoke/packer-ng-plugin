package com.mcxiaoke.packer.ng

import com.android.build.gradle.internal.dsl.ProductFlavor
import org.gradle.api.Project

// Android Packer Plugin Extension
class PackerNgExtension {
    static
    final String DEFAULT_NAME_TEMPLATE = '${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}'

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

    String market

    Map<String, String> flavorMarket = new HashMap<>()

    List<String> markerts;

    Project project

    PackerNgExtension(Project project) {
        this.project = project
        archiveOutput = new File(project.rootProject.buildDir, "archives")
        tempOutput = new File(project.rootProject.buildDir, "temp")
        archiveNameFormat = DEFAULT_NAME_TEMPLATE
        checkSigningConfig = false
        checkZipAlign = false
        market = new File(project.rootProject.buildDir, "channel.txt").absolutePath
    }

    public void market(String flavorName, String marketFile) {
        project.logger.debug("market = ${marketFile},flavor = ${flavorName}")
        flavorMarket.put(flavorName, marketFile)
    }

    @Override
    protected PackerNgExtension clone() throws CloneNotSupportedException {
        PackerNgExtension packerNgExtension = new PackerNgExtension(project)
        packerNgExtension.flavorMarket = this.flavorMarket;
        packerNgExtension.market = this.market;
        packerNgExtension.archiveOutput = this.archiveOutput;
        packerNgExtension.tempOutput = this.tempOutput;
        packerNgExtension.checkSigningConfig = this.checkSigningConfig;
        packerNgExtension.checkZipAlign = this.checkZipAlign;
        packerNgExtension.archiveNameFormat = this.archiveNameFormat;
        return packerNgExtension
    }


}
