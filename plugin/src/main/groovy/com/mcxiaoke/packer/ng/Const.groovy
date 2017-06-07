package com.mcxiaoke.packer.ng

/**
 * User: mcxiaoke
 * Date: 2017/6/2
 * Time: 12:02
 */
class Const {
    static final String HOME_PAGE = "https://github.com/mcxiaoke/packer-ng-plugin/"
    static final String PROP_CHANNELS = "channels"
    static final String PROP_OUTPUT = "output"
    static final String PROP_FORMAT = "format"

    static final String DEFAULT_OUTPUT = "archives" // in build dir

    /*
     * file name template string
     *
     * Available vars:
     * 1. projectName
     * 2. appName
     * 3. appPkg
     * 4. channel
     * 5. buildType
     * 6. versionName
     * 7. versionCode
     * 8. buildTime
     * 9. fileSHA1
     *
     * default value: '${appPkg}-${channel}-${buildType}-v${versionName}-${versionCode}'
     */
    static final String DEFAULT_FORMAT =
            '${appPkg}-${channel}-${buildType}-v${versionName}-${versionCode}'
}
