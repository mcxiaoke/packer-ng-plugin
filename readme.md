Android多渠道打包工具Gradle插件
================================

## 项目介绍

**gradle-packer-plugin** 是Android多渠道打包工具Gradle插件，可方便的于自动化构建系统集成，通过很少的配置可实现如下功能 ：

* 支持自动替换AndroidManifest文件中的meta-data字段实现多渠道打包
* 支持自定义多渠道打包输出的存放目录和最终APK文件名
* 支持自动修改versionName中的build版本号，实现版本号自动增长

## 参与开发  

**gradle-packer-plugin** 库路径： `com.mcxiaoke.gradle:packer:1.0.+` 简短名：`packer`，可以在项目的 `build.gradle` 中指定使用

项目说明 `plugin` 目录是插件的源代码，用 `Groovy` 语言编写，项目 `sample` 目录是一个完整的Andoid项目示例，在项目根目录有几个脚本可以用于测试：

* **deploy-local.sh** 部署插件到本地的 `/tmp/repo/` 目录，方便即时测试
* **test-build.sh** 部署并测试插件是否有错误，测试build版本号自动功能
* **test-market** 部署并测试插件是否有错误，测试多渠道打包功能 


## 最新版本

- [![Maven Central](http://img.shields.io/badge/2014.12.20-com.mcxiaoke.gradle:packer:1.0.+-brightgreen.svg)](http://search.maven.org/#artifactdetails%7Ccom.mcxiaoke.gradle%7Cpacker%7C1.2.0%7Cjar) 

## 使用方法

#### 修改项目根目录的 `build.gradle` ：

```groovy

buildscript {
    repositories {
		mavenCentral()
	}

	dependencies{
		classpath 'com.mcxiaoke.gradle:packer:1.0.+'
	}
}  
```

#### 修改Android项目的 `build.gradle` :

```groovy

apply plugin: 'packer'  
```

### 多渠道打包

需要在命令行指定 -Pmarket=yourMarketFileName属性，market是你的渠道名列表，一行一个渠道，名字和注释用#号分割，举例： `Google_Play#build for google play store` 

### 文件名格式

可以使用 `archiveNameFormat` 自定义渠道打包输出的APK文件名格式，默认格式是 `${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}` 举例：假如你的App包名是  `com.your.company` ，渠道名是 `Google_Play` ，`buildType` 是 `release` ，`versionName` 是 `2.1.15` ，`versionCode` 是 `200115` ，那么生成的APK的文件名是 `com.your.company-Google_Player-release-2.1.15-20015.apk` 

### 版本号自增

版本号自动会自动在在 `vesionName` 尾部增加 `.buildNumer` 该字段会自动增长，举例：如果App本来的版本号是 1.2.3，那么使用版本号自动后会是 `1.2.3.1` `1.2.3.2` ... `1.2.3.25` 末尾的build版本号会随构建次数自动增长。注意：如果在命令行使用 `-PbuildNum=123` 这种形式指定了build版本号，那么自增版本号不会生肖
	
## 配置选项 

* **archiveOutput**  指定渠道打包输出的APK存放目录，默认位于`${项目根目录}/build/archives`   

* **archiveNameFormat** - `Groovy格式字符串`， 指定渠道打包输出的APK文件名格式，默认文件名格式是： `${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}`，可使用以下变量:  
  
  * *projectName* - 项目名字
  * *appName* - App模块名字
  * *appPkg* - App包名 (`applicationId`或`packageName`)
  * *buildType* - `buildType` (release/debug/beta等)
  * *flavorName* - `flavorName` (对应渠道打包中的渠道名字)
  * *versionName* - `versionName` (显示用的版本号)
  * *versionCode* - `versionCode` (内部版本号)
  * *buildTime* - `buildTime` (编译构建日期时间)

* **manifestMatcher** 指定渠道打包需要修改的AndroidManifest.xml的meta-data的项名称，列表类型，举例： `['UMENG_CHANNEL', 'Promotion_Market']`，注意：需要同时在命令行使用 `-Pmarket=yourMarketFileName` 指定market属性多渠道打包才会生效 

* **buildNumberAuto** - 布尔值，是否使用自增版本号功能 设为 `true` 为使用插件提供的自增build版本号功能，该功能会在项目目录生成一个 `packer.properties` 文件，建议加入到 `.gitignore` 中，注意：该功能不会应用于多渠道打包生成的APK，不会影响渠道打包

* **buildNumberTypeMatcher** - 指定需要使用自增版本号的buildType，列表类型，举例： `['release', 'beta']` 默认是全部


## 使用示例：

### 多渠道打包
* 修改项目根目录的 `build.gradle` 在 `buildscript.dependencies` 部分加入 `classpath 'com.mcxiaoke.gradle:packer:1.0.0'`  
* 修改Android项目的 `build.gradle` 在 `apply plugin: 'com.android.application'` 下面加入 `apply plugin: 'packer'`  
* 修改Android项目的 `build.gradle` 加入如下配置项，`manifestMatcher` 是必须指定的，其它几项可以使用默认值：  

```groovy 
 
packer {
    // 指定渠道打包输出目录
    // archiveOutput = file(new File(project.rootProject.buildDir.path, "archives"))
    // 指定渠道打包输出文件名格式
    // archiveNameFormat = ''
    // 指定渠道打包需要修改的AndroidManifest文件项
    manifestMatcher = ['UMENG_CHANNEL','Promotion_Market']

}

```

* 假设渠道列表文件位于项目根目录，文件名为 `markets.txt` ，在项目根目录打开shell运行命令：
    `./gradlew -Pmarket=markets.txt clean archiveApkRelease`  如果没有错误，打包完成后你可以在 `${项目根目录}/build/archives/` 目录找到最终的渠道包。说明：渠道打包的 `gradle task` 名字是 `archiveApk${buildType}` buildType一般是release，也可以是你自己指定的beta或者someOtherType，使用时首字母需要大写

### 版本号自增

* 修改项目根目录的 `build.gradle` 在 `buildscript.dependencies` 部分加入 `classpath 'com.mcxiaoke.gradle:packer:1.0.0'`  
* 修改Android项目的 `build.gradle` 在 `apply plugin: 'com.android.application'` 下面加入 `apply plugin: 'packer'`  
* 修改Android项目的 `build.gradle` 加入如下配置项，buildNumberAuto是开关

```groovy   

packer {
    // 指定是否使用build版本号自增
    buildNumberAuto = true
    // 指定使用版本号自增的buildType，默认是全部
    buildNumberTypeMatcher = ['release', 'beta']

}

```
* 在项目根目录打开shell运行命令： `./gradlew clean assembleRelease`  如果没有错误，你可以安装apk查看versionName自增是否生效， 也可以运行 `./gradlew -PbuildNum=123 clean assembleRelease` 从命令行指定build版本号，该方法多用于自动化构建系统


## 完整示例：

项目的 `samples` 目录包含一个完整的项目示例，可以查看其中的 `build.gradle` 

```groovy

buildscript {
    repositories {
        mavenCentral()
    }
    dependencies {
        classpath 'com.android.tools.build:gradle:1.0.0'
        // `添加packer插件依赖`
        classpath 'com.mcxiaoke.gradle:packer:1.0.0'
    }
}

repositories {
    mavenCentral()
}

apply plugin: 'com.android.application'
// 建议放在 `com.android.application` 下面  
// `使用 apply plugin使用packer插件`  
apply plugin: 'packer'

packer {
    // 指定渠道打包输出目录
    archiveOutput = file(new File(project.rootProject.buildDir.path, "apks"))
    // 指定渠道打包输出文件名格式
    archiveNameFormat = ''
    // 指定渠道打包需要修改的AndroidManifest文件项
    manifestMatcher = ['UMENG_CHANNEL','Promotion_Market']
    // 指定是否使用build版本号自增
    buildNumberAuto = true
    // 指定使用版本号自增的buildType，默认是全部
    buildNumberTypeMatcher = ['release', 'beta']

}

android {
    compileSdkVersion 21
    buildToolsVersion "21.1.1"

    defaultConfig {
        applicationId "com.mcxiaoke.packer.sample"
        minSdkVersion 15
        targetSdkVersion 21
        versionCode 12345
        versionName "1.2.3"
    }

    signingConfigs {
        release {
            storeFile file("android.keystore")
            storePassword "android"
            keyAlias "android"
            keyPassword "android"
        }
    }

    buildTypes {
        release {
            signingConfig signingConfigs.release
            minifyEnabled false
        }

        beta {
            signingConfig signingConfigs.release
            minifyEnabled false
            debuggable true
        }

    }

}

dependencies {
    compile fileTree(dir: 'libs', include: ['*.jar'])
    compile 'com.android.support:support-v4:21.0.2'
}


```


## 项目许可


    Copyright 2013 Chris Banes

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

