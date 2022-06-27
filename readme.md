# Packer-NG Gradle Plugin V2

### 提示：本项目已停止新功能开发，有需要的请自行Fork修改

```
对Gradle 7.x的支持，欢迎提PR，或者Fork自己修改（2022.06.27）
```

极速渠道打包工具

- **v2.0.1 - 2018.03.23** - 支持Android Plugin 3.x和Gradle 4.x
- **v2.0.0 - 2017.06.23** - 全新发布，支持V2签名模式，包含多项优化

<!-- TOC -->

- [特别提示](#特别提示)
- [项目介绍](#项目介绍)
- [使用指南](#使用指南)
    - [修改项目配置](#修改项目配置)
    - [修改模块配置](#修改模块配置)
    - [插件配置示例](#插件配置示例)
    - [渠道列表格式](#渠道列表格式)
    - [集成打包](#集成打包)
    - [脚本打包](#脚本打包)
    - [代码中读取渠道](#代码中读取渠道)
    - [文件名格式模版](#文件名格式模版)
- [其它说明](#其它说明)
- [关于作者](#关于作者)
    - [联系方式](#联系方式)
    - [开源项目](#开源项目)
- [License](#license)

<!-- /TOC -->

## 特别提示

V2版只支持`APK Signature Scheme v2`，要求在 `signingConfigs` 里 `v2SigningEnabled true` 启用新版签名模式，如果你需要使用旧版本，看这里 [v1.0.9](https://github.com/mcxiaoke/packer-ng-plugin/tree/v1.0.9)。

## 项目介绍

[**packer-ng-plugin**](https://github.com/mcxiaoke/packer-ng-plugin) 是下一代Android渠道打包工具Gradle插件，支持极速打包，**100**个渠道包只需要**10**秒钟，速度是 [**gradle-packer-plugin**](https://github.com/mcxiaoke/gradle-packer-plugin) 的**300**倍以上，可方便的用于CI系统集成，同时提供命令行打包脚本，渠道读取提供Python和C语言的实现。

## 使用指南

[`Maven Central`](http://search.maven.org/#search%7Cga%7C1%7Ca%3A%22packer-ng%22)

### 修改项目配置

```groovy
// build.gradle
buildscript {
    dependencies{
        classpath 'com.mcxiaoke.packer-ng:plugin:2.0.1'
    }
}
```

### 修改模块配置

```groovy
apply plugin: 'packer'
// build.gradle
dependencies {
    compile 'com.mcxiaoke.packer-ng:helper:2.0.1'
}
```

**注意：`plugin` 和 `helper` 的版本号需要保持一致**

### 插件配置示例

```groovy
packer {
    archiveNameFormat = '${buildType}-v${versionName}-${channel}'
    archiveOutput = new File(project.rootProject.buildDir, "apks")
//    channelList = ['*Douban*', 'Google/', '中文/@#市场', 'Hello@World',
//                   'GradleTest', '20070601!@#$%^&*(){}:"<>?-=[];\',./']
//    channelFile = new File(project.rootDir, "markets.txt")
    channelMap = [
            "Cat" : project.rootProject.file("channels/cat.txt"),
            "Dog" : project.rootProject.file("channels/dog.txt"),
            "Fish": project.rootProject.file("channels/channels.txt")
    ]
}
```

* **archiveNameFormat** - 指定最终输出的渠道包文件名的格式模版，详细说明见后面，默认值是 `${appPkg}-${channel}-${buildType}-v${versionName}-${versionCode}` (可选)
* **archiveOutput** - 指定最终输出的渠道包的存储位置，默认值是 `${project.buildDir}/archives` (可选)
* **channelList** - 指定渠道列表，List类型，见示例
* **channelMap** - 根据productFlavor指定不同的渠道列表文件，见示例
* **channelFile** - 指定渠道列表文件，File类型，见示例

注意：`channelList` / `channelMap` / `channelFile` 不能同时使用，根据实际情况选择一种即可，三个属性同时存在时优先级为： `channelList` > `channelMap` > `channelFile `，另外，这三个属性会被命令行参数 `-Pchannels` 覆盖。

### 渠道列表格式

渠道名列表文件是纯文本文件，按行读取，每行一个渠道，行首和行尾的空白会被忽略，如果有注释，渠道名和注释之间用 `#` 分割。

渠道名建议尽量使用规范的**中英文和数字**，不要使用特殊字符和不可见字符。示例：[channels.txt](blob/v2dev/channels/channels.txt)

### 集成打包

* 项目中没有使用 `productFlavors`

    ```shell
    ./gradlew clean apkRelease
    ```

* 项目中使用了 `productFlavors`

    如果项目中指定了多个 `flavor` ，需要指定需要打渠道包的 `flavor` 名字，假设你有 `Paid` `Free` 两个 `flavor` ，打包的时候命令如下：

    ```shell
    ./gradlew clean apkPaidRelease
    ./gradlew clean apkFreeRelease
    ```

    直接使用 `./gradlew clean apkRelease` 会输出所有 `flavor` 的渠道包。

* 通过参数直接指定渠道列表(会覆盖`build.gradle`中的属性)：

    ```shell
    ./gradlew clean apkRelease -Pchannels=ch1,ch2,douban,google
    ```

    渠道数目很少时可以使用此种方式。

* 通过参数指定渠道列表文件的位置(会覆盖`build.gradle`中的属性)：

    ```shell
    ./gradlew clean apkRelease -Pchannels=@channels.txt
    ```

    使用@符号指定渠道列表文件的位置，使用相对于项目根目录的相对路径。

* 还可以指定输出目录和文件名格式模版：

    ```shell
    ./gradlew clean apkRelease -Poutput=build/apks
    ./gradlew clean apkRelease -Pformat=${versionName}-${channel}
    ```

    这些参数 `channels` `output` `format` 可以组合使用，命令行参数会覆盖 `build.gradle` 对应的属性。

* Gradle打包命令说明

    渠道打包的Task名字是 `apk${flavor}${buildType}` buildType一般是release，也可以是你自己指定的beta或者someOtherType，如果没有 `flavor` 可以忽略，使用时首字母需要大写，假设 `flavor` 是 `Paid`，`release`类型对应的任务名是 `apkPaidRelease`，`beta`类型对应的任务名是 `apkPaidBetaBeta`，其它的以此类推。

* 特别提示

    如果你同时使用其它的资源压缩工具或应用加固功能，请使用命令行脚本打包增加渠道信息，增加渠道信息需要放在APK处理过程的最后一步。

### 脚本打包

除了使用Gradle集成以外，还可以使用项目提供的Java脚本打包，Jar位于本项目的 `tools` 目录，请使用最新版，以下用 `packer-ng` 指代 `java -jar tools/packer-ng-2.0.1.jar`，下面是几个示例。

* 参数说明：

```
packer-ng - 表示 java -jar packer-ng-2.0.1.jar
channels.txt - 替换成你的渠道列表文件的实际路径
build/archives - 替换成你指定的渠道包的输出路径
app.apk - 替换成你要打渠道包的APK文件的实际路径
```

* 直接指定渠道列表打包：

```shell
packer-ng generate --channels=ch1,ch2,ch3 --output=build/archives app.apk
```

* 指定渠道列表文件打包：

```shell
packer-ng generate --channels=@channels.txt --output=build/archives app.apk
```

* 验证渠道信息：

```shell
packer-ng verify app.apk
```

* 运行命令查看帮助

```shell
java -jar tools/packer-ng-2.0.1.jar --help
```

* Python脚本读取渠道：

```shell
python tools/packer-ng-v2.py app.apk
```

* C程序读取渠道：

```shell
cd tools
make
make install
packer app.apk
```

### 代码中读取渠道

```java
// 如果没有找到渠道信息或遇到错误，默认返回的是""
// com.mcxiaoke.packer.helper.PackerNg
String channel = PackerNg.getChannel(Context)
```

### 文件名格式模版

格式模版使用Groovy字符串模版引擎，默认文件名格式是： `${appPkg}-${channel}-${buildType}-v${versionName}-${versionCode}` 。

假如你的App包名是  `com.your.company` ，渠道名是 `Google_Play` ，`buildType` 是 `release` ，`versionName` 是 `2.1.15` ，`versionCode` 是 `200115` ，那么生成的默认APK的文件名是 `com.your.company-Google_Player-release-2.1.15-20015.apk` 。

可使用以下变量:

  * *projectName* - 项目名字
  * *appName* - App模块名字
  * *appPkg* - `applicationId` (App包名packageName)
  * *channel* - 打包时指定的渠道名
  * *buildType* - `buildType` (release/debug/beta等)
  * *flavor* - `flavor` (flavor名字，如paid/free等)
  * *versionName* - `versionName` (显示用的版本号)
  * *versionCode* - `versionCode` (内部版本号)
  * *buildTime* - `buildTime` (编译构建日期时间)
  * *fileSHA1* - `fileSHA1 ` (最终APK文件的SHA1哈希值)

------

## 其它说明

渠道读取C语言实现使用 [GenericMakefile](https://github.com/mbcrawfo/GenericMakefile) 构建，[APK Signing Block](https://source.android.com/security/apksigning/v2) 读取和写入Java实现修改自 [apksig](https://android.googlesource.com/platform/tools/apksig/+/master) 和 [walle](https://github.com/Meituan-Dianping/walle/tree/master/payload_writer) ，特此致谢。


------

## 关于作者

### 联系方式
* Blog: <http://blog.mcxiaoke.com>
* Github: <https://github.com/mcxiaoke>
* Email: [packer-ng-plugin@mcxiaoke.com](mailto:packer-ng-plugin@mcxiaoke.com)

### 开源项目

* Rx文档中文翻译: <https://github.com/mcxiaoke/RxDocs>
* MQTT协议中文版: <https://github.com/mcxiaoke/mqtt>
* Awesome-Kotlin: <https://github.com/mcxiaoke/awesome-kotlin>
* Kotlin-Koi: <https://github.com/mcxiaoke/kotlin-koi>
* Next公共组件库: <https://github.com/mcxiaoke/Android-Next>
* Gradle渠道打包: <https://github.com/mcxiaoke/gradle-packer-plugin>
* EventBus实现xBus: <https://github.com/mcxiaoke/xBus>
* 蘑菇饭App: <https://github.com/mcxiaoke/minicat>

------

## License

    Copyright 2014 - 2021 Xiaoke Zhang

    Licensed under the Apache License, Version 2.0 (the "License");
    you may not use this file except in compliance with the License.
    You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

    Unless required by applicable law or agreed to in writing, software
    distributed under the License is distributed on an "AS IS" BASIS,
    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
    See the License for the specific language governing permissions and
    limitations under the License.

