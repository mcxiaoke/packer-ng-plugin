极速Android渠道打包Gradle插件
========

## 最新版本

- 2015.11.26 发布1.0.0版，使用全新的极速打包方式，只需要编译一次 

## 项目介绍

**gradle-packer-ng-plugin** 是Android多渠道打包工具Gradle插件，极速打包，五分钟可以打包几百个渠道，可方便的用于自动化构建系统集成，通过很少的配置可支持自定义输出目录和最终APK文件名，库路径： `com.mcxiaoke.gradle:packer-ng:1.0.+` 简短名：`packer`，可以在项目的 `build.gradle` 中指定使用。

## 使用方法

[`Maven Central`](http://search.maven.org/#artifactdetails%7Ccom.mcxiaoke.gradle%7Cpacker-ng%7C1.0.0%7Cjar)

#### 修改项目根目录的 `build.gradle` ：

```groovy

buildscript {
    repositories {
		mavenCentral()
	}

	dependencies{
		classpath 'com.mcxiaoke.gradle:packer-ng:1.0.+'
	}
}  
```

#### 修改Android项目的 `build.gradle` :

```groovy

apply plugin: 'packer'  
```

### 多渠道打包

需要在命令行指定 -Pmarket=yourMarketFileName属性，market是你的渠道名列表文件名，market文件是基于**项目根目录**的 `相对路径` ，假设你的项目位于 `~/github/myapp` 你的market文件位于 `~/github/myapp/config/markets.txt` 那么参数应该是 `-Pmarket=config/markets.txt`，一般建议直接放在项目根目录，如果market文件参数错误或者文件不存在会抛出异常

渠道名列表文件是纯文本文件，每行一个渠道号，列表解析的时候会自动忽略空白行，但是格式不规范会报错，渠道名和注释之间用 `#` 号分割开，行示例：

```
 Google_Play#play store market
 Gradle_Test#test
 SomeMarket#some market
```

渠道打包的命令行参数格式示例（在项目根目录执行）：  

```shell
./gradlew -Pmarket=markets.txt clean archiveApkRelease
``` 

### 获取当前渠道

TODO

### Windows系统

* 如果你是在windows系统下使用，需要下载 [Gradle](http://www.gradle.org/docs/current/userguide/gradle_wrapper.html)，设置 **GRADLE_HOME** 环境变量，并且将Gradle的 **bin** 目录添加到环境变量PATH，然后将命令行中的 `./gradlew` 替换为 `gradle.bat`
* 如果同时还需要使用gradlew，你需要给你的项目配置使用gradle wrapper，在设置好了gradle之后，在你的项目根目录命令行输入 `gradle.bat wrapper` 然后就可以使用 `gradlew.bat` 了
* Windows系统下的命令行参考：
    * 使用gradle： `gradle.bat clean assembleRelease`
    * 使用gradle wrapper： `gradlew.bat clean assembleRelease`


### 文件名格式

可以使用 `archiveNameFormat` 自定义渠道打包输出的APK文件名格式，默认格式是 

`${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}` 

举例：假如你的App包名是  `com.your.company` ，渠道名是 `Google_Play` ，`buildType` 是 `release` ，`versionName` 是 `2.1.15` ，`versionCode` 是 `200115` ，那么生成的APK的文件名是 

`com.your.company-Google_Player-release-2.1.15-20015.apk` 

	
## 配置选项 

* **archiveOutput**  指定渠道打包输出的APK存放目录，默认位于`${项目根目录}/build/archives`   

* **archiveNameFormat** - `Groovy格式字符串`， 指定渠道打包输出的APK文件名格式，默认文件名格式是： `${appPkg}-${flavorName}-${buildType}-v${versionName}-${versionCode}`，可使用以下变量:  
  
  * *projectName* - 项目名字
  * *appName* - App模块名字
  * *appPkg* - `applicationId` (App包名packageName)
  * *buildType* - `buildType` (release/debug/beta等)
  * *flavorName* - `flavorName` (对应渠道打包中的渠道名字)
  * *versionName* - `versionName` (显示用的版本号)
  * *versionCode* - `versionCode` (内部版本号)
  * *buildTime* - `buildTime` (编译构建日期时间)

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

}

```

* 假设渠道列表文件位于项目根目录，文件名为 `markets.txt` ，在项目根目录打开shell运行命令：

```shell
./gradlew -Pmarket=markets.txt clean archiveApkRelease
// Windows系统下替换为：
gradle.bat -Pmarket=markets.txt clean archiveApkRelease
// 或
gradlew.bat -Pmarket=markets.txt clean archiveApkRelease
``` 
    
如果没有错误，打包完成后你可以在 `${项目根目录}/build/archives/` 目录找到最终的渠道包。说明：渠道打包的Gradle Task名字是 `archiveApk${buildType}` buildType一般是release，也可以是你自己指定的beta或者someOtherType，使用时首字母需要大写，例如release的渠道包任务名是 `archiveApkRelease`，beta的渠道包任务名是 `archiveApkBeta`，其它的以此类推


------

## 关于作者

#### 联系方式
* Blog: <http://blog.mcxiaoke.com>
* Github: <https://github.com/mcxiaoke>
* Email: [mail@mcxiaoke.com](mailto:mail@mcxiaoke.com)

#### 开源项目

* Next公共组件库: <https://github.com/mcxiaoke/Android-Next>
* Gradle渠道打包: <https://github.com/mcxiaoke/gradle-packer-plugin>
* EventBus实现xBus: <https://github.com/mcxiaoke/xBus>
* Rx文档中文翻译: <https://github.com/mcxiaoke/RxDocs>
* MQTT协议中文版: <https://github.com/mcxiaoke/mqtt>
* 蘑菇饭App: <https://github.com/mcxiaoke/minicat>
* 饭否客户端: <https://github.com/mcxiaoke/fanfouapp-opensource>
* Volley镜像: <https://github.com/mcxiaoke/android-volley>

------

## License

    Copyright 2014 - 2015 Xiaoke Zhang

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

