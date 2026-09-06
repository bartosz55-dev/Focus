import SwiftUI
import AppKit

final class AppDelegate: NSObject, NSApplicationDelegate {
    func applicationDidFinishLaunching(_ notification: Notification) {
        setupDockIcon()
    }

    private func setupDockIcon() {
        var possiblePaths: [String] = []
        if let p1 = Bundle.main.path(forResource: "AppIcon", ofType: "icns") { possiblePaths.append(p1) }
        if let p2 = Bundle.main.path(forResource: "icon", ofType: "png") { possiblePaths.append(p2) }
        possiblePaths.append(Bundle.main.bundleURL.appendingPathComponent("Contents/Resources/AppIcon.icns").path)
        possiblePaths.append(Bundle.main.bundleURL.appendingPathComponent("Contents/Resources/icon.png").path)

        for path in possiblePaths {
            if FileManager.default.fileExists(atPath: path), let img = NSImage(contentsOfFile: path) {
                NSApplication.shared.applicationIconImage = img
                break
            }
        }
    }
}

@main
struct FocusMacApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) var appDelegate

    var body: some Scene {
        WindowGroup {
            MainWindowView()
                .preferredColorScheme(.dark)
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)
        .commands {
            SidebarCommands()
        }
    }
}
