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
                    let credits = NSMutableAttributedString(string: "High-Performance AI Scenepack Generator & Video Studio\nNative Apple Silicon & Intel Engine\nDesigned & Engineered by Bartosz Kwiatkowski\n\nhttps://github.com/bartosz55-dev/Focus")
                    NSApplication.shared.orderFrontStandardAboutPanel(options: [
                        .applicationName: "Focus",
                        .version: "2.0.0",
                        .applicationVersion: "200",
                        NSApplication.AboutPanelOptionKey(rawValue: "Copyright"): "© 2026 Bartosz Kwiatkowski. All rights reserved.",
                        .credits: credits
                    ])
                }
            }
        }
    }
}
