import SwiftUI
import UniformTypeIdentifiers
import AppKit

public struct MediaDropZone: View {
    @ObservedObject var appState: AppState
    @State private var isVideoTargeted = false
    @State private var isImageTargeted = false

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
                            chooseVideoSource()
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
                            .fill(isVideoTargeted ? appState.accentColor.opacity(0.15) : Color.primary.opacity(0.04))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(isVideoTargeted ? appState.accentColor : Color.primary.opacity(0.08), lineWidth: 1)
                            )
                    )
                    .onTapGesture {
                        chooseVideoSource()
                    }
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
                        if !appState.referenceImageURLs.isEmpty,
                           let first = appState.referenceImageURLs.first,
                           let nsImg = NSImage(contentsOf: first) {
                            Image(nsImage: nsImg)
                                .resizable()
                                .aspectRatio(contentMode: .fill)
                                .frame(width: 32, height: 32)
                                .clipShape(RoundedRectangle(cornerRadius: 6))
                        } else if let imgURL = appState.referenceImageURL,
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
                            if appState.referenceImageURLs.count > 1 {
                                Text("\(appState.referenceImageURLs.count) Reference Faces")
                                    .font(.system(size: 12, weight: .medium))
                                    .lineLimit(1)
                                Text(appState.referenceImageURLs.map { $0.lastPathComponent }.joined(separator: ", "))
                                    .font(.system(size: 10))
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                            } else if let imgURL = appState.referenceImageURL {
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

                        if !appState.referenceImageURLs.isEmpty || appState.referenceImageURL != nil || appState.selectedCharacterProfile != nil {
                            Button(action: {
                                chooseReferenceImage(append: true)
                            }) {
                                Image(systemName: "plus")
                                    .font(.system(size: 11, weight: .bold))
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                            .help("Add another reference face image")

                            Button(action: {
                                appState.referenceImageURLs.removeAll()
                                appState.referenceImageURL = nil
                                appState.selectedCharacterProfile = nil
                            }) {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundColor(.secondary)
                            }
                            .buttonStyle(.plain)
                        } else {
                            Button("Select...") {
                                chooseReferenceImage(append: false)
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.small)
                        }
                    }
                    .padding(8)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(isImageTargeted ? appState.accentColor.opacity(0.15) : Color.primary.opacity(0.04))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(isImageTargeted ? appState.accentColor : Color.primary.opacity(0.08), lineWidth: 1)
                            )
                    )
                    .onTapGesture {
                        chooseReferenceImage(append: false)
                    }
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
                            chooseSaveLocation()
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.small)
                    }
                    .padding(8)
                    .contentShape(Rectangle())
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.primary.opacity(0.04))
                            .overlay(
                                RoundedRectangle(cornerRadius: 8)
                                    .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                            )
                    )
                    .onTapGesture {
                        chooseSaveLocation()
                    }
                }
            }
        }
    }

    private func chooseVideoSource() {
        let panel = NSOpenPanel()
        panel.title = "Select Video Files or Season Folder"
        panel.canChooseFiles = true
        panel.canChooseDirectories = true
        panel.allowsMultipleSelection = true
        if panel.runModal() == .OK {
            appState.addVideoURLs(panel.urls)
        }
    }

    private func chooseReferenceImage(append: Bool = false) {
        let panel = NSOpenPanel()
        panel.title = "Select Character Reference Images"
        panel.canChooseFiles = true
        panel.canChooseDirectories = false
        panel.allowsMultipleSelection = true
        panel.allowedContentTypes = [.image]
        if panel.runModal() == .OK {
            let valid = panel.urls.filter { ["png", "jpg", "jpeg", "webp"].contains($0.pathExtension.lowercased()) }
            guard !valid.isEmpty else { return }
            if append {
                for u in valid where !appState.referenceImageURLs.contains(u) {
                    appState.referenceImageURLs.append(u)
                }
            } else {
                appState.referenceImageURLs = valid
                appState.referenceImageURL = valid.first
            }
            appState.selectedCharacterProfile = nil
            if appState.referenceImageURLs.count > 1 {
                appState.showToast("\(appState.referenceImageURLs.count) reference faces selected", icon: "person.crop.circle.badge.checkmark")
            } else if let first = appState.referenceImageURLs.first {
                appState.showToast("Reference face selected: \(first.lastPathComponent)", icon: "person.crop.circle.badge.checkmark")
            }
        }
    }

    private func chooseSaveLocation() {
        let panel = NSSavePanel()
        panel.title = "Select Export Scenepack Location"
        panel.allowedContentTypes = [.mpeg4Movie]
        panel.canCreateDirectories = true
        if let current = appState.outputURL {
            panel.directoryURL = current.deletingLastPathComponent()
            panel.nameFieldStringValue = current.lastPathComponent
        } else if let first = appState.selectedVideoURLs.first {
            panel.directoryURL = first.deletingLastPathComponent()
            panel.nameFieldStringValue = "\(first.deletingPathExtension().lastPathComponent)_scenepack.mp4"
        } else {
            panel.directoryURL = FileManager.default.urls(for: .desktopDirectory, in: .userDomainMask).first
            panel.nameFieldStringValue = "scenepack.mp4"
        }
        if panel.runModal() == .OK, let targetURL = panel.url {
            appState.outputURL = targetURL
            appState.showToast("Save location set: \(targetURL.lastPathComponent)", icon: "folder.badge.gearshape")
        }
    }

    private func handleDrop(providers: [NSItemProvider], isVideo: Bool) -> Bool {
        for provider in providers {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                guard let data = item as? Data,
                      let url = URL(dataRepresentation: data, relativeTo: nil) else { return }
                DispatchQueue.main.async {
                    if isVideo {
                        self.appState.addVideoURLs([url])
                    } else {
                        let ext = url.pathExtension.lowercased()
                        if ["png", "jpg", "jpeg", "webp"].contains(ext) {
                            if !self.appState.referenceImageURLs.contains(url) {
                                self.appState.referenceImageURLs.append(url)
                            }
                            self.appState.referenceImageURL = self.appState.referenceImageURLs.first
                            self.appState.selectedCharacterProfile = nil
                            self.appState.showToast("Reference face added: \(url.lastPathComponent)", icon: "person.crop.circle.badge.checkmark")
                        }
                    }
                }
            }
        }
        return true
    }
}
