//
//  ScriptingTests.swift
//  NetNewsWireTests
//
//  Created by Olof Hellman on 1/7/18.
//  Copyright © 2018 Olof Hellman. All rights reserved.
//

import XCTest

@MainActor final class ScriptingTests: AppleScriptXCTestCase {
    func testFixtureSourcesBindToCurrentHost() throws {
        let hostID = try currentTestHostID()
        print("Scripting fixture host: \(hostID)")
        #if NNW_ACCEPTANCE_TESTS
        XCTAssertEqual(hostID, "org.nonews.acceptance.NetNewsWire-Evergreen-DEBUG")
        #endif
        for filename in ["testFeedExists", "testGetURL", "testNameAndUrlOfEveryFeed", "testNameOfAuthors", "testNameOfEveryFolder"] {
            let source = try scriptSource(filename: filename, hostID: hostID)
            XCTAssertTrue(source.contains("tell application id \"\(hostID)\""), filename)
            XCTAssertFalse(source.contains("__TEST_HOST_BUNDLE_ID__"), filename)
            XCTAssertFalse(source.contains("tell application \"NetNewsWire\""), filename)
        }
        let generic = try scriptSource(filename: "testGenericScript", hostID: hostID)
        XCTAssertTrue(generic.contains("Geoducks!"))
        XCTAssertFalse(generic.contains("tell application"))
        XCTAssertThrowsError(try bindScriptSource("tell application \"NetNewsWire\"", filename: "testFeedExists", hostID: hostID))
        XCTAssertThrowsError(try bindScriptSource("tell application id \"__TEST_HOST_BUNDLE_ID__\"", filename: "testFeedExists", hostID: "bad\"id"))
        XCTAssertThrowsError(try scriptSource(filename: "missing", hostID: hostID))
    }

    /*
        @function testGenericScript
        @brief  An example of how a script can be run as part of an XCTest
                the applescript returns 
                     {test_result:true, script_result:"Geoducks!"}
                doIndividualScript() verifies the test_result portion
                this code verifies the script_result portion
    */
    func testGenericScript() {
        let scriptResult = doIndividualScript(filename: "testGenericScript")
        XCTAssert(scriptResult?.stringValue == "Geoducks!")
    }

    func testGetUrlScript() {
        _ = doIndividualScript(filename: "testGetURL")
    }

    func testNameAndUrlOfEveryFeedScript() {
        _ = doIndividualScript(filename: "testNameAndUrlOfEveryFeed")
    }

    func testNameOfEveryFolderScript() {
        _ = doIndividualScript(filename: "testNameOfEveryFolder")
    }

    func testNameOfAuthorsScript() {
        _ = doIndividualScript(filename: "testNameOfAuthors")
    }

    func testFeedExists() {
        _ = doIndividualScript(filename: "testFeedExists")
    }

    func doIndividualScriptWithExpectation(filename: String) {
        let scriptExpectation = self.expectation(description: filename+"expectation")
		DispatchQueue.main.async {
             _ = self.doIndividualScript(filename: filename)
             scriptExpectation.fulfill()
        }
        self.wait(for: [scriptExpectation], timeout: 60)
    }
}
