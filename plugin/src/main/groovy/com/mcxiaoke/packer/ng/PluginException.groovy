package com.mcxiaoke.packer.ng

import org.gradle.api.GradleException

/**
 * User: mcxiaoke
 * Date: 2017/6/5
 * Time: 15:29
 */
class PluginException extends GradleException {
    PluginException() {
//        super("See docs on ${Const.HOME_PAGE}")
        super()
    }

    PluginException(final String message) {
        super(message)
    }

    PluginException(final String message, final Throwable cause) {
        super(message, cause)
    }
}
