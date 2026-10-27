//
//  AppleScriptXCTestCase.swift
//  NetNewsWireUITests
//
//  Created by Olof Hellman on 2/10/18.
//  Copyright © 2018 Ranchero Software. All rights reserved.
//

import XCTest

class AppleScriptXCTestCase: XCTestCase {
    enum ScriptFixtureError: Error {
        case invalidHost, missingSource, invalidSource
    }

    private let targetedFixtures: Set<String> = [
        "testFeedExists", "testGetURL", "testNameAndUrlOfEveryFeed",
        "testNameOfAuthors", "testNameOfEveryFolder"
    ]
    private let hostMarker = "__TEST_HOST_BUNDLE_ID__"

    func currentTestHostID() throws -> String {
        guard let hostID = Bundle.main.bundleIdentifier,
              hostID.range(of: #"^[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)+$"#, options: .regularExpression) != nil else {
            throw ScriptFixtureError.invalidHost
        }
        #if NNW_ACCEPTANCE_TESTS
        guard hostID == "org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG" else {
            throw ScriptFixtureError.invalidHost
        }
        #endif
        return hostID
    }

    func bindScriptSource(_ source: String, filename: String, hostID: String) throws -> String {
        guard hostID.range(of: #"^[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)+$"#, options: .regularExpression) != nil,
              !source.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            throw ScriptFixtureError.invalidSource
        }
        let markerCount = source.components(separatedBy: hostMarker).count - 1
        let applicationCount = try NSRegularExpression(pattern: #"\bapplication\b"#, options: .caseInsensitive)
            .numberOfMatches(in: source, range: NSRange(source.startIndex..., in: source))
        if targetedFixtures.contains(filename) {
            guard markerCount == 1, applicationCount == 1,
                  source.contains("tell application id \"\(hostMarker)\"") else {
                throw ScriptFixtureError.invalidSource
            }
            return source.replacingOccurrences(of: hostMarker, with: hostID)
        }
        guard filename == "testGenericScript", markerCount == 0, applicationCount == 0 else {
            throw ScriptFixtureError.invalidSource
        }
        return source
    }

    func scriptSource(filename: String, hostID: String) throws -> String {
        guard let url = Bundle(for: type(of: self)).url(forResource: filename, withExtension: "txt"),
              let source = try? String(contentsOf: url, encoding: .utf8) else {
            throw ScriptFixtureError.missingSource
        }
        return try bindScriptSource(source, filename: filename, hostID: hostID)
    }

    /*
        @function doIndividualScript
        @param filename -- name of a raw script resource in the test bundle
        @brief  given a file, loads the script and runs it.  Expects a result from running
                the script of the form
                     {test_result:true, script_result:<anything>}
                if the test_result is false or is missing, the test fails
        @return  the value of script_result, if any
    */
    func doIndividualScript(filename: String) -> NSAppleEventDescriptor? {
        let testScript: NSAppleScript
        do {
            let hostID = try currentTestHostID()
            let source = try scriptSource(filename: filename, hostID: hostID)
            guard let script = NSAppleScript(source: source) else {
                throw ScriptFixtureError.invalidSource
            }
            testScript = script
        } catch {
            XCTFail("Cannot bind script fixture \(filename): \(error)")
            return nil
        }

        var errorDict: NSDictionary?
        let scriptResult = testScript.executeAndReturnError(&errorDict)
        if errorDict != nil {
            print("error is \(String(describing: errorDict))")
            XCTFail("Failed executing script")
            return nil
        }

        let usrfDictionary = scriptResult.usrfDictionary()
        guard let testResult = usrfDictionary["test_result"] else {
            XCTFail("test script didn't return test result in usrf")
            return nil
        }

        if !testResult.booleanValue {
            print("test_result was \(testResult)")
            print("script_result was \(String(describing: usrfDictionary["script_result"]))")
        }

        XCTAssert(testResult.booleanValue == true, "test_result should be true")
        return usrfDictionary["script_result"]
    }
}
