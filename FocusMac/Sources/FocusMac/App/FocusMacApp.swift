import SwiftUI
import AppKit

@main
struct FocusMacApp: App {
    var body: some Scene {
        WindowGroup {
            MainWindowView()
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)
        .commands {
            SidebarCommands()
            CommandGroup(replacing: .appInfo) {
                Button("About Focus") {
                    let credits = NSMutableAttributedString(string: "High-Performance AI Scenepack Generator & Video Studio\nNative Apple Silicon & Intel Engine\nEngineered by Bartosz5500\n\nhttps://github.com/Bartosz5500/Focus")
                    NSApplication.shared.orderFrontStandardAboutPanel(options: [
                        .applicationName: "Focus",
                        .version: "2.0.0",
                        .applicationVersion: "200",
                        NSApplication.AboutPanelOptionKey(rawValue: "Copyright"): "© 2026 Bartosz5500. All rights reserved.",
                        .credits: credits
                    ])
                }
            }
        }
    }
}
