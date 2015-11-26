package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.ProjectConfigurationException
import org.gradle.api.Task
import org.gradle.api.tasks.StopExecutionException

// Android Multi Packer Plugin Source
class PackerNgPlugin implements Plugin<Project> {
    static final String PLUGIN_NAME = "packer"
    static final String P_MARKET = "market"

    Project project
    PackerNgExtension modifierExtension
    List<String> markets;

    @Override
    void apply(Project project) {
        if (!hasAndroidPlugin(project)) {
            throw new ProjectConfigurationException("the android plugin must be applied", null)
        }

        this.project = project
        applyExtension()
        parseMarkets()
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
            //applySigningConfigs()
            project.android.applicationVariants.all { BaseVariant variant ->
                if (variant.buildType.name != "debug") {
                    if (markets) {
                        // modify  archive apk
                        // only when markets found and not debug
                        debug("applyPluginTasks() archive task.")
                        checkArchiveTask(variant)
                    }
                }
            }
        }
    }

/**
 *  parse markets file
 * @param project Project
 * @return found markets file
 */
    boolean parseMarkets() {
        if (!project.hasProperty(P_MARKET)) {
            debug("parseMarkets() market property not found, ignore")
            return false
        }

        markets = new ArrayList<String>();

        // check markets file exists
        def marketsFilePath = project.property(P_MARKET).toString()
        if (!marketsFilePath) {
            warn("parseMarkets()  markets file path property not found")
            // if not set, use default ./markets.txt
            marketsFilePath = "markets.txt"
        }

        File file = project.rootProject.file(marketsFilePath)
        if (!file.exists()) {
            debug("parseMarkets() markets file not found")
            throw new StopExecutionException("market file not found: '${file.absolutePath}'")
        }

        if (!file.isFile()) {
            warn("parseMarkets() markets file is not a file")
            throw new StopExecutionException("market file is not a file: '${file.absolutePath}'")
        }

        if (!file.canRead()) {
            warn("parseMarkets() markets file not readable")
            throw new StopExecutionException("market file not readable: '${file.absolutePath}'")
        }
        debug("parseMarkets() markets file: ${file.absolutePath}")
        // add all markets
        file.eachLine { line, number ->
            String[] parts = line.split('#')
            if (parts && parts[0]) {
                def market = parts[0].trim()
                if (market) {
                    markets.add(market)
                }
            } else {
                warn("parseMarkets() skip invalid line ${number}:[${line}]")
            }
        }
        debug("parseMarkets() markets:[${markets.join(', ')}]")
        return true
    }

/**
 *  add archiveApk tasks
 * @param variant current Variant
 */
    void checkArchiveTask(BaseVariant variant) {
        if (variant.buildType.signingConfig == null) {
            warn("${variant.name}: signingConfig is null, ignore archive task.")
            return
        }
        if (!variant.buildType.zipAlignEnabled) {
            warn("${variant.name}: zipAlignEnabled==false, ignore archive task.")
            return
        }
        debug("checkArchiveTask() for ${variant.name}")
        def File inputFile = variant.outputs[0].outputFile
        def File tempDir = modifierExtension.tempOutput
        def File outputDir = modifierExtension.archiveOutput
        debug("checkArchiveTask() input: ${inputFile}")
        debug("checkArchiveTask() temp: ${tempDir}")
        debug("checkArchiveTask() output: ${outputDir}")
        def archiveTask = project.task("apk${variant.name.capitalize()}",
                type: ArchiveAllApkTask) {
            theVariant = variant
            theExtension = modifierExtension
            theMarkets = markets
            dependsOn variant.assemble
        }

        debug("checkArchiveTask() new task:${archiveTask.name}")

        def buildTypeName = variant.buildType.name
        if (variant.name != buildTypeName) {
            def Task task = project.task("apk${buildTypeName.capitalize()}", dependsOn: archiveTask)
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
 *  check android plugin applied
 * @param project Project
 * @return plugin applied
 */
    static boolean hasAndroidPlugin(Project project) {
        return project.plugins.hasPlugin("com.android.application")
    }

/**
 *  print debug messages
 * @param msg msg
 * @param vars vars
 */
    void debug(String msg, Object... vars) {
        project.logger.info(msg, vars)
    }

    void warn(String msg, Object... vars) {
        project.logger.warn(msg, vars)
    }

}
