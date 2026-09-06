import SwiftUI

public struct CharacterGalleryView: View {
    @ObservedObject var appState: AppState

    private let columns = [
        GridItem(.adaptive(minimum: 150, maximum: 190), spacing: 14)
    ]

    public var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Character Detection Gallery (Beta)")
                        .font(.system(size: 16, weight: .bold))
                    Text("Automatically detect and cluster unique characters from your input video.")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }

                Spacer()

                Button(action: {
                    startGalleryScan()
                }) {
                    HStack(spacing: 6) {
                        Image(systemName: "person.2.crop.square.stack")
                        Text(appState.isProcessing ? "Scanning Video..." : "Pre-Scan Characters")
                    }
                }
                .buttonStyle(.borderedProminent)
                .tint(.purple)
                .disabled(appState.selectedVideoURLs.isEmpty || appState.isProcessing)
            }
            .padding(.horizontal, 4)

            if appState.galleryProfiles.isEmpty {
                VStack(spacing: 12) {
                    Spacer()
                    Image(systemName: "person.crop.artframe")
                        .font(.system(size: 40))
                        .foregroundColor(.secondary.opacity(0.5))
                    Text("No characters scanned yet.")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(.secondary)
                    Text("Select a video in the Generator and click 'Pre-Scan Characters' to discover all faces.")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary.opacity(0.8))
                    Spacer()
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVGrid(columns: columns, spacing: 14) {
                        ForEach(appState.galleryProfiles) { profile in
                            CharacterCard(profile: profile) {
                                appState.selectedCharacterProfile = profile
                                appState.referenceImageURL = nil
                                appState.currentTab = .generator
                                appState.showToast("Selected Character #\(profile.id) as Reference!", icon: "person.crop.circle.badge.checkmark")
                            }
                        }
                    }
                    .padding(4)
                }
            }
        }
        .padding(16)
    }

    private func startGalleryScan() {
        guard let video = appState.selectedVideoURLs.first else { return }
        appState.isProcessing = true
        appState.progressValue = 0.0
        appState.processingStatus = "Scanning video for characters..."
        appState.galleryProfiles.removeAll()

        let args = [
            "-v", video.path,
            "--mode", appState.mode.rawValue,
            "--gallery-scan"
        ]

        Task {
            do {
                try await ProcessBridge.shared.run(arguments: args) { event in
                    Task { @MainActor in
                        switch event {
                        case .galleryProgress(let val, let status):
                            self.appState.progressValue = val
                            self.appState.processingStatus = status
                        case .galleryResults(let profiles):
                            self.appState.galleryProfiles = profiles
                            self.appState.isProcessing = false
                            self.appState.showToast("Found \(profiles.count) character profile(s)!", icon: "person.2.fill")
                        case .galleryStatus(let status):
                            self.appState.processingStatus = status
                        case .error(let err):
                            self.appState.isProcessing = false
                            self.appState.showToast("Gallery scan failed: \(err)", icon: "xmark.octagon")
                        default:
                            break
                        }
                    }
                }
            } catch {
                self.appState.isProcessing = false
                self.appState.showToast("Scan failed: \(error.localizedDescription)", icon: "xmark.octagon")
            }
        }
    }
}

struct CharacterCard: View {
    let profile: CharacterProfile
    let onSelect: () -> Void

    var body: some View {
        GlassCard {
            VStack(spacing: 8) {
                if let nsImg = NSImage(contentsOfFile: profile.cropPath) {
                    Image(nsImage: nsImg)
                        .resizable()
                        .aspectRatio(contentMode: .fill)
                        .frame(width: 90, height: 90)
                        .clipShape(RoundedRectangle(cornerRadius: 8))
                } else {
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.white.opacity(0.08))
                        .frame(width: 90, height: 90)
                        .overlay(Image(systemName: "person.fill").foregroundColor(.secondary))
                }

                Text("Character #\(profile.id)")
                    .font(.system(size: 11, weight: .bold))

                Text("\(profile.count) detection(s)")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)

                Button("Select as Reference") {
                    onSelect()
                }
                .buttonStyle(.borderedProminent)
                .tint(.purple)
                .controlSize(.small)
            }
            .frame(maxWidth: .infinity)
        }
    }
}
