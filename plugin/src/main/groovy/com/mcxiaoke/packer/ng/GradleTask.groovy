package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import com.mcxiaoke.packer.cli.Bridge
import com.mcxiaoke.packer.cli.Helper
import groovy.text.SimpleTemplateEngine
import groovy.text.Template
import org.gradle.api.DefaultTask
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.TaskAction

import java.text.SimpleDateFormat

/**
 * User: mcxiaoke
 * Date: 15/11/23
 * Time: 14:40
 */
class GradleTask extends DefaultTask {

    @Input
    BaseVariant variant

    @Input
    GradleExtension extension

    GradleTask() {
        description = 'generate APK with channel info'
    }

    Template getNameTemplate() {
        String format
        String propValue = project.findProperty(Const.PROP_FORMAT)
        if (propValue != null) {
            format = propValue.toString()
        } else {
            format = extension.archiveNameFormat
        }
        if (format == null || format.isEmpty()) {
            format = Const.DEFAULT_FORMAT
        }
        def engine = new SimpleTemplateEngine()
        return engine.createTemplate(format)
    }

    File getOriginalApk() {
        variant.outputs.each { ot ->
            logger.info("Output APK: ${ot.name},${ot.outputFile}")
        }
        File file = variant.outputs[0].outputFile
        if (!Bridge.verifyApk(file)) {
            throw new PluginException("APK Signature Scheme v2 verify failed: '${file}'")
        }
        return file
    }

    File getOutputRoot() {
        File outputDir
        String propValue = project.findProperty(Const.PROP_OUTPUT)
        if (propValue != null) {
            String dirName = propValue.toString()
            outputDir = new File(project.rootDir, dirName)
        } else {
            outputDir = extension.archiveOutput
        }
        if (outputDir == null) {
            outputDir = new File(project.rootProject.buildDir, Const.DEFAULT_OUTPUT)
        }
        if (!outputDir.exists()) {
            outputDir.mkdirs()
        }
        return outputDir
    }

    File getVariantOutput() {
        File outputDir = getOutputRoot()
        String flavorName = variant.flavorName
        if (flavorName.length() > 0) {
            outputDir = new File(outputDir, flavorName)
        }
        if (!outputDir.exists()) {
            outputDir.mkdirs()
        } else {
            logger.info(":${name} delete old APKs in ${outputDir.absolutePath}")
            Helper.deleteAPKs(outputDir)
        }
        return outputDir
    }

    Set<String> getChannels() {
        // -P channels=ch1,ch2,ch3
        // -P channels=@channels.txt
        // channelList = [ch1,ch2,ch3]
        // channelFile = project.file("channels.txt")
        Collection<String> channels = []
        // check command line property
        def propValue = project.findProperty(Const.PROP_CHANNELS)
        if (propValue != null) {
            String prop = propValue.toString()
            logger.info(":${project.name} channels property: '${prop}'")
            if (prop.startsWith("@")) {
                def fileName = prop.substring(1)
                if (fileName != null) {
                    File f = new File(project.rootDir, fileName)
                    if (!f.isFile() || !f.canRead()) {
                        throw new PluginException("channel file not exists: '${f.absolutePath}'")
                    }
                    channels = Helper.parseChannels(f)
                } else {
                    throw new PluginException("invalid channels property: '${prop}'")
                }
            } else {
                channels = Helper.parseChannels(prop);
            }
            if (channels == null || channels.isEmpty()) {
                throw new PluginException("invalid channels property: '${prop}'")
            }
            return channels
        }
        if (extension.channelList != null) {
            channels = Helper.escape(extension.channelList)
            logger.info(":${project.name} ext.channelList: ${channels}")
        } else if (extension.channelMap != null) {
            String flavorName = variant.flavorName
            File f = extension.channelMap.get(flavorName)
            logger.info(":${project.name} extension.channelMap file: ${f}")
            if (f == null || !f.isFile()) {
                throw new PluginException("channel file not exists: '${f.absolutePath}'")
            }
            if (f != null && f.isFile()) {
                channels = Helper.parseChannels(f)
            }
        } else if (extension.channelFile != null) {
            File f = extension.channelFile
            logger.info(":${project.name} extension.channelFile: ${f}")
            if (!f.isFile()) {
                throw new PluginException("channel file not exists: '${f.absolutePath}'")
            }
            channels = Helper.parseChannels(f)
        }
        if (channels == null || channels.isEmpty()) {
            throw new PluginException("No channels found")
        }
        return channels
    }


    void showProperties() {
        logger.info("Extension: ${extension}")
        logger.info("Property: ${Const.PROP_CHANNELS} = " +
                "${project.findProperty(Const.PROP_CHANNELS)}")
        logger.info("Property: ${Const.PROP_OUTPUT} = " +
                "${project.findProperty(Const.PROP_OUTPUT)}")
        logger.info("Property: ${Const.PROP_FORMAT} = " +
                "${project.findProperty(Const.PROP_FORMAT)}")
    }

    @TaskAction
    void generate() {
        println("============================================================")
        println("PackerNg - https://github.com/mcxiaoke/packer-ng-plugin")
        println("============================================================")
        showProperties()
        File apkFile = getOriginalApk()
        File rootDir = getOutputRoot()
        File outputDir = getVariantOutput()
        Collection<String> channels = getChannels()
        Template template = getNameTemplate()
        println("Variant: ${variant.name}")
        println("Input: ${apkFile.path}")
        println("Output: ${outputDir.path}")
        println("Channels: [${channels.join(' ')}]")
        for (String channel : channels) {
            File tempFile = new File(outputDir, "tmp-${channel}.apk")
            try {
                Helper.copyFile(apkFile, tempFile)
                Bridge.writeChannel(tempFile, channel)
                String apkName = buildApkName(channel, tempFile, template)
                File finalFile = new File(outputDir, apkName)
                if (Bridge.verifyChannel(tempFile, channel)) {
                    println("Generating: ${apkName}")
                    tempFile.renameTo(finalFile)
                    logger.info("Generated: ${finalFile}")
                } else {
                    throw new PluginException("${channel} APK verify failed")
                }
            } catch (IOException ex) {
                throw new PluginException("${channel} APK generate failed", ex)
            } finally {
                tempFile.delete()
            }
        }
        println("Outputs: ${rootDir.absolutePath}")
        println("============================================================")
    }

    String buildApkName(channel, file, template) {
        def buildTime = new SimpleDateFormat('yyyyMMdd-HHmmss').format(new Date())
        def fileSHA1 = HASH.sha1(file)
        def nameMap = [
                'appName'    : project.name,
                'projectName': project.rootProject.name,
                'fileSHA1'   : fileSHA1,
                'channel'    : channel,
                'flavor'     : variant.flavorName,
                'buildType'  : variant.buildType.name,
                'versionName': variant.versionName,
                'versionCode': variant.versionCode,
                'appPkg'     : variant.applicationId,
                'buildTime'  : buildTime
        ]
        logger.info("nameMap: ${nameMap}")
        return template.make(nameMap).toString() + '.apk'
    }

    /*
    static Set<String> escape(Collection<String> cs) {
        // filter invalid chars for filename
        Pattern pattern = ~/[\/:*?"'<>|]/
        return cs.collect { it.replaceAll(pattern, "_") }.toSet()
    }
     */
}
