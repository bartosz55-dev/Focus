import SwiftUI

public struct PreferencesView: View {
    @ObservedObject var appState: AppState

    private let standardSwatches = [
        ("Violet", "#8B5CF6"),
        ("Blue", "#2563EB"),
        ("Emerald", "#10B981"),
        ("Indigo", "#6366F1"),
        ("Rose", "#EC4899"),
        ("Orange", "#F97316"),
        ("Crimson", "#EF4444"),
        ("Amber", "#F59E0B")
    ]

    public var body: some View {
        Form {
            Section(appState.localized("appearance_theme")) {
                VStack(alignment: .leading, spacing: 8) {
                    Text(appState.localized("select_accent"))
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(.secondary)

                    HStack(spacing: 8) {
                        ForEach(standardSwatches, id: \.1) { name, hex in
                            Circle()
                                .fill(Color(hex: hex))
                                .frame(width: 24, height: 24)
                                .overlay(
                                    Circle()
                                        .stroke(Color.white, lineWidth: appState.accentColorHex.uppercased() == hex.uppercased() ? 2.5 : 0)
                                )
                                .onTapGesture {
                                    appState.accentColorHex = hex
                                }
                                .help(name)
                        }

                        ColorPicker("", selection: Binding(
                            get: { appState.accentColor },
                            set: { col in
                                if let hex = col.toHex() {
                                    appState.accentColorHex = hex
                                }
                            }
                        ))
                        .labelsHidden()
                    }
                }
                .padding(.vertical, 4)
            }

            Section(appState.localized("power_sleep")) {
                Toggle(appState.localized("sleep_toggle"), isOn: $appState.settings.preventSleep)
                Text(appState.localized("sleep_desc"))
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }

            Section(appState.localized("lang_section")) {
                Picker(appState.localized("interface_lang"), selection: $appState.currentLanguage) {
                    Text("English").tag("English")
                    Text("Polski").tag("Polski")
                    Text("Deutsch").tag("Deutsch")
                    Text("Español").tag("Español")
                    Text("Français").tag("Français")
                    Text("日本語").tag("日本語")
                }
            }

            Section(appState.localized("diagnostics_section")) {
                HStack {
                    Text("Focus for Mac (SwiftUI Native Engine)")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                    Spacer()
                    Button(appState.localized("copy_report")) {
                        let text = "Focus for Mac Diagnostic Report\nOS: macOS\nLanguage: \(appState.currentLanguage)\nAccent: \(appState.accentColorHex)\nSelected: \(appState.selectedVideoURLs.count) videos"
                        NSPasteboard.general.clearContents()
                        NSPasteboard.general.setString(text, forType: .string)
                        appState.showToast("Diagnostics copied to clipboard!", icon: "doc.on.doc")
                    }
                    .controlSize(.small)
                }
            }
        }
        .formStyle(.grouped)
        .padding(16)
        .frame(width: 480, height: 380)
    }
}
