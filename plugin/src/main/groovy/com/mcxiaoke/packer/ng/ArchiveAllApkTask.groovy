package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import com.mcxiaoke.packer.helper.PackerNg
import groovy.text.SimpleTemplateEngine
import org.gradle.api.DefaultTask
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.TaskAction

import java.text.SimpleDateFormat

/**
 * User: mcxiaoke
 * Date: 15/11/23
 * Time: 14:40
 */
class ArchiveAllApkTask extends DefaultTask {

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
        File originalFile = theVariant.outputs[0].outputFile
        File tempDir = new File(project.rootProject.buildDir, "temp")
        File outputDir = theExtension.archiveOutput
        logger.info(":${name} apk file: ${originalFile.absolutePath}")
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
        logger.info(":${name} all markets:[${theMarkets.join(', ')}]")
        theMarkets.eachWithIndex { String market, index ->
            String apkName = buildApkName(theVariant, market)
            File tempFile = new File(tempDir, apkName)
            File finalFile = new File(outputDir, apkName)
            copyTo(originalFile, tempFile)
            PackerNg.Helper.writeMarket(tempFile, market)
            if (PackerNg.Helper.verifyMarket(tempFile, market)) {
                println(":${name} processed No.${index + 1} apk file for ${market}")
                copyTo(tempFile, finalFile)

            } else {
                logger.error(":${name} failed to process ${market} apk file!")
            }
        }
        println(":${name} ${theMarkets.size()} apks saved to ${outputDir.path}")
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
