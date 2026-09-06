import SwiftUI
import AppKit

@main
struct FocusMacApp: App {

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
