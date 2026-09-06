import SwiftUI
import AppKit

public struct AboutAppView: View {
    @ObservedObject var appState: AppState
    var onClose: (() -> Void)? = nil

    private var appIcon: NSImage? {
        let possiblePaths = [
            Bundle.main.path(forResource: "AppIcon", ofType: "icns") ?? "",
            Bundle.main.path(forResource: "icon", ofType: "png") ?? "",
            Bundle.main.bundleURL.appendingPathComponent("Contents/Resources/AppIcon.icns").path,
            Bundle.main.bundleURL.appendingPathComponent("Contents/Resources/icon.png").path,
            "icon.png",
            "icon.icns"
        ]
        for p in possiblePaths {
            if FileManager.default.fileExists(atPath: p), let img = NSImage(contentsOfFile: p) {
                return img
            }
        }
        return NSApplication.shared.applicationIconImage
    }

    public init(appState: AppState, onClose: (() -> Void)? = nil) {
        self.appState = appState
        self.onClose = onClose
    }

    public var body: some View {
        VStack(spacing: 20) {
            // Header with App Icon
            VStack(spacing: 12) {
                if let icon = appIcon {
                    Image(nsImage: icon)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(width: 88, height: 88)
                        .shadow(color: appState.accentColor.opacity(0.35), radius: 14, x: 0, y: 6)
                } else {
                    ZStack {
                        RoundedRectangle(cornerRadius: 20, style: .continuous)
                            .fill(appState.accentColor)
                            .frame(width: 88, height: 88)
                        Image(systemName: "wand.and.stars")
                            .font(.system(size: 40))
                            .foregroundColor(.white)
                    }
                }

                VStack(spacing: 4) {
                    Text("FOCUS")
                        .font(.system(size: 26, weight: .heavy, design: .rounded))
                        .tracking(3)
                        .foregroundColor(.primary)

                    Text("Version 2.0.0 (Build 200)")
                        .font(.system(size: 12, weight: .semibold, design: .monospaced))
                        .foregroundColor(.secondary)

                    Text("macOS Native SwiftUI 6 & Apple Silicon Engine")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(appState.accentColor)
                }
            }

            // Description
            Text("High-performance AI video scenepack generator for video editors and creators. Automatically tracks anime characters and live actors, cuts scenes with dialogue awareness, and exports multi-audio timelines.")
                .font(.system(size: 12))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 24)

            // Technology Feature Pills
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                TechPill(icon: "bolt.fill", title: "Apple VideoToolbox", desc: "Hardware Accelerated NVENC/VT")
                TechPill(icon: "eye.circle.fill", title: "Dual Face AI", desc: "OpenCV Anime & Neural Real Faces")
                TechPill(icon: "waveform.badge.mic", title: "VAD Dialogue Sync", desc: "Lip-sync & MFCC voice matching")
                TechPill(icon: "power", title: "Zero-Sleep IOKit", desc: "Uninterrupted overnight processing")
            }
            .padding(.horizontal, 16)

            Divider()
                .padding(.horizontal, 20)

            // Credits & Links
            VStack(spacing: 8) {
                Text("Engineered by Bartosz5500")
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.primary)

                Text("© 2026 Bartosz5500. All rights reserved.")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)

                HStack(spacing: 12) {
                    Button(action: {
                        if let url = URL(string: "https://github.com/Bartosz5500/Focus") {
                            NSWorkspace.shared.open(url)
                        }
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "link")
                            Text("GitHub: Bartosz5500")
                        }
                        .font(.system(size: 11, weight: .medium))
                    }
                    .buttonStyle(.link)

                    if let onClose = onClose {
                        Button("Done") {
                            onClose()
                        }
                        .keyboardShortcut(.defaultAction)
                        .controlSize(.small)
                    }
                }
                .padding(.top, 4)
            }
        }
        .padding(24)
        .frame(width: 480)
        .background(.ultraThinMaterial)
    }
}

private struct TechPill: View {
    let icon: String
    let title: String
    let desc: String

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(.accentColor)
                .frame(width: 22)

            VStack(alignment: .leading, spacing: 1) {
                Text(title)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.primary)
                Text(desc)
                    .font(.system(size: 9))
                    .foregroundColor(.secondary)
                    .lineLimit(1)
            }
            Spacer()
        }
        .padding(8)
        .background(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor).opacity(0.6))
        )
    }
}
