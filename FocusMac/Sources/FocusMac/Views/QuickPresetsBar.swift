import SwiftUI

public struct QuickPresetsBar: View {
    @ObservedObject var appState: AppState
    @State private var showSaveSheet = false
    @State private var newPresetName = ""
    @State private var selectedPreset = "Presets..."

    public var body: some View {
        HStack(spacing: 8) {
            Text(appState.localized("quick_presets"))
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.secondary)

            // Built-in smart presets
            Button(appState.localized("preset_tiktok")) {
                applyTikTokPreset()
            }
            .buttonStyle(.bordered)
            .controlSize(.small)

            Button(appState.localized("preset_youtube")) {
                applyYouTubePreset()
            }
            .buttonStyle(.bordered)
            .controlSize(.small)

            Button(appState.localized("preset_draft")) {
                applyDraftPreset()
            }
            .buttonStyle(.bordered)
            .controlSize(.small)

            Divider()
                .frame(height: 16)

            // Custom user presets menu
            Menu {
                if appState.customPresets.isEmpty {
                    Text("No custom presets saved")
                } else {
                    ForEach(appState.customPresets, id: \.self) { name in
                        Button("👤 \(name)") {
                            selectedPreset = name
                            appState.applyPreset(name: name)
                        }
                    }
                }
            } label: {
                HStack(spacing: 4) {
                    Text(selectedPreset == "Presets..." ? appState.localized("custom_presets") : "👤 \(selectedPreset)")
                        .font(.system(size: 11, weight: .medium))
                    Image(systemName: "chevron.up.chevron.down")
                        .font(.system(size: 9))
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color(nsColor: .controlBackgroundColor))
                )
            }
            .menuStyle(.borderlessButton)
            .controlSize(.small)
            .onAppear {
                appState.refreshPresets()
            }

            // Save new preset button
            Button(action: {
                newPresetName = ""
                showSaveSheet = true
            }) {
                Image(systemName: "plus.circle")
                    .foregroundColor(appState.accentColor)
            }
            .buttonStyle(.borderless)
            .help("Save current settings as a custom preset")

            // Delete selected preset button
            if selectedPreset != "Presets..." {
                Button(action: {
                    PresetManager.deletePreset(name: selectedPreset)
                    appState.refreshPresets()
                    selectedPreset = "Presets..."
                    appState.showToast("Preset deleted.", icon: "trash")
                }) {
                    Image(systemName: "trash")
                        .foregroundColor(.red.opacity(0.8))
                }
                .buttonStyle(.borderless)
                .help("Delete selected custom preset")
            }

            Spacer()
        }
        .padding(.horizontal, 4)
        .sheet(isPresented: $showSaveSheet) {
            VStack(spacing: 16) {
                Text("Save Custom Preset")
                    .font(.system(size: 15, weight: .bold))

                TextField("Preset Name (e.g. Action Anime)", text: $newPresetName)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 260)

                HStack(spacing: 12) {
                    Button("Cancel") {
                        showSaveSheet = false
                    }
                    .keyboardShortcut(.cancelAction)

                    Button("Save") {
                        if !newPresetName.trimmingCharacters(in: .whitespaces).isEmpty {
                            PresetManager.savePreset(name: newPresetName.trimmingCharacters(in: .whitespaces), settings: appState.settings)
                            appState.refreshPresets()
                            selectedPreset = newPresetName
                            appState.showToast("Preset '\(newPresetName)' saved!", icon: "square.and.arrow.down")
                            showSaveSheet = false
                        }
                    }
                    .keyboardShortcut(.defaultAction)
                    .buttonStyle(.borderedProminent)
                    .tint(appState.accentColor)
                }
            }
            .padding(24)
            .frame(width: 320)
        }
    }

    private func applyTikTokPreset() {
        appState.settings.aspect = .verticalAutoTrack
        appState.settings.padBefore = 1.5
        appState.settings.padAfter = 1.5
        appState.settings.minScene = 1.0
        appState.settings.frameSkip = 12
        appState.showToast("Applied Preset: 📱 TikTok / Shorts (9:16)", icon: "iphone")
    }

    private func applyYouTubePreset() {
        appState.settings.aspect = .original
        appState.settings.padBefore = 2.0
        appState.settings.padAfter = 2.0
        appState.settings.minScene = 1.5
        appState.settings.frameSkip = 15
        appState.showToast("Applied Preset: 🎬 YouTube (16:9)", icon: "play.rectangle")
    }

    private func applyDraftPreset() {
        appState.settings.aspect = .original
        appState.settings.padBefore = 1.0
        appState.settings.padAfter = 1.0
        appState.settings.minScene = 0.8
        appState.settings.frameSkip = 30
        appState.showToast("Applied Preset: ⚡ Ultra-Fast Draft", icon: "bolt")
    }
}
