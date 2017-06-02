package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import com.mcxiaoke.packer.cli.Packer
import groovy.io.FileType
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
class GradleTask extends DefaultTask {

    @Input
    BaseVariant variant

    @Input
    GradleExtension extension

    GradleTask() {
        setDescription('pack original apk file and move to output dir')
    }

    @TaskAction
    void showMessage() {
        project.logger.info("${name}: ${description}")
    }

    void checkChannels(List<String> channels) throws GradleException {
        if (channels == null || channels.isEmpty()) {
            throw new InvalidUserDataException(":${name} " +
                    "no channels found, please check your market file!")
        }
    }

    void checkSignature(File file) throws GradleException {
        boolean apkVerified = Packer.verifyApk(file)
        if (!apkVerified) {
            throw new GradleException(":${name} " +
                    "apk ${file} not v2 signed, please check your signingConfig!")
        }
    }

    List<String> getChannels() {
        // -P channels=ch1,ch2,ch3
        // -P channels=@channels.txt
        // channelList = [ch1,ch2,ch3]
        // channelFile = project.file("channels.txt")
        List<String> channels = []
        if (project.hasProperty("channels")) {
            def pv = project.property("channels").toString();
            logger.info(":${project.name} channels property: ${pv}")
            if (pv.startsWith("@")) {
                def fp = pv.substring(1)
                if (fp != null) {
                    File f = new File(project.rootDir, fp)
                    channels = readChannels(f)
                }
            } else {
                channels = pv.split(",")
            }
        } else if (extension.channelList != null) {
            channels = extension.channelList
            logger.info(":${project.name} ext.channelList: ${extension.channelList}")
        } else {
            File f;
            if (extension.channelFile != null) {
                f = extension.channelFile
            } else {
                f = new File(project.rootDir, "channels.txt")
            }
            logger.info(":${project.name} extension.channelFile: ${f}")
            channels = readChannels(f)
        }
        if (channels == null) {
            channels = []
        }
        return channels
    }

    List<String> readChannels(File file) {
        List<String> channels = []
        file.eachLine { line, number ->
            String[] parts = line.split('#')
            if (parts && parts[0]) {
                def c = parts[0].trim()
                if (c) {
                    channels.add(c)
                }
            } else {
                logger.info(":${project.name} skip invalid #${number}:'${line}'")
            }
        }
        return channels
    }

    @TaskAction
    void pack() {
        logger.info("====================PACKER NG TASK BEGIN====================")
        File originalFile = variant.outputs[0].outputFile
        checkSignature(originalFile)
        List<String> channels = getChannels();
        checkChannels(channels)
        File outputDir = extension.archiveOutput
        File apkPath = project.rootDir.toPath().relativize(originalFile.toPath()).toFile()
        println(":${project.name}:${name} apk: ${apkPath}")
        logger.info(":${name} output dir:${outputDir.absolutePath}")
        if (!outputDir.exists()) {
            outputDir.mkdirs()
        } else {
            logger.info(":${name} delete old apks in ${outputDir.absolutePath}")
            // delete old APKs
            outputDir.eachFile(FileType.FILES) { file ->
                if (file.getName().endsWith(".apk")) {
                    file.delete()
                }
            }
        }
        println(":${project.name}:${name} channels:[${channels.join(', ')}]")
        for (String channel : channels) {
            File tempFile = new File(outputDir, channel + ".tmp")
            copyTo(originalFile, tempFile)
            try {
                Packer.writeChannel(tempFile, channel)
                String apkName = buildApkName(variant, channel, tempFile)
                File finalFile = new File(outputDir, apkName)
                if (Packer.verifyChannel(tempFile, channel)) {
                    println(":${project.name}:${name} Generating apk for ${channel}")
                    tempFile.renameTo(finalFile)
                } else {
                    throw new GradleException(":${name} ${channel} apk verify failed.")
                }
            } catch (IOException ex) {
                throw new GradleException(":${name} ${channel} apk generate failed.", ex)
            } finally {
                tempFile.delete()
            }
        }
        println(":${project.name}:${name} all ${channels.size()} apks saved to ${outputDir.path}")
        println("\nPackerNg Build Successful!")
        logger.info("====================PACKER NG TASK END====================")
    }

    String buildApkName(variant, channel, apkFile) {
        def buildTime = new SimpleDateFormat('yyyyMMdd-HHmmss').format(new Date())
        File file = apkFile
        def fileSHA1 = HASH.sha1(file)
        def nameMap = [
                'appName'    : project.name,
                'projectName': project.rootProject.name,
                'fileSHA1'   : fileSHA1,
                'channel'    : channel,
                'buildType'  : variant.buildType.name,
                'versionName': variant.versionName,
                'versionCode': variant.versionCode,
                'appPkg'     : variant.applicationId,
                'buildTime'  : buildTime
        ]

        def dt = GradleExtension.DEFAULT_NAME_TEMPLATE
        def engine = new SimpleTemplateEngine()
        def template = extension.archiveNameFormat == null ? dt : extension.archiveNameFormat
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
