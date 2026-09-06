import SwiftUI

public struct ReviewTableView: View {
    @ObservedObject var appState: AppState

    public var totalSelectedDuration: Double {
        appState.detectedClips
            .filter { $0.isSelected }
            .reduce(0.0) { $0 + $1.duration }
    }

    public var body: some View {
        GlassCard(title: "Review Detected Clips (\(appState.detectedClips.count) found)", icon: "checklist") {
            VStack(spacing: 10) {
                // Header action bar
                HStack {
                    Button("Select All") {
                        appState.selectAllClips(true)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)

                    Button("Deselect All") {
                        appState.selectAllClips(false)
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)

                    Spacer()

                    Text("Selected: \(appState.detectedClips.filter { $0.isSelected }.count) clips (\(String(format: "%.1fs", totalSelectedDuration)))")
                        .font(.system(size: 11, weight: .semibold))
                        .foregroundColor(.secondary)

                    Button(action: {
                        appState.startRender()
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "film.fill")
                            Text("Render Selected Clips")
                        }
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.purple)
                    .controlSize(.small)
                    .disabled(appState.isProcessing || appState.detectedClips.filter { $0.isSelected }.isEmpty)
                }

                // Table of detected clips
                ScrollView {
                    LazyVStack(spacing: 6) {
                        ForEach($appState.detectedClips) { $clip in
                            ClipRowView(clip: $clip) {
                                appState.previewClip = clip
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
                .frame(maxHeight: 280)
            }
        }
    }
}

struct ClipRowView: View {
    @Binding var clip: ClipInterval
    let onPreview: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            Toggle("", isOn: $clip.isSelected)
                .labelsHidden()
                .toggleStyle(.checkbox)

            // Thumbnail
            Group {
                if !clip.thumbPath.isEmpty,
                   let nsImg = NSImage(contentsOfFile: clip.thumbPath) {
                    Image(nsImage: nsImg)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                        .frame(width: 80, height: 48)
                        .clipShape(RoundedRectangle(cornerRadius: 6))
                } else {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.white.opacity(0.08))
                        .frame(width: 80, height: 48)
                        .overlay(Image(systemName: "film").foregroundColor(.secondary))
                }
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(clip.source.isEmpty ? "Scene Clip #\(clip.id + 1)" : URL(fileURLWithPath: clip.source).lastPathComponent)
                    .font(.system(size: 11, weight: .semibold))
                    .lineLimit(1)

                HStack(spacing: 10) {
                    Text("Start: \(String(format: "%.2fs", clip.start))")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                    Text("End: \(String(format: "%.2fs", clip.end))")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            Text("\(String(format: "%.2fs", clip.duration))")
                .font(.system(size: 11, weight: .bold))
                .foregroundColor(.purple)
                .frame(width: 55, alignment: .trailing)

            Button("▶️ Preview") {
                onPreview()
            }
            .buttonStyle(.bordered)
            .controlSize(.small)
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(clip.isSelected ? Color.purple.opacity(0.08) : Color.white.opacity(0.02))
        )
    }
}
