package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.ProjectConfigurationException

// Android Multi Packer Plugin Source
class PackerNgPlugin implements Plugin<Project> {
    static final String TAG = "PackerNg"
    static final String PLUGIN_NAME = "packer"
    static final String P_MARKET = "market"

    Project project
    PackerNgExtension modifierExtension
    List<String> markets;

    @Override
    void apply(Project project) {
        this.project = project
        if (!project.plugins.hasPlugin("com.android.application")) {
            throw new ProjectConfigurationException("the android plugin must be applied", null)
        }
        applyExtension()
        applyPluginTasks()
    }

    void applyExtension() {
        // setup plugin and extension
        project.configurations.create(PLUGIN_NAME).extendsFrom(project.configurations.compile)
        this.modifierExtension = project.extensions.create(PLUGIN_NAME, PackerNgExtension, project)
    }

    void applyPluginTasks() {
        project.afterEvaluate {
            checkCleanTask()
            debug(":${project.name} flavors: ${project.android.productFlavors.collect { it.name }}")
            //applySigningConfigs()
            project.android.applicationVariants.all { BaseVariant variant ->
                checkPackerNgTask(variant)
            }
        }
    }

/**
 *  add archiveApk tasks
 * @param variant current Variant
 */
    void checkPackerNgTask(BaseVariant variant) {
        debug("checkPackerNgTask() for ${variant.name}")
        def File inputFile = variant.outputs[0].outputFile
        def File tempDir = modifierExtension.tempOutput
        def File outputDir = modifierExtension.archiveOutput
        debug("checkPackerNgTask() input: ${inputFile}")
        debug("checkPackerNgTask() temp: ${tempDir}")
        debug("checkPackerNgTask() output: ${outputDir}")
        def archiveTask = project.task("apk${variant.name.capitalize()}",
                type: ArchiveAllApkTask) {
            theVariant = variant
            theExtension = modifierExtension.clone()
            if (modifierExtension.flavorMarket.containsKey(variant.flavorName)) {
                debug("checkPackerNgTask() variant: ${variant.flavorName}")
                theExtension.archiveOutput = new File(modifierExtension.archiveOutput, variant.flavorName)
                debug("checkPackerNgTask() variant: ${theExtension.archiveOutput.absolutePath}")
                theMarkets = new MarkertsParser(project, modifierExtension.flavorMarket.get(variant.flavorName)).parseMarkets()
            } else if (!variant.flavorName.equals("")) {
                theExtension.archiveOutput = new File(modifierExtension.archiveOutput, variant.flavorName)
                theMarkets = new MarkertsParser(project, modifierExtension.market).parseMarkets()
            } else {
                theMarkets = new MarkertsParser(project, modifierExtension.market).parseMarkets()
            }
            dependsOn variant.assemble

        }

        debug("checkPackerNgTask() new variant task:${archiveTask.name}")

        def buildTypeName = variant.buildType.name
        if (variant.name != buildTypeName) {
            def taskName = "apk${buildTypeName.capitalize()}"
            def task = project.tasks.findByName(taskName)
            if (task == null) {
                debug("checkPackerNgTask() new build type task:${taskName}")
                task = project.task(taskName, dependsOn: archiveTask)
            } else {
                task.dependsOn archiveTask
            }
        }
    }

    /**
     *  add cleanArchives task if not added
     * @return task
     */
    void checkCleanTask() {
        def output = modifierExtension.archiveOutput
        debug("checkCleanTask() create clean archived apks task, path:${output}")
        def task = project.task("cleanApks",
                type: CleanArchivesTask) {
            target = output
        }

        project.getTasksByName("clean", true)?.each {
            it.dependsOn task
        }
    }

/**
 *  print debug messages
 * @param msg msg
 * @param vars vars
 */
    void debug(String msg) {
        project.logger.info(msg)
    }

}
