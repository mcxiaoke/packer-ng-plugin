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
        // add markets must before evaluate
        def hasMarkets = parseMarkets()
        applyPluginTasks(hasMarkets)
    }

    void applyExtension() {
        // setup plugin and extension
        project.configurations.create(PLUGIN_NAME).extendsFrom(project.configurations.compile)
        this.modifierExtension = project.extensions.create(PLUGIN_NAME, PackerNgExtension, project)
    }

    void applyPluginTasks(hasMarkets) {
        project.afterEvaluate {
            checkCleanTask()
            //applySigningConfigs()
            project.android.applicationVariants.all { BaseVariant variant ->
                if (variant.buildType.name != "debug") {
                    if (hasMarkets) {
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
            warn("parseMarkets() invalid market file path, ignore")
            throw new StopExecutionException("invalid market file path : '${marketsFilePath}'")
        }

        File marketsFile = project.rootProject.file(marketsFilePath)
        if (!marketsFile.exists()) {
            debug("parseMarkets() market file not found, ignore")
            throw new StopExecutionException("market file not found: '${marketsFile.absolutePath}'")
        }

        if (!marketsFile.isFile()) {
            warn("parseMarkets() market file is not a file, ignore")
            throw new StopExecutionException("market file is not a file: '${marketsFile.absolutePath}'")
        }

        if (!marketsFile.canRead()) {
            warn("parseMarkets() market file not readable, ignore")
            throw new StopExecutionException("market file not readable: '${marketsFile.absolutePath}'")
        }
        debug("parseMarkets() file: ${marketsFile}")
        // add all markets
        marketsFile.eachLine { line, number ->
            debug("parseMarkets() ${number}:'${line}'")
            String[] parts = line.split('#')
            if (parts && parts[0]) {
                def market = parts[0].trim()
                if (market) {
                    debug("apply new market: " + market)
                    markets.add(market)
                }
            } else {
                warn("parseMarkets() skip invalid line: ${number}:[${line}]")
            }
        }
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
        def archiveTask = project.task("archiveApk${variant.name.capitalize()}",
                type: ArchiveAllApkTask) {
            theVariant = variant
            theExtension = modifierExtension
            theMarkets = markets
            dependsOn variant.assemble
        }

        debug("checkArchiveTask() new task:${archiveTask.name}")

        def buildTypeName = variant.buildType.name
        if (variant.name != buildTypeName) {
            def Task task = checkArchiveAllTask(buildTypeName)
            task.dependsOn archiveTask
        }
    }

    /**
     * add archiveApkType task if not added
     * @param buildTypeName buildTypeName
     * @return task
     */
    Task checkArchiveAllTask(buildTypeName) {
        def taskName = "archiveApk${buildTypeName.capitalize()}"
        def task = project.tasks.findByName(taskName)
        if (task == null) {
            task = project.task(taskName, type: ArchiveApkBuildTypeTask) {
                typeName = buildTypeName
            }
        }
        return task
    }

    /**
     *  add cleanArchives task if not added
     * @return task
     */
    void checkCleanTask() {
        def output = modifierExtension.archiveOutput
        debug("checkCleanTask() create clean archives task, path:${output}")
        def task = project.task("cleanArchives",
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
