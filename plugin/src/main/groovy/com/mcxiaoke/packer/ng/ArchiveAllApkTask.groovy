package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import com.mcxiaoke.packer.ng.PackerNgExtension
import com.mcxiaoke.packer.zip.ZipHelper
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
        File target = theVariant.outputs[0].outputFile
        File output = theExtension.archiveOutput
        project.logger.info("${name}: target: ${target.absolutePath}")
        File tempDir = new File(project.rootProject.buildDir, "apkTemp")
        if (!tempDir.exists()) {
            tempDir.mkdirs()
        }
        if (!output.exists()) {
            output.mkdirs()
        }
        for (String market : theMarkets) {
            String apkName = buildApkName(theVariant, market)
            logger.info("${name}: ${apkName}")
            File tempFile = new File(tempDir, apkName)
            File finalFile = new File(output, apkName)
            ZipHelper.copyFile(target, tempFile)

            ZipHelper.writeMarket(tempFile, market)
            if (ZipHelper.verifyMarket(tempFile, market)) {
                ZipHelper.copyFile(tempFile, finalFile)
            } else {
                logger.warn("${name}: failed to process file: ${apkName}")
            }
        }
        ZipHelper.deleteDir(tempDir)
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
        def apkName = fileName + '.apk'
        logger.debug "buildApkName() final $apkName"
        return apkName
    }
}
