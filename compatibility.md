# 兼容性问题

------

 	更新时间：2016.08.05
 
## APK signature scheme v2

- **使用最新版SDK(Android Gradle Plugin 2.2.0+)时，请务必在 `signingConfigs` 里加入 `v2SigningEnabled false` ，否则打包时会报错**

```groovy
apply plugin: 'packer' 

dependencies {
	compile 'com.mcxiaoke.gradle:packer-helper:1.0.8'
} 

 android {
    //...
    signingConfigs {
      release {
      	// 如果要支持最新版的系统 Android 7.0
      	// 这一行必须加，否则安装时会提示没有签名
      	// 作用是只使用旧版签名，禁用V2版签名模式
        v2SigningEnabled false 
      }
    }
  }
```

为了提高Android系统的安全性，Google从Android 7.0开始增加一种新的增强签名模式，从`Android Gradle Plugin 2.2.0`开始，构建系统在打包应用后签名时默认使用`APK signature scheme v2`，该模式在原有的签名模式上，增加校验APK的SHA256哈希值，如果签名后对APK作了任何修改，安装时会校验失败，提示没有签名无法安装，使用本工具修改的APK会无法安装，**解决办法是在 `signingConfigs` 里增加 `v2SigningEnabled false`** ，禁用新版签名模式，技术细节请看官方文档：[APK signature scheme v2](https://developer.android.com/preview/api-overview.html#apk_signature_v2)，还有这里 [Issue 31](https://github.com/mcxiaoke/packer-ng-plugin/issues/31) 的讨论 。
