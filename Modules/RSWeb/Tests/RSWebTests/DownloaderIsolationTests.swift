import Foundation
import Testing
import RSCore
@testable import RSWeb

@MainActor struct DownloaderIsolationTests {
	@Test func concurrentScopesDoNotShareDownloadsOrCachedResponses() async throws {
		try #require(Platform.isRunningUnitTests)
		let url = try #require(URL(string: "https://fixture.invalid/\(UUID().uuidString)"))
		async let first = download(url, testID: UUID().uuidString, body: "First")
		async let second = download(url, testID: UUID().uuidString, body: "Second")
		_ = try await (first, second)
	}

	private func download(_ url: URL, testID: String, body: String) async throws {
		try await TestingURLProtocol.$currentTestID.withValue(testID) {
			defer { TestingURLProtocol.endTest(withID: testID) }
			TestingURLProtocol.setResponse(.init(statusCode: 200, data: Data(body.utf8)), forURLContaining: url.absoluteString)
			let first = try await Downloader.shared.download(url)
			let cached = try await Downloader.shared.download(url)
			#expect(first.data == Data(body.utf8))
			#expect(cached.data == Data(body.utf8))
			#expect(!first.returnedFromCache)
			#expect(cached.returnedFromCache)
			#expect(TestingURLProtocol.requestCount(forURLContaining: url.absoluteString) == 1)
		}
	}
}
