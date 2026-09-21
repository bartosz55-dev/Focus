import Foundation
import IOKit.pwr_mgt

public final class SleepManager: @unchecked Sendable {
    public static let shared = SleepManager()
    private var displayAssertionID: IOPMAssertionID = 0
    private var systemAssertionID: IOPMAssertionID = 0
    private var caffeinateProcess: Process?
    private var isPreventingSleep = false
    private let lock = NSLock()

    private init() {}

    public func preventSleep(reason: String = "Focus active video processing & rendering") {
        lock.lock()
        defer { lock.unlock() }
        guard !isPreventingSleep else { return }

        // 1. Primary: Prevent Display Sleep & Screen Lock (kIOPMAssertionTypePreventUserIdleDisplaySleep)
        let displaySuccess = IOPMAssertionCreateWithName(
            kIOPMAssertionTypePreventUserIdleDisplaySleep as CFString,
            IOPMAssertionLevel(kIOPMAssertionLevelOn),
            reason as CFString,
            &displayAssertionID
        )

        // 2. Secondary: Prevent System Sleep (kIOPMAssertionTypePreventUserIdleSystemSleep)
        let systemSuccess = IOPMAssertionCreateWithName(
            kIOPMAssertionTypePreventUserIdleSystemSleep as CFString,
            IOPMAssertionLevel(kIOPMAssertionLevelOn),
            reason as CFString,
            &systemAssertionID
        )

        // 3. Fallback: Native caffeinate process (dimsu = display, idle, disk, system, user active)
        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: "/usr/bin/caffeinate")
        proc.arguments = ["-dimsu", "-w", String(ProcessInfo.processInfo.processIdentifier)]
        try? proc.run()
        caffeinateProcess = proc

        if displaySuccess == kIOReturnSuccess || systemSuccess == kIOReturnSuccess || proc.isRunning {
            isPreventingSleep = true
        }
    }

    public func allowSleep() {
        lock.lock()
        defer { lock.unlock() }
        guard isPreventingSleep else { return }

        if displayAssertionID != 0 {
            IOPMAssertionRelease(displayAssertionID)
            displayAssertionID = 0
        }
        if systemAssertionID != 0 {
            IOPMAssertionRelease(systemAssertionID)
            systemAssertionID = 0
        }
        if let proc = caffeinateProcess, proc.isRunning {
            proc.terminate()
            caffeinateProcess = nil
        }

        isPreventingSleep = false
    }
}
