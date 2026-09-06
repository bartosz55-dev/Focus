import SwiftUI

/// Legacy compatibility wrapper forwarding to the unified SettingsView.
public struct PreferencesView: View {
    @ObservedObject var appState: AppState

    public init(appState: AppState) {
        self.appState = appState
    }

    public var body: some View {
        SettingsView(appState: appState)
    }
}
