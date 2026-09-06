import SwiftUI

public struct PreferencesView: View {
    @ObservedObject var appState: AppState
    @AppStorage("accentColorHex") private var accentColorHex = "#8B5CF6"
    @AppStorage("appLanguage") private var appLanguage = "English"

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
            Section("Appearance & Accent Theme") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Select Accent Color")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(.secondary)

                    HStack(spacing: 8) {
                        ForEach(standardSwatches, id: \.1) { name, hex in
                            Circle()
                                .fill(Color(hex: hex))
                                .frame(width: 24, height: 24)
                                .overlay(
                                    Circle()
                                        .stroke(Color.white, lineWidth: accentColorHex.uppercased() == hex.uppercased() ? 2 : 0)
                                )
                                .onTapGesture {
                                    accentColorHex = hex
                                }
                                .help(name)
                        }

                        ColorPicker("", selection: Binding(
                            get: { Color(hex: accentColorHex) },
                            set: { col in
                                if let hex = col.toHex() {
                                    accentColorHex = hex
                                }
                            }
                        ))
                        .labelsHidden()
                    }
                }
                .padding(.vertical, 4)
            }

            Section("Power & System Sleep") {
                Toggle("Inhibit system & display sleep during active video jobs", isOn: $appState.settings.preventSleep)
                Text("Keeps your Mac awake while scanning or rendering long video scenepacks.")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }

            Section("Language & Localization") {
                Picker("Interface Language", selection: $appLanguage) {
                    Text("English").tag("English")
                    Text("Polski").tag("Polski")
                    Text("Deutsch").tag("Deutsch")
                    Text("Español").tag("Español")
                    Text("Français").tag("Français")
                    Text("日本語").tag("日本語")
                }
            }

            Section("Diagnostics & Logs") {
                HStack {
                    Text("Focus for Mac (SwiftUI Native Engine)")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                    Spacer()
                    Button("Copy Diagnostic Report") {
                        let text = "Focus for Mac Diagnostic Report\nOS: macOS\nSelected: \(appState.selectedVideoURLs.count) videos"
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

extension Color {
    init(hex: String) {
        let cleanHex = hex.trimmingCharacters(in: CharacterSet.alphanumerics.inverted)
        var int: UInt64 = 0
        Scanner(string: cleanHex).scanHexInt64(&int)
        let r, g, b: Double
        switch cleanHex.count {
        case 6:
            r = Double((int >> 16) & 0xFF) / 255.0
            g = Double((int >> 8) & 0xFF) / 255.0
            b = Double(int & 0xFF) / 255.0
        default:
            r = 0.5; g = 0.5; b = 0.5
        }
        self.init(red: r, green: g, blue: b)
    }

    func toHex() -> String? {
        guard let components = NSColor(self).usingColorSpace(.deviceRGB) else { return nil }
        let r = Int(components.redComponent * 255.0)
        let g = Int(components.greenComponent * 255.0)
        let b = Int(components.blueComponent * 255.0)
        return String(format: "#%02X%02X%02X", r, g, b)
    }
}
