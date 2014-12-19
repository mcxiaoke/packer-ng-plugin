package com.mcxiaoke.packer

import org.gradle.api.tasks.Copy
import org.gradle.api.tasks.TaskAction

/**
 * User: mcxiaoke
 * Date: 14/12/19
 * Time: 11:42
 */
class ArchiveApkVariantTask extends Copy {

    String variantName

    ArchiveApkVariantTask() {
        setDescription('copy variant apk to output and rename apk')
    }

    @TaskAction
    void showMessage() {
        project.logger.info("${name}: copy archives of ${variantName} to output dir")
    }
}
