import SwiftUI

public struct GeneratorView: View {
    @ObservedObject var appState: AppState

    public var body: some View {
        ScrollView {
            VStack(spacing: 16) {
                // Header: Dashboard Title & Mode Switcher
                HStack(alignment: .center) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Studio Dashboard")
                            .font(.system(size: 20, weight: .bold))
                        Text("High-performance character tracking & scenepack extractor")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    // Mode Switcher Pills
                    Picker("", selection: $appState.mode) {
                        ForEach(DetectionMode.allCases) { m in
                            Label(m.label, systemImage: m.icon).tag(m)
                        }
                    }
                    .pickerStyle(.segmented)
                    .frame(width: 320)
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
