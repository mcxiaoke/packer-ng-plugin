package com.mcxiaoke.packer

import org.gradle.api.DefaultTask
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.InputFile
import org.gradle.api.tasks.OutputFile
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
class ProcessMetaDataTask extends DefaultTask {
    @InputFile
    @OutputFile
    def File manifestFile
    @Input
    def manifestMatcher
    @Input
    def flavorName

    ProcessMetaDataTask() {
        setDescription("modify manifest meta-data to apply market value")
    }

    @TaskAction
    void processMeta() {
        def root = new XmlSlurper().parse(manifestFile)
                .declareNamespace(android: "http://schemas.android.com/apk/res/android")
        project.logger.debug("processMeta() manifest matcher:${manifestMatcher}")
        manifestMatcher?.each { String pattern ->
            project.logger.debug("processMeta() check pattern:${manifestMatcher}");
            def metadata = root.application.'meta-data'
            def found = metadata.find { mt -> pattern == mt.'@android:name'.toString() }
            if (found.size() > 0) {
                project.logger.debug(":${name}:meta-data ${pattern} found, modify it")
                found.replaceNode {
                    'meta-data'('android:name': found."@android:name", 'android:value': flavorName) {}
                }
            } else {
                project.logger.debug(":${name}:meta-data ${pattern} not found, add it.")
                root.application.appendNode {
                    'meta-data'('android:name': pattern, 'android:value': flavorName) {}
                }
            }
        }

        AndroidPackerPlugin.serializeXml(root, manifestFile)
    }
}
