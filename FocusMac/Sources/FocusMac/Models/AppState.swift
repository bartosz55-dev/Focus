import Foundation
import SwiftUI
import Combine

public enum SidebarTab: String, CaseIterable, Identifiable, Sendable {
    case generator = "Generator"
    case gallery = "Character Gallery"
    case settings = "Preferences"
    case logs = "Diagnostics"

    public var id: String { rawValue }
    
    public var icon: String {
        switch self {
        case .generator: return "wand.and.stars"
        case .gallery: return "person.crop.artframe"
        case .settings: return "gearshape.2"
        case .logs: return "terminal"
        }
    }
}

@MainActor
public final class AppState: ObservableObject {
    // Media selections
    @Published public var selectedVideoURLs: [URL] = []
    @Published public var referenceImageURL: URL?
    @Published public var selectedCharacterProfile: CharacterProfile?
    @Published public var outputURL: URL?

    // Workflow & Tuning
    @Published public var mode: DetectionMode = .realFaces
    @Published public var settings: ScanSettings = ScanSettings()
    @Published public var customPresets: [String] = []
    @Published public var currentTab: SidebarTab = .generator

    // Execution state
    @Published public var isProcessing: Bool = false
    @Published public var processingStatus: String = "Ready to analyze footage"
    @Published public var progressValue: Double = 0.0
    @Published public var episodeProgressBadge: String?
    @Published public var episodeProgressBar: Double = 0.0

    // Results & Reviews
    @Published public var detectedClips: [ClipInterval] = []
    @Published public var audioTracks: [AudioTrackItem] = [
        AudioTrackItem(index: 0, label: "Default Audio Stream (Track 1)"),
        AudioTrackItem(index: -1, label: "Keep All Audio Tracks (Multi-Audio)")
    ]
    @Published public var galleryProfiles: [CharacterProfile] = []
    @Published public var logLines: [String] = []
    @Published public var toastMessage: String?
    @Published public var toastIcon: String = "checkmark.circle"
    @Published public var previewClip: ClipInterval?

    public init() {
        refreshPresets()
    }

    public func showToast(_ msg: String, icon: String = "checkmark.circle") {
        withAnimation(.spring(response: 0.35, dampingFraction: 0.8)) {
            self.toastMessage = msg
            self.toastIcon = icon
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 3.0) {
            if self.toastMessage == msg {
                withAnimation {
                    self.toastMessage = nil
                }
            }
        }
    }

    public func refreshPresets() {
        let p = PresetManager.loadPresets()
        self.customPresets = Array(p.keys).sorted()
    }

    public func applyPreset(name: String) {
        let p = PresetManager.loadPresets()
        guard let data = p[name] else { return }
        if let pb = data["pad_before"] as? Double { settings.padBefore = pb }
        if let pa = data["pad_after"] as? Double { settings.padAfter = pa }
        if let mg = data["max_gap"] as? Double { settings.maxGap = mg }
        if let ms = data["min_scene"] as? Double { settings.minScene = ms }
        if let fs = data["frame_skip"] as? Int { settings.frameSkip = fs }
        if let ve = data["vad_enabled"] as? Bool { settings.vadEnabled = ve }
        if let vb = data["vad_buffer"] as? Int { settings.vadBuffer = vb }
        if let vs = data["vad_speaker"] as? Bool { settings.vadSpeakerEnabled = vs }
        if let vt = data["vad_threshold"] as? Int { settings.vadSpeakerThreshold = Double(vt) / 100.0 }
        if let si = data["skip_intro"] as? Bool { settings.skipIntro = si }
        if let so = data["skip_outro"] as? Bool { settings.skipOutro = so }
        if let im = data["intro_mode"] as? String { settings.introMode = im }
        if let id = data["intro_dur"] as? Double { settings.introDuration = id }
        if let ar = data["auto_render"] as? Bool { settings.autoRender = ar }
        showToast("Applied preset: \(name)", icon: "sparkles")
    }

    public func selectAllClips(_ select: Bool) {
        for i in detectedClips.indices {
            detectedClips[i].isSelected = select
        }
    }

    public func startScan() {
        guard let video = selectedVideoURLs.first else {
            showToast("Please select an Input Video first.", icon: "exclamationmark.triangle")
            return
        }
        guard referenceImageURL != nil || selectedCharacterProfile != nil else {
            showToast("Please select a Reference Face image.", icon: "person.crop.circle.badge.questionmark")
            return
        }

        isProcessing = true
        progressValue = 0.0
        processingStatus = "Initializing scan..."
        detectedClips.removeAll()
        if settings.preventSleep {
            SleepManager.shared.preventSleep(reason: "Focus scanning video")
        }

        var args: [String] = [
            "-v", video.path,
            "--mode", mode.rawValue,
            "--pad-before", String(settings.padBefore),
            "--pad-after", String(settings.padAfter),
            "--max-gap", String(settings.maxGap),
            "--min-scene", String(settings.minScene),
            "--skip-frames", String(settings.frameSkip),
            "--vad-buffer", String(settings.vadBuffer),
            "--vad-speaker-threshold", String(settings.vadSpeakerThreshold),
            "--intro-mode", settings.introMode,
            "--intro-duration", String(settings.introDuration),
            "--aspect", settings.aspect.rawValue,
            "--quality", settings.quality.rawValue,
            "--audio-track", String(settings.audioTrackIndex),
            "--scan-only"
        ]
        if let img = referenceImageURL {
            args += ["-i", img.path]
        } else if let char = selectedCharacterProfile {
            args += ["-i", char.cropPath]
        }
        if settings.vadEnabled { args.append("--vad") }
        if settings.vadSpeakerEnabled { args.append("--vad-speaker") }
        if settings.skipIntro { args.append("--skip-intro") }
        if settings.skipOutro { args.append("--skip-outro") }

        Task {
            do {
                try await ProcessBridge.shared.run(arguments: args) { [weak self] event in
                    guard let self else { return }
                    Task { @MainActor in
                        self.handleBridgeEvent(event)
                    }
                }
            } catch {
                self.isProcessing = false
                self.processingStatus = "Error: \(error.localizedDescription)"
                SleepManager.shared.allowSleep()
                self.showToast("Scan error: \(error.localizedDescription)", icon: "xmark.octagon")
            }
        }
    }

    public func startRender() {
        guard let video = selectedVideoURLs.first else { return }
        let selected = detectedClips.filter { $0.isSelected }
        guard !selected.isEmpty else {
            showToast("No clips selected to render.", icon: "exclamationmark.triangle")
            return
        }

        isProcessing = true
        progressValue = 0.0
        processingStatus = "Rendering clips with hardware acceleration..."
        if settings.preventSleep {
            SleepManager.shared.preventSleep(reason: "Focus rendering scenepack")
        }

        let out = outputURL ?? video.deletingPathExtension().appendingPathExtension("scenepack.mp4")

        var args: [String] = [
            "-v", video.path,
            "-o", out.path,
            "--mode", mode.rawValue,
            "--aspect", settings.aspect.rawValue,
            "--quality", settings.quality.rawValue,
            "--audio-track", String(settings.audioTrackIndex)
        ]
        if let img = referenceImageURL {
            args += ["-i", img.path]
        } else if let char = selectedCharacterProfile {
            args += ["-i", char.cropPath]
        }

        Task {
            do {
                try await ProcessBridge.shared.run(arguments: args) { [weak self] event in
                    guard let self else { return }
                    Task { @MainActor in
                        self.handleBridgeEvent(event)
                    }
                }
            } catch {
                self.isProcessing = false
                self.processingStatus = "Render error: \(error.localizedDescription)"
                SleepManager.shared.allowSleep()
                self.showToast("Render failed: \(error.localizedDescription)", icon: "xmark.octagon")
            }
        }
    }

    public func cancel() {
        Task {
            await ProcessBridge.shared.cancel()
        }
        isProcessing = false
        processingStatus = "Cancelled"
        SleepManager.shared.allowSleep()
        showToast("Process cancelled", icon: "slash.circle")
    }

    private func handleBridgeEvent(_ event: BridgeEvent) {
        switch event {
        case .log(let msg):
            logLines.append(msg)
        case .progress(let val, let status):
            self.progressValue = val
            self.processingStatus = status
        case .episodeProgress(let cur, let tot, let name, let epProg, let totProg):
            self.episodeProgressBadge = "Episode [\(cur)/\(tot)]: \(name)"
            self.episodeProgressBar = epProg
            self.progressValue = totProg
        case .galleryProgress(let val, let status):
            self.progressValue = val
            self.processingStatus = status
        case .galleryStatus(let status):
            self.processingStatus = status
        case .galleryResults(let profiles):
            self.galleryProfiles = profiles
            self.isProcessing = false
            self.processingStatus = "Found \(profiles.count) character profile(s)."
            SleepManager.shared.allowSleep()
        case .reviewReady(let clips):
            self.detectedClips = clips
            self.isProcessing = false
            self.processingStatus = "Scan complete! Found \(clips.count) clip(s)."
            SleepManager.shared.allowSleep()
            if settings.autoRender && !clips.isEmpty {
                startRender()
            }
        case .renderComplete(let out):
            self.isProcessing = false
            self.progressValue = 1.0
            self.processingStatus = "Render complete! Saved to \(URL(fileURLWithPath: out).lastPathComponent)"
            SleepManager.shared.allowSleep()
            NSSound(named: "Glass")?.play()
            showToast("Scenepack successfully rendered!", icon: "checkmark.seal.fill")
        case .audioTracks(let tracks):
            self.audioTracks = tracks + [AudioTrackItem(index: -1, label: "Keep All Audio Tracks (Multi-Audio)")]
        case .masterConcatComplete(let out):
            self.isProcessing = false
            self.processingStatus = "Master scenepack created: \(URL(fileURLWithPath: out).lastPathComponent)"
            SleepManager.shared.allowSleep()
        case .error(let msg):
            self.isProcessing = false
            self.processingStatus = "Error: \(msg)"
            SleepManager.shared.allowSleep()
            showToast("Error: \(msg)", icon: "xmark.octagon")
        }
    }
}
