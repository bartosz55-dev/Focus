import SwiftUI

public struct MainWindowView: View {
    @StateObject var appState = AppState()

    public init() {}

    public var body: some View {
        HStack(spacing: 0) {
            SidebarView(appState: appState)

            Divider()

            ZStack(alignment: .top) {
                // Detail view based on tab with smooth crossfade
                Group {
                    switch appState.currentTab {
                    case .generator:
                        GeneratorView(appState: appState)
                    case .gallery:
                        CharacterGalleryView(appState: appState)
                    case .settings:
                        SettingsView(appState: appState)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .transition(.opacity.combined(with: .scale(scale: 0.995)))

                // Floating Toast Banner
                if let msg = appState.toastMessage {
                    ToastBanner(message: msg, icon: appState.toastIcon, accentColor: appState.accentColor)
                        .padding(.top, 16)
                        .transition(.asymmetric(
                            insertion: .move(edge: .top).combined(with: .opacity),
                            removal: .opacity
                        ))
                }
            }
        }
        .frame(minWidth: 900, minHeight: 650)
        .preferredColorScheme(appState.preferredColorScheme)
        .sheet(item: $appState.previewClip) { clip in
            if let video = appState.selectedVideoURLs.first {
                NativeVideoPlayerView(clip: clip, videoURL: video) {
                    appState.previewClip = nil
                }
            }
        }
        .sheet(isPresented: $appState.showAboutSheet) {
            AboutAppView(appState: appState) {
                appState.showAboutSheet = false
            }
        }
    }
}
