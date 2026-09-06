import SwiftUI

public struct MainWindowView: View {
    @StateObject var appState = AppState()

    public init() {}

    public var body: some View {
        HStack(spacing: 0) {
            SidebarView(appState: appState)

            Divider()

            ZStack(alignment: .top) {
                // Detail view based on tab
                Group {
                    switch appState.currentTab {
                    case .generator:
                        GeneratorView(appState: appState)
                    case .gallery:
                        CharacterGalleryView(appState: appState)
                    case .settings:
                        PreferencesView(appState: appState)
                    case .logs:
                        DiagnosticsLogView(appState: appState)
                    }
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)

                // Floating Toast Banner
                if let msg = appState.toastMessage {
                    ToastBanner(message: msg, icon: appState.toastIcon)
                        .padding(.top, 16)
                }
            }
        }
        .frame(minWidth: 880, minHeight: 640)
        .sheet(item: $appState.previewClip) { clip in
            if let video = appState.selectedVideoURLs.first {
                NativeVideoPlayerView(clip: clip, videoURL: video) {
                    appState.previewClip = nil
                }
            }
        }
    }
}

struct DiagnosticsLogView: View {
    @ObservedObject var appState: AppState

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Diagnostics & Processing Logs")
                    .font(.system(size: 16, weight: .bold))
                Spacer()
                Button("Copy All Logs") {
                    let all = appState.logLines.joined(separator: "\n")
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(all, forType: .string)
                    appState.showToast("Logs copied to clipboard!", icon: "doc.on.doc")
                }
                .controlSize(.small)
            }

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 2) {
                        ForEach(appState.logLines.indices, id: \.self) { idx in
                            Text(appState.logLines[idx])
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(.green.opacity(0.85))
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .id(idx)
                        }
                    }
                    .padding(10)
                }
                .background(Color.black.opacity(0.85))
                .cornerRadius(8)
                .onChange(of: appState.logLines.count) { _ in
                    if let last = appState.logLines.indices.last {
                        proxy.scrollTo(last, anchor: .bottom)
                    }
                }
            }
        }
        .padding(16)
    }
}
