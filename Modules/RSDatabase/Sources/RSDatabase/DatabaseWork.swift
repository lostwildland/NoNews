import Foundation
import Synchronization

/// Identifies work admitted by an account before its shutdown began.
public final class DatabaseWork: Sendable {
	@TaskLocal public static var current: DatabaseWork?
	public let accountID: String
	private let active = Mutex(true)
	public var isActive: Bool { active.withLock { $0 } }
	public init(accountID: String) { self.accountID = accountID }
	public func finish() { active.withLock { $0 = false } }
}
