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
        File target = theVariant.outputs[0].outputFile
        File output = theExtension.archiveOutput
        BufferedWriter logfile = new File(output, "log.txt").newWriter("UTF-8");
        logger.info(":${name} target: ${target.absolutePath}")
        File tempDir = new File(project.rootProject.buildDir, "apkTemp")
        if (!tempDir.exists()) {
            tempDir.mkdirs()
        }
        if (!output.exists()) {
            output.mkdirs()
        }
        PackerNg.deleteDir(output)
        logger.info(":${name} temp dir:${tempDir.absolutePath}")
        for (String market : theMarkets) {
            String apkName = buildApkName(theVariant, market)
            File tempFile = new File(tempDir, apkName)
            File finalFile = new File(output, apkName)
            PackerNg.copyFile(target, tempFile)
            PackerNg.writeMarket(tempFile, market)
            if (PackerNg.verifyMarket(tempFile, market)) {
                PackerNg.copyFile(tempFile, finalFile)
                logger.info(":${name} processed apk file for [${market}]!")
                logfile.writeLine("processed: ${apkName}")
            } else {
                logger.warn(":${name} failed to process apk file for [${market}]!")
                logfile.writeLine("aborted: ${apkName}")
            }
        }
        logfile.close()
        logger.info(":${name} ${theMarkets.size()} market apks are saved to ${output.absolutePath}")
        PackerNg.deleteDir(tempDir)
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
}
