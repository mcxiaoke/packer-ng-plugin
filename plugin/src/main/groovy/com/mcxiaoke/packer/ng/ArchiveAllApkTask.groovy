package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import com.mcxiaoke.packer.helper.PackerNg
import groovy.text.SimpleTemplateEngine
import org.gradle.api.DefaultTask
import org.gradle.api.GradleException
import org.gradle.api.InvalidUserDataException
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.TaskAction

import java.text.SimpleDateFormat

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
        setDescription('modify original apk file and move to archive dir')
    }

    @TaskAction
    void showMessage() {
        project.logger.info("${name}: ${description}")
    }

    @TaskAction
    void modify() {
        logger.info("====================ARCHIVE APK TASK START====================")
        if (theMarkets == null || theMarkets.isEmpty()) {
            throw new InvalidUserDataException(":${name} ERROR: no markets found, task aborted!")
        }
        if (theVariant.buildType.signingConfig == null) {
            throw new GradleException(":${project.name}:${name} ERROR: android.buildTypes." +
                    "${theVariant.buildType.name}.signingConfig is null, task aborted!")
        }
        if (!theVariant.buildType.zipAlignEnabled) {

            throw new GradleException(":${project.name}:${name} ERROR: android.buildTypes." +
                    "${theVariant.buildType.name}.zipAlignEnabled is false, task aborted!")
        }
        File originalFile = theVariant.outputs[0].outputFile
        File tempDir = new File(project.rootProject.buildDir, "temp")
        File outputDir = theExtension.archiveOutput
        println(":${project.name}:${name} apk: ${originalFile.absolutePath}")
        logger.info(":${name} temp dir:${tempDir.absolutePath}")
        logger.info(":${name} output dir:${outputDir.absolutePath}")
        logger.info(":${name} delete old files in ${outputDir.absolutePath}")
        outputDir.deleteDir()
        if (!tempDir.exists()) {
            tempDir.mkdirs()
        }
        if (!outputDir.exists()) {
            outputDir.mkdirs()
        }
        logger.info(":${project.name}:${name} markets:[${theMarkets.join(', ')}]")
        theMarkets.eachWithIndex { String market, index ->
            String apkName = buildApkName(theVariant, market)
            File tempFile = new File(tempDir, apkName)
            File finalFile = new File(outputDir, apkName)
            copyTo(originalFile, tempFile)
            PackerNg.Helper.writeMarket(tempFile, market)
            if (PackerNg.Helper.verifyMarket(tempFile, market)) {
                println(":${project.name}:${name} processed apk for ${market} (${index + 1})")
                copyTo(tempFile, finalFile)
            } else {
                println(":${project.name}:${name} apk failed for ${market} (${index + 1})")
            }
        }
        println(":${project.name}:${name} all ${theMarkets.size()} apks saved to ${outputDir.path}")
        println(":${project.name}:${name} PackerNg: Market Packaging Successful!")
        logger.info(":${name} delete temp files in ${tempDir.absolutePath}")
        tempDir.deleteDir()
        logger.info("====================ARCHIVE APK TASK END====================")
    }

    /**
     *  build human readable apk name
     * @param variant Variant
     * @return final apk name
     */
    String buildApkName(variant, market) {
        def buildTime = new SimpleDateFormat('yyyyMMdd-HHmmss').format(new Date())
        def nameMap = [
                'appName'    : project.name,
                'projectName': project.rootProject.name,
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
