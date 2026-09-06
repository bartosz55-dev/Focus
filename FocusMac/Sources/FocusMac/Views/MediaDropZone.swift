import SwiftUI
import UniformTypeIdentifiers

public struct MediaDropZone: View {
    @ObservedObject var appState: AppState
    @State private var isVideoTargeted = false
    @State private var isImageTargeted = false
    @State private var showVideoPicker = false
    @State private var showImagePicker = false
    @State private var showSavePicker = false

    public var body: some View {
        VStack(spacing: 12) {
            // Row 1: Video selection drop zone
            HStack(spacing: 12) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(appState.localized("input_footage"))
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.secondary)

                    HStack(spacing: 12) {
                        Image(systemName: "film.stack")
                            .font(.system(size: 20))
                            .foregroundColor(appState.accentColor)
                            .frame(width: 32)

                        VStack(alignment: .leading, spacing: 2) {
                            if let first = appState.selectedVideoURLs.first {
                                if appState.selectedVideoURLs.count == 1 {
                                    Text(first.lastPathComponent)
                                        .font(.system(size: 13, weight: .semibold))
                                        .lineLimit(1)
                                } else {
                                    Text("\(appState.selectedVideoURLs.count) Videos Selected (\(first.lastPathComponent)...)")
                                        .font(.system(size: 13, weight: .semibold))
                                        .lineLimit(1)
                                }
                                Text(first.deletingLastPathComponent().path)
                                    .font(.system(size: 10))
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                            } else {
                                Text(appState.localized("drop_video"))
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                        }

                        Spacer()

                        Button("Browse...") {
                            showVideoPicker = true
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.regular)

                        if !appState.selectedVideoURLs.isEmpty {
                            Button(action: { appState.selectedVideoURLs.removeAll() }) {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundColor(.secondary)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(10)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(isVideoTargeted ? appState.accentColor.opacity(0.15) : Color(nsColor: .controlBackgroundColor).opacity(0.6))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(isVideoTargeted ? appState.accentColor : Color.white.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .onDrop(of: [.fileURL], isTargeted: $isVideoTargeted) { providers in
                        handleDrop(providers: providers, isVideo: true)
                    }
                }
            }

            // Row 2: Reference Face & Output Save Location (2-column layout)
            HStack(spacing: 12) {
                // Reference Face Card
                VStack(alignment: .leading, spacing: 6) {
                    Text(appState.localized("target_reference"))
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.secondary)

                    HStack(spacing: 10) {
                        if let imgURL = appState.referenceImageURL,
                           let nsImg = NSImage(contentsOf: imgURL) {
                            Image(nsImage: nsImg)
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                                .frame(width: 32, height: 32)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        } else if let char = appState.selectedCharacterProfile,
                                  let nsImg = NSImage(contentsOfFile: char.cropPath) {
                            Image(nsImage: nsImg)
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                                .frame(width: 32, height: 32)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        } else {
                            Image(systemName: "person.crop.circle.badge.plus")
                                .font(.system(size: 20))
                                .foregroundColor(appState.accentColor)
                                .frame(width: 32)
                        }

                        VStack(alignment: .leading, spacing: 2) {
                            if let imgURL = appState.referenceImageURL {
                                Text(imgURL.lastPathComponent)
                                    .font(.system(size: 12, weight: .medium))
                                    .lineLimit(1)
                            } else if let char = appState.selectedCharacterProfile {
                                Text("Character #\(char.id) (\(char.count) detections)")
                                    .font(.system(size: 12, weight: .medium))
                                    .lineLimit(1)
                            } else {
                                Text(appState.localized("drop_image"))
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                        }

                        Spacer()

                        Button("Select...") {
                            showImagePicker = true
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                    .padding(8)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(isImageTargeted ? appState.accentColor.opacity(0.15) : Color(nsColor: .controlBackgroundColor).opacity(0.6))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(isImageTargeted ? appState.accentColor : Color.white.opacity(0.1), lineWidth: 1)
                            )
                    )
                    .onDrop(of: [.fileURL], isTargeted: $isImageTargeted) { providers in
                        handleDrop(providers: providers, isVideo: false)
                    }
                }

                // Output Destination Card
                VStack(alignment: .leading, spacing: 6) {
                    Text(appState.localized("save_location"))
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.secondary)

                    HStack(spacing: 10) {
                        Image(systemName: "folder")
                            .font(.system(size: 18))
                            .foregroundColor(appState.accentColor)
                            .frame(width: 32)

                        VStack(alignment: .leading, spacing: 2) {
                            if let out = appState.outputURL {
                                Text(out.lastPathComponent)
                                    .font(.system(size: 12, weight: .medium))
                                    .lineLimit(1)
                            } else {
                                Text(appState.localized("auto_desktop"))
                                    .font(.system(size: 12))
                                    .foregroundColor(.secondary)
                            }
                        }

                        Spacer()

                        Button("Set...") {
                            showSavePicker = true
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                    .padding(8)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color(nsColor: .controlBackgroundColor).opacity(0.6))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.white.opacity(0.1), lineWidth: 1)
                            )
                    )
                }
            }
        }
        .fileImporter(
            isPresented: $showVideoPicker,
            allowedContentTypes: [.movie, .video, .quickTimeMovie, .mpeg4Movie],
            allowsMultipleSelection: true
        ) { result in
            if case .success(let urls) = result {
                appState.selectedVideoURLs = urls
                if let first = urls.first {
                    appState.outputURL = first.deletingLastPathComponent().appendingPathComponent("\(first.deletingPathExtension().lastPathComponent)_scenepack.mp4")
                }
            }
        }
        .fileImporter(
            isPresented: $showImagePicker,
            allowedContentTypes: [.image],
            allowsMultipleSelection: false
        ) { result in
            if case .success(let urls) = result, let first = urls.first {
                appState.referenceImageURL = first
                appState.selectedCharacterProfile = nil
            }
        }
    }

    private func handleDrop(providers: [NSItemProvider], isVideo: Bool) -> Bool {
        for provider in providers {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                guard let data = item as? Data,
                      let url = URL(dataRepresentation: data, relativeTo: nil) else { return }
                DispatchQueue.main.async {
                    if isVideo {
                        if !self.appState.selectedVideoURLs.contains(url) {
                            self.appState.selectedVideoURLs.append(url)
                            if self.appState.outputURL == nil {
                                self.appState.outputURL = url.deletingLastPathComponent().appendingPathComponent("\(url.deletingPathExtension().lastPathComponent)_scenepack.mp4")
                            }
                        }
                    } else {
                        self.appState.referenceImageURL = url
                        self.appState.selectedCharacterProfile = nil
                    }
                }
            }
        }
        return true
    }
}
