package com.mcxiaoke.packer

import org.junit.Assert
import org.gradle.api.Project
import org.gradle.api.ProjectConfigurationException
import org.gradle.testfixtures.ProjectBuilder
import org.junit.Before
import org.junit.Rule
import org.junit.Test
import org.junit.rules.ExpectedException

class AndroidPackerPluginTest {
    @Rule
    public ExpectedException thrown = ExpectedException.none()

    @Before
    public void setUp() {
    }

    @Test
    public void testSupportedAndroidVersion() {
        Assert.assertFalse(AndroidPackerPlugin.isVersionSupported('0.11.+'))
        Assert.assertFalse(AndroidPackerPlugin.isVersionSupported('0.13.1'))
        Assert.assertTrue(AndroidPackerPlugin.isVersionSupported('0.14.+'))
        Assert.assertTrue(AndroidPackerPlugin.isVersionSupported('0.14.2'))
        Assert.assertTrue(AndroidPackerPlugin.isVersionSupported('1.0.0-rc1'))
        Assert.assertTrue(AndroidPackerPlugin.isVersionSupported('1.0.0'))
    }

    @Test(expected = ProjectConfigurationException.class)
    public void testWithoutAndroidPlugin() {
        Project project = ProjectBuilder.builder().build()
        configBuildScript(project, 'com.android.tools.build:gradle:1.0.0')
        new AndroidPackerPlugin().apply(project)
    }

    @Test
    public void testWithAndroidPlugin() {
        Project project = ProjectBuilder.builder().build()
        configBuildScript(project, 'com.android.tools.build:gradle:1.0.0')
        project.apply plugin: 'com.android.application'
        new AndroidPackerPlugin().apply(project)
    }

    @Test(expected = IllegalStateException.class)
    public void testUnSupportedAndroidPlugin() {
        Project project = ProjectBuilder.builder().build()
        configBuildScript(project, 'com.android.tools.build:gradle:0.13.1')
        project.apply plugin: 'com.android.application'
        new AndroidPackerPlugin().apply(project)
        project.evaluate()
    }

//    @Test
//    public void testVariantsAndBuildTypes() {
//        Project project = createProject()
//        project.evaluate()
//        def variants = project.android.applicationVariants
//        def variantNames = variants.collect { it.name }.join(' ')
//        Assert.assertEquals(variants.size(), 3)
//        Assert.assertTrue(variantNames.contains('beta'))
//
//        def variantBeta = variants.find { it.buildType.name == 'beta' }
//        Assert.assertEquals(variantBeta.buildType.name, 'beta')
//    }

    private Project createProject() {
        Project project = ProjectBuilder.builder().withName('plugin-test').build()
//        configBuildScript(project, 'com.android.tools.build:gradle:1.0.0')
        project.apply plugin: 'com.android.application'
        project.apply plugin: 'packer'
        project.android {
            compileSdkVersion 21
            buildToolsVersion "21.1.1"

            defaultConfig {
                minSdkVersion 14
                targetSdkVersion 21
                versionCode 1
                versionName "1.0.0"
                applicationId 'com.mcxiaoke.packer.test'
            }

            signingConfigs {
                release {
                    storeFile project.file("android.keystore")
                    storePassword "android"
                    keyAlias "android"
                    keyPassword "android"
                }

            }
        }
        return project
    }

    static void configBuildScript(Project project, String androidVersion) {
        project.buildscript {
            repositories {
                maven { url "/tmp/repo/" }
                mavenCentral()
            }
            dependencies {
                classpath androidVersion
            }
        }
    }

}
