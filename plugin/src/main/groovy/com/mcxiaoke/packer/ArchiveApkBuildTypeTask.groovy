package com.mcxiaoke.packer
import org.gradle.api.DefaultTask
import org.gradle.api.tasks.TaskAction
/**
 * User: mcxiaoke
 * Date: 14/12/19
 * Time: 12:08
 */
class ArchiveApkBuildTypeTask extends DefaultTask {

    String typeName

    ArchiveApkBuildTypeTask() {
        setDescription('copy archives of this build type to output dir')
    }

    @TaskAction
    void showMessage() {
        project.logger.info("${name}: copy archives of this build type to output dir for ${typeName}")
    }
}
