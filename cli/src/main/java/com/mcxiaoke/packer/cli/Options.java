/*
 * Copyright (C) 2016 The Android Open Source Project
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

package com.mcxiaoke.packer.cli;

import java.util.Arrays;

/**
 * Parser of command-line options/switches/flags.
 * <p>
 * <p>Supported option formats:
 * <ul>
 * <li>{@code --name value}</li>
 * <li>{@code --name=value}</li>
 * <li>{@code -name value}</li>
 * <li>{@code --name} (boolean options only)</li>
 * </ul>
 * <p>
 * <p>To use the parser, create an instance, providing it with the command-line parameters, then
 * iterate over options by invoking {@link #nextOption()} until it returns {@code null}.
 */
class Options {
    private final String[] params;
    private int index;
    private String lastOptionValue;
    private String lastOptionOriginalForm;

    /**
     * Constructs a new {@code OptionsParser} initialized with the provided command-line.
     */
    public Options(String[] params) {
        this.params = params.clone();
    }

    /**
     * Returns the name (without leading dashes) of the next option (starting with the very first
     * option) or {@code null} if there are no options left.
     * <p>
     * <p>The value of this option can be obtained via {@link #getRequiredValue(String)},
     * {@link #getRequiredIntValue(String)}, and {@link #getOptionalBooleanValue(boolean)}.
     */
    public String nextOption() {
        if (index >= params.length) {
            // No more parameters left
            return null;
        }
        String param = params[index];
        if (!param.startsWith("-")) {
            // Not an option
            return null;
        }

        index++;
        lastOptionOriginalForm = param;
        lastOptionValue = null;
        if (param.startsWith("--")) {
            // FORMAT: --name value OR --name=value
            if ("--".equals(param)) {
                // End of options marker
                return null;
            }
            int valueDelimiterIndex = param.indexOf('=');
            if (valueDelimiterIndex != -1) {
                lastOptionValue = param.substring(valueDelimiterIndex + 1);
                lastOptionOriginalForm = param.substring(0, valueDelimiterIndex);
                return param.substring("--".length(), valueDelimiterIndex);
            } else {
                return param.substring("--".length());
            }
        } else {
            // FORMAT: -name value
            return param.substring("-".length());
        }
    }

    /**
     * Returns the original form of the current option. The original form includes the leading dash
     * or dashes. This is intended to be used for referencing the option in error messages.
     */
    public String getOptionOriginalForm() {
        return lastOptionOriginalForm;
    }

    /**
     * Returns the value of the current option, throwing an exception if the value is missing.
     */
    public String getRequiredValue(String valueDescription) throws OptionsException {
        if (lastOptionValue != null) {
            String result = lastOptionValue;
            lastOptionValue = null;
            return result;
        }
        if (index >= params.length) {
            // No more parameters left
            throw new OptionsException(
                    valueDescription + " missing after " + lastOptionOriginalForm);
        }
        String param = params[index];
        if ("--".equals(param)) {
            // End of options marker
            throw new OptionsException(
                    valueDescription + " missing after " + lastOptionOriginalForm);
        }
        index++;
        return param;
    }

    /**
     * Returns the value of the current numeric option, throwing an exception if the value is
     * missing or is not numeric.
     */
    public int getRequiredIntValue(String valueDescription) throws OptionsException {
        String value = getRequiredValue(valueDescription);
        try {
            return Integer.parseInt(value);
        } catch (NumberFormatException e) {
            throw new OptionsException(
                    valueDescription + " (" + lastOptionOriginalForm
                            + ") must be a decimal number: " + value);
        }
    }

    /**
     * Gets the value of the current boolean option. Boolean options are not required to have
     * explicitly specified values.
     */
    public boolean getOptionalBooleanValue(boolean defaultValue) throws OptionsException {
        if (lastOptionValue != null) {
            // --option=value form
            String stringValue = lastOptionValue;
            lastOptionValue = null;
            if ("true".equals(stringValue)) {
                return true;
            } else if ("false".equals(stringValue)) {
                return false;
            }
            throw new OptionsException(
                    "Unsupported value for " + lastOptionOriginalForm + ": " + stringValue
                            + ". Only true or false supported.");
        }

        // --option (true|false) form OR just --option
        if (index >= params.length) {
            return defaultValue;
        }

        String stringValue = params[index];
        if ("true".equals(stringValue)) {
            index++;
            return true;
        } else if ("false".equals(stringValue)) {
            index++;
            return false;
        } else {
            return defaultValue;
        }
    }

    /**
     * Returns the remaining command-line parameters. This is intended to be invoked once
     * {@link #nextOption()} returns {@code null}.
     */
    public String[] getRemainingParams() {
        if (index >= params.length) {
            return new String[0];
        }
        String param = params[index];
        if ("--".equals(param)) {
            // Skip end of options marker
            return Arrays.copyOfRange(params, index + 1, params.length);
        } else {
            return Arrays.copyOfRange(params, index, params.length);
        }
    }

    /**
     * Indicates that an error was encountered while parsing command-line options.
     */
    public static class OptionsException extends Exception {
        private static final long serialVersionUID = 1L;

        public OptionsException(String message) {
            super(message);
        }
    }
}
