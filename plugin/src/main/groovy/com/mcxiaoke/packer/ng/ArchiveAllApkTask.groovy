package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import com.android.builder.model.SigningConfig
import com.mcxiaoke.packer.helper.PackerNg
import groovy.io.FileType
import groovy.text.SimpleTemplateEngine
import org.gradle.api.DefaultTask
import org.gradle.api.GradleException
import org.gradle.api.InvalidUserDataException
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.TaskAction

import java.text.SimpleDateFormat
import java.util.jar.JarEntry
import java.util.jar.JarFile

/**
 * User: mcxiaoke
 * Date: 15/11/23
 * Time: 14:40
 */
class ArchiveAllApkTask extends DefaultTask {
    static final TAG = PackerNgPlugin.TAG

    @Input
    BaseVariant theVariant

    @Input
    PackerNgExtension theExtension

    @Input
    List<String> theMarkets

    ArchiveAllApkTask() {
        setDescription('modify original apk file and move to release dir')
    }

    @TaskAction
    void showMessage() {
        project.logger.info("${name}: ${description}")
    }

    void checkMarkets() throws GradleException {
        if (theMarkets == null || theMarkets.isEmpty()) {
            throw new InvalidUserDataException(":${name} " +
                    "no markets found, please check your market file!")
        }
    }

    SigningConfig getSigningConfig() {
        def config1 = theVariant.buildType.signingConfig
        def config2 = theVariant.mergedFlavor.signingConfig
        return config1 == null ? config2 : config1
    }

    void checkSigningConfig() throws GradleException {
        logger.info(":${name} buildType.signingConfig = " +
                "${theVariant.buildType.signingConfig}")
        logger.info(":${name} mergedFlavor.signingConfig = " +
                "${theVariant.mergedFlavor.signingConfig}")
        def signingConfig = getSigningConfig()
        if (theExtension.checkSigningConfig && signingConfig == null) {
            throw new GradleException(":${project.name}:${name} " +
                    "signingConfig not found, task aborted, " +
                    "please check your signingConfig!")
        }

        // ensure APK Signature Scheme v2 disabled.
        if (signingConfig.hasProperty("v2SigningEnabled") &&
                signingConfig.v2SigningEnabled == true) {
            throw new GradleException("Please add 'v2SigningEnabled false' " +
                    "to signingConfig to disable APK Signature Scheme v2, " +
                    "as it's not compatible with packer-ng plugin, more details at " +
                    "https://github.com/mcxiaoke/packer-ng-plugin/blob/master/compatibility.md.")
        }
    }

    void checkApkSignature(File file) throws GradleException {
        File apkPath = project.rootDir.toPath().relativize(file.toPath()).toFile()
        JarFile jarFile = new JarFile(file)
        JarEntry mfEntry = jarFile.getJarEntry("META-INF/MANIFEST.MF")
        JarEntry certEntry = jarFile.getJarEntry("META-INF/CERT.SF")
        if (mfEntry == null || certEntry == null) {
            throw new GradleException(":${name} " +
                    "apk ${apkPath} not signed, please check your signingConfig!")
        }
    }

    @TaskAction
    void modify() {
        logger.info("====================PACKER APK TASK BEGIN====================")
        checkMarkets()
        checkSigningConfig()
        File originalFile = theVariant.outputs[0].outputFile
        checkApkSignature(originalFile)
        File outputDir = theExtension.archiveOutput
        File apkPath = project.rootDir.toPath().relativize(originalFile.toPath()).toFile()
        println(":${project.name}:${name} apk: ${apkPath}")
        logger.info(":${name} output dir:${outputDir.absolutePath}")
        if (!outputDir.exists()) {
            outputDir.mkdirs()
        } else {
            logger.info(":${name} delete old apks in ${outputDir.absolutePath}")
            // delete old apks
            outputDir.eachFile(FileType.FILES) { file ->
                if (file.getName().endsWith(".apk")) {
                    file.delete()
                }
            }
        }
        logger.info(":${project.name}:${name} markets:[${theMarkets.join(', ')}]")
        for (String market : theMarkets) {
            File tempFile = new File(outputDir, market + ".tmp")
            copyTo(originalFile, tempFile)
            try {
                PackerNg.Helper.writeMarket(tempFile, market)
                String apkName = buildApkName(theVariant, market, tempFile)
                File finalFile = new File(outputDir, apkName)
                if (PackerNg.Helper.verifyMarket(tempFile, market)) {
                    println(":${project.name}:${name} Generating apk for ${market}")
                    tempFile.renameTo(finalFile)
                } else {
                    throw new GradleException(":${name} ${market} apk verify failed.")
                }
            } catch (IOException ex) {
                throw new GradleException(":${name} ${market} apk generate failed.", ex)
            } finally {
                tempFile.delete()
            }
        }
        println(":${project.name}:${name} all ${theMarkets.size()} apks saved to ${outputDir.path}")
        println("\nPackerNg Build Successful!")
        logger.info("====================PACKER APK TASK END====================")
    }

    /**
     *  build human readable apk name
     * @param variant Variant
     * @return final apk name
     */
    String buildApkName(variant, market, apkFile) {
        def buildTime = new SimpleDateFormat('yyyyMMdd-HHmmss').format(new Date())
        File file = apkFile
        def fileMD5 = HASH.md5(file)
        def fileSHA1 = HASH.sha1(file)
        def nameMap = [
                'appName'    : project.name,
                'projectName': project.rootProject.name,
                'fileMD5'    : fileMD5,
                'fileSHA1'   : fileSHA1,
                'flavorName' : market,
                'buildType'  : variant.buildType.name,
                'versionName': variant.versionName,
                'versionCode': variant.versionCode,
                'appPkg'     : variant.applicationId,
                'buildTime'  : buildTime
        ]

        def defaultTemplate = PackerNgExtension.DEFAULT_NAME_TEMPLATE
        def engine = new SimpleTemplateEngine()
        def template = theExtension.archiveNameFormat == null ? defaultTemplate : theExtension.archiveNameFormat
        def fileName = engine.createTemplate(template).make(nameMap).toString()
        return fileName + '.apk'
    }

    static void copyTo(File src, File dest) {
        def input = src.newInputStream()
        def output = dest.newOutputStream()
        output << input
        input.close()
        output.close()
    }
}
