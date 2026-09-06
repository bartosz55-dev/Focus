import Foundation
import SwiftUI
import Combine

public enum SidebarTab: String, CaseIterable, Identifiable, Sendable {
    case generator = "Generator"
    case gallery = "Character Gallery"
    case settings = "Settings"

    public var id: String { rawValue }
    
    public var icon: String {
        switch self {
        case .generator: return "wand.and.stars"
        case .gallery: return "person.crop.artframe"
        case .settings: return "gearshape.2"
        }
    }
}

public enum SettingsSubTab: String, CaseIterable, Identifiable, Sendable {
    case general = "General & Theme"
    case manual = "User Manual"
    case changelog = "Changelog"
    case diagnostics = "Diagnostics & Logs"
    case about = "About Focus"

    public var id: String { rawValue }
    
    public var icon: String {
        switch self {
        case .general: return "slider.horizontal.3"
        case .manual: return "book.pages"
        case .changelog: return "clock.arrow.circlepath"
        case .diagnostics: return "terminal"
        case .about: return "info.circle"
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

    // Appearance & Localization
    @Published public var appearanceMode: String = UserDefaults.standard.string(forKey: "appearanceMode") ?? "Dark" {
        didSet {
            UserDefaults.standard.set(appearanceMode, forKey: "appearanceMode")
        }
    }

    public var preferredColorScheme: ColorScheme? {
        switch appearanceMode {
        case "Light": return .light
        case "Dark": return .dark
        default: return nil // Auto / System
        }
    }

    @Published public var settingsSubTab: SettingsSubTab = .general
    @Published public var showAboutSheet: Bool = false

    @Published public var accentColorHex: String = UserDefaults.standard.string(forKey: "accentColorHex") ?? "#8B5CF6" {
        didSet {
            UserDefaults.standard.set(accentColorHex, forKey: "accentColorHex")
        }
    }

    @Published public var currentLanguage: String = UserDefaults.standard.string(forKey: "currentLanguage") ?? "English" {
        didSet {
            UserDefaults.standard.set(currentLanguage, forKey: "currentLanguage")
        }
    }

    public var accentColor: Color {
        Color(hex: accentColorHex)
    }

    public func localized(_ key: String) -> String {
        LocalizationManager.shared.string(for: key, language: currentLanguage)
    }

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
        guard let data = p[name] else {
            showToast("Preset '\(name)' not found", icon: "exclamationmark.triangle")
            return
        }

        func numDouble(_ val: Any?) -> Double? {
            if let d = val as? Double { return d }
            if let n = val as? NSNumber { return n.doubleValue }
            if let s = val as? String, let d = Double(s) { return d }
            return nil
        }

        func numInt(_ val: Any?) -> Int? {
            if let i = val as? Int { return i }
            if let n = val as? NSNumber { return n.intValue }
            if let s = val as? String, let i = Int(s) { return i }
            return nil
        }

        func boolVal(_ val: Any?) -> Bool? {
            if let b = val as? Bool { return b }
            if let n = val as? NSNumber { return n.boolValue }
            return nil
        }

        if let pb = numDouble(data["pad_before"]) { settings.padBefore = pb }
        if let pa = numDouble(data["pad_after"]) { settings.padAfter = pa }
        if let mg = numDouble(data["max_gap"]) { settings.maxGap = mg }
        if let ms = numDouble(data["min_scene"]) { settings.minScene = ms }
        if let fs = numInt(data["frame_skip"]) { settings.frameSkip = fs }
        if let ve = boolVal(data["vad_enabled"]) { settings.vadEnabled = ve }
        if let vb = numInt(data["vad_buffer"]) { settings.vadBuffer = vb }
        if let vs = boolVal(data["vad_speaker"]) { settings.vadSpeakerEnabled = vs }
        if let vt = numDouble(data["vad_threshold"]) {
            settings.vadSpeakerThreshold = vt > 1.0 ? vt / 100.0 : vt
        }
        if let si = boolVal(data["skip_intro"]) { settings.skipIntro = si }
        if let so = boolVal(data["skip_outro"]) { settings.skipOutro = so }
        if let im = data["intro_mode"] as? String { settings.introMode = im }
        if let id = numDouble(data["intro_dur"]) { settings.introDuration = id }
        if let ar = boolVal(data["auto_render"]) { settings.autoRender = ar }
        if let aspStr = data["aspect"] as? String, let asp = AspectRatioOption(rawValue: aspStr) {
            settings.aspect = asp
        }
        if let qStr = data["quality"] as? String, let q = ExportQualityOption(rawValue: qStr) {
            settings.quality = q
        }
        showToast("Applied preset: \(name)", icon: "sparkles")
    }

    public func addVideoURLs(_ urls: [URL]) {
        var foundVideos: [URL] = []
        let videoExtensions = Set(["mp4", "mkv", "avi", "mov", "webm", "flv", "m4v", "ts"])

        for url in urls {
            var isDir: ObjCBool = false
            if FileManager.default.fileExists(atPath: url.path, isDirectory: &isDir) {
                if isDir.boolValue {
                    if let enumerator = FileManager.default.enumerator(at: url, includingPropertiesForKeys: [.isRegularFileKey], options: [.skipsHiddenFiles]) {
                        for case let fileURL as URL in enumerator {
                            if videoExtensions.contains(fileURL.pathExtension.lowercased()) {
                                foundVideos.append(fileURL)
                            }
                        }
                    }
                } else if videoExtensions.contains(url.pathExtension.lowercased()) {
                    foundVideos.append(url)
                }
            }
        }

        foundVideos.sort { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }

        if !foundVideos.isEmpty {
            self.selectedVideoURLs = foundVideos
            if self.outputURL == nil, let first = foundVideos.first {
                self.outputURL = first.deletingLastPathComponent().appendingPathComponent("\(first.deletingPathExtension().lastPathComponent)_scenepack.mp4")
            }
            showToast("Selected \(foundVideos.count) video(s)", icon: "film.stack")
        }
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

public extension Color {
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
