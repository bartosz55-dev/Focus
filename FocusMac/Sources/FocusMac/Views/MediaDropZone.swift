import SwiftUI
import UniformTypeIdentifiers
import AppKit

public struct MediaDropZone: View {
    @ObservedObject var appState: AppState
    @State private var isVideoTargeted = false
    @State private var isImageTargeted = false

    public var body: some View {
        HStack(spacing: 10) {
            // Tile 1: Input Video Footage
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    HStack(spacing: 5) {
                        Image(systemName: "film.stack")
                            .foregroundColor(appState.accentColor)
                            .font(.system(size: 11, weight: .bold))
                        Text(appState.localized("input_footage"))
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.primary)
                    }
                    Spacer()
                    if !appState.selectedVideoURLs.isEmpty {
                        Text(appState.selectedVideoURLs.count == 1 ? "1 Video" : "\(appState.selectedVideoURLs.count) Videos")
                            .font(.system(size: 9, weight: .bold))
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(Capsule().fill(appState.accentColor.opacity(0.15)))
                            .foregroundColor(appState.accentColor)

                        Button(action: { appState.selectedVideoURLs.removeAll() }) {
                            Image(systemName: "xmark.circle.fill")
                                .foregroundColor(.secondary)
                                .font(.system(size: 12))
                        }
                        .buttonStyle(.plain)
                    } else {
                        Button(action: { chooseVideoSource() }) {
                            Text("Browse...")
                                .font(.system(size: 10, weight: .semibold))
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.mini)
                    }
                }

                HStack(spacing: 8) {
                    Image(systemName: "video.fill")
                        .font(.system(size: 16))
                        .foregroundColor(appState.selectedVideoURLs.isEmpty ? .secondary.opacity(0.6) : appState.accentColor)
                        .frame(width: 24, height: 24)

                    VStack(alignment: .leading, spacing: 2) {
                        if let first = appState.selectedVideoURLs.first {
                            Text(first.lastPathComponent)
                                .font(.system(size: 11, weight: .semibold))
                                .lineLimit(1)
                                .truncationMode(.middle)
                            Text(first.deletingLastPathComponent().path)
                                .font(.system(size: 9))
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        } else {
                            Text(appState.localized("drop_video"))
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                                .lineLimit(2)
                        }
                    }
                }
            }
            .padding(10)
            .frame(maxWidth: .infinity, minHeight: 76, alignment: .topLeading)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(isVideoTargeted ? appState.accentColor.opacity(0.15) : Color.primary.opacity(0.03))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(isVideoTargeted ? appState.accentColor : Color.primary.opacity(0.08), lineWidth: 1)
                    )
            )
            .contentShape(Rectangle())
            .onTapGesture {
                chooseVideoSource()
            }
            .onDrop(of: [.fileURL], isTargeted: $isVideoTargeted) { providers in
                handleDrop(providers: providers, isVideo: true)
            }

            // Tile 2: Target Character Reference
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    HStack(spacing: 5) {
                        Image(systemName: "person.crop.circle")
                            .foregroundColor(appState.accentColor)
                            .font(.system(size: 11, weight: .bold))
                        Text(appState.localized("target_reference"))
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.primary)
                    }
                    Spacer()
                    if !appState.referenceImageURLs.isEmpty || appState.referenceImageURL != nil || appState.selectedCharacterProfile != nil {
                        HStack(spacing: 4) {
                            if appState.referenceImageURLs.count > 1 {
                                Text("\(appState.referenceImageURLs.count) Faces")
                                    .font(.system(size: 9, weight: .bold))
                                    .padding(.horizontal, 6)
                                    .padding(.vertical, 2)
                                    .background(Capsule().fill(appState.accentColor.opacity(0.15)))
                                    .foregroundColor(appState.accentColor)
                            }

                            Button(action: {
                                chooseReferenceImage(append: true)
                            }) {
                                Image(systemName: "plus")
                                    .font(.system(size: 10, weight: .bold))
                            }
                            .buttonStyle(.bordered)
                            .controlSize(.mini)
                            .help("Add another reference face image")

                            Button(action: {
                                appState.referenceImageURLs.removeAll()
                                appState.referenceImageURL = nil
                                appState.selectedCharacterProfile = nil
                            }) {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundColor(.secondary)
                                    .font(.system(size: 12))
                            }
                            .buttonStyle(.plain)
                        }
                    } else {
                        Button(action: { chooseReferenceImage(append: false) }) {
                            Text("Select...")
                                .font(.system(size: 10, weight: .semibold))
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.mini)
                    }
                }

                HStack(spacing: 8) {
                    if !appState.referenceImageURLs.isEmpty,
                       let first = appState.referenceImageURLs.first,
                       let nsImg = NSImage(contentsOf: first) {
                        Image(nsImage: nsImg)
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 24, height: 24)
                            .clipShape(RoundedRectangle(cornerRadius: 5))
                    } else if let imgURL = appState.referenceImageURL,
                       let nsImg = NSImage(contentsOf: imgURL) {
                        Image(nsImage: nsImg)
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 24, height: 24)
                            .clipShape(RoundedRectangle(cornerRadius: 5))
                    } else if let char = appState.selectedCharacterProfile,
                              let nsImg = NSImage(contentsOfFile: char.cropPath) {
                        Image(nsImage: nsImg)
                            .resizable()
                            .aspectRatio(contentMode: .fill)
                            .frame(width: 24, height: 24)
                            .clipShape(RoundedRectangle(cornerRadius: 5))
                    } else {
                        Image(systemName: "person.crop.circle.badge.plus")
                            .font(.system(size: 16))
                            .foregroundColor(.secondary.opacity(0.6))
                            .frame(width: 24, height: 24)
                    }

                    VStack(alignment: .leading, spacing: 2) {
                        if appState.referenceImageURLs.count > 1 {
                            Text("\(appState.referenceImageURLs.count) Reference Faces")
                                .font(.system(size: 11, weight: .semibold))
                                .lineLimit(1)
                            Text(appState.referenceImageURLs.map { $0.lastPathComponent }.joined(separator: ", "))
                                .font(.system(size: 9))
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        } else if let imgURL = appState.referenceImageURL {
                            Text(imgURL.lastPathComponent)
                                .font(.system(size: 11, weight: .semibold))
                                .lineLimit(1)
                                .truncationMode(.middle)
                            Text(imgURL.deletingLastPathComponent().path)
                                .font(.system(size: 9))
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        } else if let char = appState.selectedCharacterProfile {
                            Text("Character #\(char.id) (\(char.count) detections)")
                                .font(.system(size: 11, weight: .semibold))
                                .lineLimit(1)
                            Text("From Gallery Scan")
                                .font(.system(size: 9))
                                .foregroundColor(.secondary)
                        } else {
                            Text(appState.localized("drop_image"))
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                                .lineLimit(2)
                        }
                    }
                }
            }
            .padding(10)
            .frame(maxWidth: .infinity, minHeight: 76, alignment: .topLeading)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(isImageTargeted ? appState.accentColor.opacity(0.15) : Color.primary.opacity(0.03))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(isImageTargeted ? appState.accentColor : Color.primary.opacity(0.08), lineWidth: 1)
                    )
            )
            .contentShape(Rectangle())
            .onTapGesture {
                chooseReferenceImage(append: false)
            }
            .onDrop(of: [.fileURL], isTargeted: $isImageTargeted) { providers in
                handleDrop(providers: providers, isVideo: false)
            }

            // Tile 3: Save Destination
            VStack(alignment: .leading, spacing: 6) {
                HStack {
                    HStack(spacing: 5) {
                        Image(systemName: "folder")
                            .foregroundColor(appState.accentColor)
                            .font(.system(size: 11, weight: .bold))
                        Text(appState.localized("save_location"))
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.primary)
                    }
                    Spacer()
                    if appState.selectedVideoURLs.count > 1 {
                        Text("Master")
                            .font(.system(size: 9, weight: .bold))
                            .padding(.horizontal, 5)
                            .padding(.vertical, 1)
                            .background(Capsule().fill(appState.accentColor.opacity(0.15)))
                            .foregroundColor(appState.accentColor)
                    }
                    Button(action: { chooseSaveLocation() }) {
                        Text(appState.outputURL != nil ? "Change..." : "Set...")
                            .font(.system(size: 10, weight: .semibold))
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.mini)
                }

                HStack(spacing: 8) {
                    Image(systemName: "folder.fill")
                        .font(.system(size: 16))
                        .foregroundColor(appState.outputURL == nil ? .secondary.opacity(0.6) : appState.accentColor)
                        .frame(width: 24, height: 24)

                    VStack(alignment: .leading, spacing: 2) {
                        if let out = appState.outputURL {
                            Text(out.lastPathComponent)
                                .font(.system(size: 11, weight: .semibold))
                                .lineLimit(1)
                                .truncationMode(.middle)
                            Text(out.deletingLastPathComponent().path)
                                .font(.system(size: 9))
                                .foregroundColor(.secondary)
                                .lineLimit(1)
                                .truncationMode(.middle)
                        } else {
                            Text(appState.localized("auto_desktop"))
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                                .lineLimit(2)
                        }
                    }
                }
            }
            .padding(10)
            .frame(maxWidth: .infinity, minHeight: 76, alignment: .topLeading)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(Color.primary.opacity(0.03))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                    )
            )
            .contentShape(Rectangle())
            .onTapGesture {
                chooseSaveLocation()
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
        var types: [UTType] = [.mpeg4Movie, .quickTimeMovie]
        if let mkvType = UTType(filenameExtension: "mkv") {
            types.append(mkvType)
        }
        panel.allowedContentTypes = types
        panel.canCreateDirectories = true

        let ext = appState.settings.containerFormat.fileExtension
        if let current = appState.outputURL {
            panel.directoryURL = current.deletingLastPathComponent()
            panel.nameFieldStringValue = current.lastPathComponent
        } else if let first = appState.selectedVideoURLs.first {
            panel.directoryURL = first.deletingLastPathComponent()
            if appState.selectedVideoURLs.count > 1 {
                let parent = first.deletingLastPathComponent().lastPathComponent
                let name = (parent.isEmpty || parent == "/") ? "Master_Scenepack.\(ext)" : "\(parent) - Master Scenepack.\(ext)"
                panel.nameFieldStringValue = name
            } else {
                panel.nameFieldStringValue = "\(first.deletingPathExtension().lastPathComponent)_scenepack.\(ext)"
            }
        } else {
            panel.directoryURL = FileManager.default.urls(for: .desktopDirectory, in: .userDomainMask).first
            panel.nameFieldStringValue = "scenepack.\(ext)"
        }
        if panel.runModal() == .OK, let targetURL = panel.url {
            appState.outputURL = targetURL
            let pickedExt = targetURL.pathExtension.lowercased()
            if !pickedExt.isEmpty {
                appState.settings.containerFormat = ContainerFormatOption.parse(pickedExt)
            }
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
