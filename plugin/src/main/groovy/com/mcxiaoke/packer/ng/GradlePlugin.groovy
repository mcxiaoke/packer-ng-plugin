package com.mcxiaoke.packer.ng

import com.android.build.gradle.api.BaseVariant
import org.gradle.api.Plugin
import org.gradle.api.Project
import org.gradle.api.ProjectConfigurationException

// Android PackerNg Plugin Source
class GradlePlugin implements Plugin<Project> {
    static final String TAG = "PackerNg"
    static final String PLUGIN_NAME = "packer"

    Project project

    @Override
    void apply(Project project) {
        this.project = project
        if (!project.plugins.hasPlugin("com.android.application")) {
            throw new ProjectConfigurationException(
                    "the android plugin must be applied", null)
        }
        project.configurations.create(PLUGIN_NAME).extendsFrom(project.configurations.compile)
        project.extensions.create(PLUGIN_NAME, GradleExtension, project)
        project.afterEvaluate {
            project.android.applicationVariants.all { BaseVariant variant ->
                addPackTask(variant)
            }
        }
    }

    void addPackTask(BaseVariant v) {
        debug("addPackTask() for ${v.name}")
        def packTask = project.task("apk${v.name.capitalize()}",
                type: GradleTask) {
            variant = v
            extension = project.packer
            dependsOn v.assemble
        }

        debug("addPackTask() new variant task:${packTask.name}")

        def buildTypeName = v.buildType.name
        if (v.name != buildTypeName) {
            def taskName = "apk${buildTypeName.capitalize()}"
            def task = project.tasks.findByName(taskName)
            if (task == null) {
                debug("addPackTask() new build type task:${taskName}")
                project.task(taskName, dependsOn: packTask)
            }
        }
    }

    void debug(String msg) {
        project.logger.info(msg)
    }

}
