import SwiftUI
import AppKit

public struct GeneratorView: View {
    @ObservedObject var appState: AppState

    public var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Header: Dashboard Title, Floating Liquid Glass Toolbar & Mode Switcher
                HStack(alignment: .center, spacing: 12) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text(appState.localized("studio_title"))
                            .font(.system(size: 20, weight: .bold))
                        Text(appState.localized("studio_subtitle"))
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    // Floating Liquid Glass Action Capsule (Apple HIG style)
                    LiquidGlassCapsule {
                        HStack(spacing: 2) {
                            LiquidGlassButton(
                                icon: "folder.badge.gearshape",
                                title: nil,
                                tooltip: appState.currentLanguage == "Polski" ? "Pokaż w Finderze" : "Reveal Folder in Finder",
                                isActive: false,
                                accentColor: appState.accentColor
                            ) {
                                if let url = appState.outputURL {
                                    NSWorkspace.shared.activateFileViewerSelecting([url])
                                } else if let first = appState.selectedVideoURLs.first {
                                    NSWorkspace.shared.activateFileViewerSelecting([first.deletingLastPathComponent()])
                                } else {
                                    appState.showToast("No media folder selected yet", icon: "folder")
                                }
                            }

                            LiquidGlassButton(
                                icon: "arrow.counterclockwise",
                                title: nil,
                                tooltip: appState.currentLanguage == "Polski" ? "Wyczyść zaznaczenie" : "Clear Media Selection",
                                isActive: false,
                                accentColor: appState.accentColor
                            ) {
                                withAnimation(.spring(response: 0.28, dampingFraction: 0.8)) {
                                    appState.selectedVideoURLs.removeAll()
                                    appState.referenceImageURL = nil
                                    appState.detectedClips.removeAll()
                                }
                                appState.showToast("Media selection cleared", icon: "trash")
                            }

                            LiquidGlassButton(
                                icon: "info.circle",
                                title: nil,
                                tooltip: appState.currentLanguage == "Polski" ? "O programie Focus" : "About Focus",
                                isActive: false,
                                accentColor: appState.accentColor
                            ) {
                                appState.showAboutSheet = true
                            }
                        }
                    }

                    // Native Mode Switch Toggle
                    ModeSwitchView(appState: appState)
                }
                .padding(.horizontal, 4)

                // 1. Quick Presets Toolbar
                QuickPresetsBar(appState: appState)

                // 2. Media Drop Zone & Reference
                MediaDropZone(appState: appState)

                // 3. Scene & Detection Tuning
                TuningSectionView(appState: appState)

                // 4. Progress & Primary Action Card
                ProgressCardView(appState: appState)

                // 5. Review Checklist (Visible after scan)
                if !appState.detectedClips.isEmpty {
                    ReviewTableView(appState: appState)
                        .transition(.move(edge: .bottom).combined(with: .opacity))
                }
            }
            .padding(16)
        }
    }
}
