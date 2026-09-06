import Foundation
import IOKit.pwr_mgt

public final class SleepManager: @unchecked Sendable {
    public static let shared = SleepManager()
    private var assertionID: IOPMAssertionID = 0
    private var isPreventingSleep = false
    private let lock = NSLock()

    private init() {}

    public func preventSleep(reason: String = "Focus active video processing") {
        lock.lock()
        defer { lock.unlock() }
        guard !isPreventingSleep else { return }

        let success = IOPMAssertionCreateWithName(
            kIOPMAssertionTypePreventUserIdleSystemSleep as CFString,
            IOPMAssertionLevel(kIOPMAssertionLevelOn),
            reason as CFString,
            &assertionID
        )
        if success == kIOReturnSuccess {
            isPreventingSleep = true
        }
    }

    public func allowSleep() {
        lock.lock()
        defer { lock.unlock() }
        guard isPreventingSleep else { return }
        IOPMAssertionRelease(assertionID)
        isPreventingSleep = false
        assertionID = 0
    }
}
