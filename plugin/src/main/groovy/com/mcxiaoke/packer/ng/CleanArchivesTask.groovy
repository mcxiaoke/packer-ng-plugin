package com.mcxiaoke.packer.ng

import org.gradle.api.DefaultTask
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.TaskAction

/**
 * User: mcxiaoke
 * Date: 14/12/19
 * Time: 11:29
 */
class CleanArchivesTask extends DefaultTask {

    @Input
    File target

    CleanArchivesTask() {
        setDescription('clean all apk archives in output dir')
    }

    @TaskAction
    void showMessage() {
        logger.info("${name}: ${description}")
    }

    @TaskAction
    void deleteAll() {
        logger.info("${name}: delete all files in ${target.absolutePath}")
        target.deleteDir()
    }

}
