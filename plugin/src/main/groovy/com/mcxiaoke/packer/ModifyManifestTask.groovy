package com.mcxiaoke.packer

import groovy.xml.StreamingMarkupBuilder
import groovy.xml.XmlUtil
import org.gradle.api.DefaultTask
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.TaskAction

/**
 * User: mcxiaoke
 * Date: 14/12/17
 * Time: 16:42
 */
/**
 *  parse and modify manifest file
 *  apply market value to meta-data
 */
class ModifyManifestTask extends DefaultTask {
    @InputFile
    @Input
    def File manifestFile
    @Input
    def manifestMatcher
    @Input
    def flavorName

    ModifyManifestTask() {
        setDescription("modify manifest meta-data to apply market value")
    }

    @TaskAction
    void showMessage() {
        project.logger.info("${name}: ${description}")
    }

    @TaskAction
    void processMeta() {
        project.logger.info("${name}: manifestFile:${manifestFile.absolutePath}")
        def root = new XmlSlurper().parse(manifestFile)
                .declareNamespace(android: "http://schemas.android.com/apk/res/android")
        project.logger.info("${name}: matcher:${manifestMatcher}")
        manifestMatcher?.each { String pattern ->
            def metadata = root.application.'meta-data'
            def found = metadata.find { mt -> pattern == mt.'@android:name'.toString() }
            if (found.size() > 0) {
                project.logger.info("${name}: ${pattern} found, modify it")
                found.replaceNode {
                    'meta-data'('android:name': found."@android:name", 'android:value': flavorName) {}
                }
            } else {
                project.logger.info("${name}: ${pattern} not found, add it.")
                root.application.appendNode {
                    'meta-data'('android:name': pattern, 'android:value': flavorName) {}
                }
            }
        }

        serializeXml(root, manifestFile)
    }

    /**
     *  write xml to file
     * @param xml xml
     * @param file file
     */
    static void serializeXml(xml, file) {
        XmlUtil.serialize(new StreamingMarkupBuilder().bind { mkp.yield xml },
                new FileWriter(file))
    }
}
