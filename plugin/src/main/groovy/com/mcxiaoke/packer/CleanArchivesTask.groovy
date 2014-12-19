package com.mcxiaoke.packer
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
        project.logger.info("${name}: ${description}")
    }

    @TaskAction
    void deleteAll() {
        project.logger.info("${name}: delete all files in ${target.absolutePath}")
        deleteDir(target)
    }

    static void deleteDir(File dir) {
        if (dir && dir.listFiles()) {
            dir.listFiles().sort().each { File file ->
                if (file.isFile()) {
                    file.delete()
                } else {
                    file.deleteDir()
                }
            }
        }
    }
}
