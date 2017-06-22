package com.mcxiaoke.packer.ng

import org.gradle.api.DefaultTask
import org.gradle.api.tasks.Input
import org.gradle.api.tasks.TaskAction

/**
 * User: mcxiaoke
 * Date: 14/12/19
 * Time: 11:29
 */
class CleanTask extends DefaultTask {

    @Input
    File target

    CleanTask() {
        description = 'clean all files in output dir'
    }

    @TaskAction
    void deleteAll() {
        logger.info("${name}: delete all files in ${target.absolutePath}")
        target.deleteDir()
    }

}
