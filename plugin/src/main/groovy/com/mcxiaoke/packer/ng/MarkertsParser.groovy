package com.mcxiaoke.packer.ng;

import org.gradle.api.Project;

import java.io.File;
import java.util.ArrayList;
import java.util.List;

/**
 * Created by tangshuai on 2017/6/2.
 */

public class MarkertsParser {

    Project project;
    String market;

    MarkertsParser(Project project, String market) {
        this.project = project;
        this.market = market;
    }

    /**
     * parse markets file
     *
     * @return found markets file
     */
    List<String> parseMarkets() {
        List<String> markets = new ArrayList<String>();
        debug("parseMarkets()" + market)

//        if (!project.hasProperty(P_MARKET)) {
//            debug("parseMarkets() market property not found, ignore")
//            return false
//        }

        // check markets file exists
        def marketsFilePath = this.market
//        def marketsFilePath = project.property(P_MARKET).toString()
        if (!marketsFilePath) {
            println(":${project.name} markets property not found, using default")
            // if not set, use default ./markets.txt
            marketsFilePath = "markets.txt"
        }

        File file = project.rootProject.file(marketsFilePath)
        if (!file.exists() || !file.isFile() || !file.canRead()) {
            throw new IllegalArgumentException("Invalid market file: ${file.absolutePath}")
        }
        println(":${project.name} market: ${file.absolutePath}")
        markets = readMarkets(file)
        debug(":${project.name} found markets:$markets")
        return markets
    }


    List<String> readMarkets(File file) {
        // add all markets
        List<String> allMarkets = []
        file.eachLine { line, number ->
            String[] parts = line.split('#')
            if (parts && parts[0]) {
                def market = parts[0].trim()
                if (market) {
                    allMarkets.add(market)
                }
            } else {
                debug(":${project.name} skip invalid market line ${number}:'${line}'")
            }
        }
        return allMarkets
    }

    void debug(String msg) {
        project.logger.info(msg)
    }
}
