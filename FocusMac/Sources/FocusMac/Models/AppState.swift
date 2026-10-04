import Foundation
import SwiftUI
import Combine
import AppKit
import Darwin

public struct SystemHardwareInfo: Sendable {
    public let cpuModel: String
    public let coreCount: Int
    public let ramTotalGB: Double
    public let osVersion: String
    public let diskFreeGB: Double
    public let diskTotalGB: Double

    public var cpuSummary: String {
        "\(cpuModel) (\(coreCount) Cores)"
    }

    public var ramSummary: String {
        String(format: "%.1f GB RAM", ramTotalGB)
    }

    public var diskSummary: String {
        String(format: "Free: %.1f GB / %.1f GB", diskFreeGB, diskTotalGB)
    }

    public static func current() -> SystemHardwareInfo {
        var size: size_t = 0
        sysctlbyname("machdep.cpu.brand_string", nil, &size, nil, 0)
        var brand = ""
        if size > 0 {
            var buffer = [CChar](repeating: 0, count: size)
            if sysctlbyname("machdep.cpu.brand_string", &buffer, &size, nil, 0) == 0 {
                brand = String(cString: buffer).trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }
        if brand.isEmpty {
            #if arch(arm64)
            brand = "Apple Silicon"
            #else
            brand = "Intel x86_64"
            #endif
        }

        let cores = ProcessInfo.processInfo.activeProcessorCount
        let ramBytes = ProcessInfo.processInfo.physicalMemory
        let ramGB = Double(ramBytes) / (1024.0 * 1024.0 * 1024.0)
        let os = ProcessInfo.processInfo.operatingSystemVersionString

        var freeGB = 0.0
        var totalGB = 0.0
        let targetURL = URL(fileURLWithPath: NSHomeDirectory())
        if let values = try? targetURL.resourceValues(forKeys: [.volumeAvailableCapacityForImportantUsageKey, .volumeTotalCapacityKey]) {
            if let free = values.volumeAvailableCapacityForImportantUsage {
                freeGB = Double(free) / (1024.0 * 1024.0 * 1024.0)
            }
            if let tot = values.volumeTotalCapacity {
                totalGB = Double(tot) / (1024.0 * 1024.0 * 1024.0)
            }
        }

        return SystemHardwareInfo(
            cpuModel: brand,
            coreCount: cores,
            ramTotalGB: ramGB,
            osVersion: os,
            diskFreeGB: freeGB,
            diskTotalGB: totalGB
        )
    }
}

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
    public static let appVersion: String = "v2.4.0"
    public static let appVersionShort: String = "2.4.0"
    public static let appBuild: String = "240"

    // Media selections
    @Published public var selectedVideoURLs: [URL] = []
    @Published public var referenceImageURLs: [URL] = []
    public var referenceImageURL: URL? {
        get { referenceImageURLs.first }
        set {
            if let val = newValue {
                if !referenceImageURLs.contains(val) {
                    referenceImageURLs = [val]
                }
            } else {
                referenceImageURLs = []
            }
        }
    }
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
    @Published public var currentEpisodeEta: String?
    @Published public var seasonBatchEta: String?

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
            updateAppAppearance()
        }
    }

    public var preferredColorScheme: ColorScheme? {
        switch appearanceMode {
        case "Light": return .light
        case "Dark": return .dark
        default: return nil // Auto / System
        }
    }

    public func updateAppAppearance() {
        DispatchQueue.main.async {
            let appAppearance: NSAppearance?
            switch self.appearanceMode {
            case "Light":
                appAppearance = NSAppearance(named: .aqua)
            case "Dark":
                appAppearance = NSAppearance(named: .darkAqua)
            default:
                appAppearance = nil
            }
            NSApp.appearance = appAppearance
            for window in NSApp.windows {
                window.appearance = appAppearance
            }
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

    @Published public var engineDiagnostics: ProcessBridge.EngineDiagnostics = ProcessBridge.checkEngineDiagnostics()
    @Published public var systemHardware: SystemHardwareInfo = SystemHardwareInfo.current()

    public func refreshEngineDiagnostics() {
        self.engineDiagnostics = ProcessBridge.checkEngineDiagnostics()
    }

    public func refreshSystemHardware() {
        self.systemHardware = SystemHardwareInfo.current()
    }

    public init() {
        refreshPresets()
        loadPersistentLogs()
        refreshEngineDiagnostics()
        refreshSystemHardware()
        updateAppAppearance()
    }

    public func loadPersistentLogs() {
        let logPath = ("~/Library/Logs/Focus/focus_debug.log" as NSString).expandingTildeInPath
        if FileManager.default.fileExists(atPath: logPath),
           let content = try? String(contentsOfFile: logPath, encoding: .utf8) {
            let lines = content.components(separatedBy: .newlines).filter { !$0.trimmingCharacters(in: .whitespaces).isEmpty }
            let recent = Array(lines.suffix(150))
            if !recent.isEmpty {
                self.logLines = recent
                return
            }
        }
        if self.logLines.isEmpty {
            self.logLines.append("[INFO] Focus Studio v2.4.0 Diagnostic Engine ready. Awaiting scan or render events.")
        }
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
        if let exp = boolVal(data["export_clips_folder"]) { settings.exportClipsFolder = exp }
        if let aspStr = data["aspect"] as? String, let asp = AspectRatioOption(rawValue: aspStr) {
            settings.aspect = asp
        }
        if let qStr = data["quality"] as? String {
            settings.quality = ExportQualityOption.parse(qStr)
        }
        if let vcStr = data["video_codec"] as? String {
            settings.videoCodec = VideoCodecOption.parse(vcStr)
        }
        if let cfStr = data["container_format"] as? String {
            settings.containerFormat = ContainerFormatOption.parse(cfStr)
            updateOutputContainerExtension(settings.containerFormat)
        }
        showToast("Applied preset: \(name)", icon: "sparkles")
    }

    public func updateOutputContainerExtension(_ format: ContainerFormatOption) {
        if let current = outputURL {
            let newURL = current.deletingPathExtension().appendingPathExtension(format.fileExtension)
            if newURL != current {
                self.outputURL = newURL
                self.logLines.append("[INFO] Output container format changed to .\(format.fileExtension): \(newURL.lastPathComponent)")
            }
        }
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
                let ext = settings.containerFormat.fileExtension
                if foundVideos.count > 1 {
                    let parent = first.deletingLastPathComponent().lastPathComponent
                    let name = (parent.isEmpty || parent == "/") ? "Master_Scenepack.\(ext)" : "\(parent) - Master Scenepack.\(ext)"
                    self.outputURL = first.deletingLastPathComponent().appendingPathComponent(name)
                } else {
                    self.outputURL = first.deletingLastPathComponent().appendingPathComponent("\(first.deletingPathExtension().lastPathComponent)_scenepack.\(ext)")
                }
            }
            showToast("Selected \(foundVideos.count) video(s)", icon: "film.stack")
            if let first = foundVideos.first {
                probeAudioTracks(for: first)
            }
        }
    }

    public func probeAudioTracks(for url: URL) {
        Task { @MainActor in
            let tracks = await ProcessBridge.shared.queryAudioTracks(for: url.path)
            if !tracks.isEmpty {
                self.audioTracks = tracks + [AudioTrackItem(index: -1, label: "Keep All Audio Tracks (Multi-Audio)")]
                if !self.audioTracks.contains(where: { $0.index == self.settings.audioTrackIndex }) {
                    self.settings.audioTrackIndex = 0
                }
            }
        }
    }

    public func loadScanFromJSON(url: URL) {
        do {
            let data = try Data(contentsOf: url)
            var rawList: [[String: Any]] = []
            if let jsonArray = try? JSONSerialization.jsonObject(with: data) as? [[String: Any]] {
                rawList = jsonArray
            } else if let jsonObj = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                      let intervals = jsonObj["intervals"] as? [[String: Any]] {
                rawList = intervals
            }
            guard !rawList.isEmpty else {
                showToast("No clip intervals found in JSON.", icon: "exclamationmark.triangle")
                return
            }
            var clips: [ClipInterval] = []
            for (idx, item) in rawList.enumerated() {
                let src = (item["source"] as? String) ?? ""
                let s = (item["start"] as? Double) ?? Double(item["start"] as? Int ?? 0)
                let e = (item["end"] as? Double) ?? Double(item["end"] as? Int ?? 0)
                let avg = (item["avg_x"] as? Double) ?? 0.5
                let thumb = (item["thumb_path"] as? String) ?? ""
                clips.append(ClipInterval(id: idx + 1, source: src, start: s, end: e, duration: max(0.0, e - s), avgX: avg, thumbPath: thumb, isSelected: true))
            }
            self.detectedClips = clips
            self.processingStatus = "Loaded \(clips.count) clips from scan file."
            self.logLines.append("[INFO] Loaded \(clips.count) clip(s) from: \(url.lastPathComponent)")
            showToast("Loaded \(clips.count) clips from scan!", icon: "checkmark.circle.fill")

            let sources = Set(clips.map { $0.source }.filter { !$0.isEmpty })
            if self.selectedVideoURLs.isEmpty && !sources.isEmpty {
                self.selectedVideoURLs = sources.map { URL(fileURLWithPath: $0) }.sorted { $0.lastPathComponent.localizedStandardCompare($1.lastPathComponent) == .orderedAscending }
            }
        } catch {
            showToast("Failed to load scan: \(error.localizedDescription)", icon: "xmark.octagon")
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
        episodeProgressBadge = nil
        episodeProgressBar = 0.0
        currentEpisodeEta = nil
        seasonBatchEta = nil
        processingStatus = "Initializing scan..."
        detectedClips.removeAll()
        if settings.preventSleep {
            SleepManager.shared.preventSleep(reason: "Focus scanning video")
        }

        let videoArg = selectedVideoURLs.count > 1 ? selectedVideoURLs.map { $0.path }.joined(separator: ";") : video.path
        let hw = SystemHardwareInfo.current()
        logLines.append("[SYSTEM] Host: \(hw.cpuSummary) | \(hw.ramSummary) | macOS \(hw.osVersion)")
        logLines.append("[SYSTEM] Storage: \(hw.diskSummary) | Accel: Apple VideoToolbox")
        logLines.append("[CONFIG] Mode: \(mode.rawValue) | Codec: \(settings.videoCodec.cliValue) | Container: .\(settings.containerFormat.fileExtension) | Quality: \(settings.quality.rawValue)")
        logLines.append("[CONFIG] Timing: In: \(String(format: "%.1f", settings.padBefore))s, Out: \(String(format: "%.1f", settings.padAfter))s, Gap: \(String(format: "%.1f", settings.maxGap))s, Min: \(String(format: "%.1f", settings.minScene))s, ScanStep: \(settings.frameSkip) frames")
        if settings.vadEnabled {
            logLines.append("[CONFIG] Audio AI: VAD active (\(settings.vadBuffer)ms buffer)\(settings.vadSpeakerEnabled ? " + Speaker Filter (threshold: \(String(format: "%.2f", settings.vadSpeakerThreshold)))" : "")")
        }
        logLines.append("[INFO] Starting video analysis: \(video.lastPathComponent) [Mode: \(mode.rawValue)]")

        var args: [String] = [
            "-v", videoArg,
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
            "--tolerance", String(settings.tolerance),
            "--scan-only"
        ]
        if !referenceImageURLs.isEmpty {
            let imgArg = referenceImageURLs.count > 1 ? referenceImageURLs.map { $0.path }.joined(separator: ";") : referenceImageURLs[0].path
            args += ["-i", imgArg]
        } else if let char = selectedCharacterProfile {
            args += ["-i", char.cropPath]
        }
        if settings.vadEnabled { args.append("--vad") }
        if settings.vadSpeakerEnabled { args.append("--vad-speaker") }
        if settings.skipIntro { args.append("--skip-intro") }
        if settings.skipOutro { args.append("--skip-outro") }
        if settings.snapCuts {
            args.append("--snap-cuts")
        } else {
            args.append("--no-snap-cuts")
        }
        if settings.preventSleep {
            args.append("--prevent-sleep")
        }

        Task { [weak self] in
            guard let self else { return }
            do {
                try await ProcessBridge.shared.run(arguments: args) { [weak self] event in
                    guard let self else { return }
                    Task { @MainActor in
                        self.handleBridgeEvent(event)
                    }
                }
            } catch {
                await MainActor.run {
                    self.isProcessing = false
                    self.processingStatus = "Error: \(error.localizedDescription)"
                    self.logLines.append("[ERROR] Scan execution failed: \(error.localizedDescription)")
                    SleepManager.shared.allowSleep()
                    self.showToast("Scan error: \(error.localizedDescription)", icon: "xmark.octagon")
                }
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

        let ext = settings.containerFormat.fileExtension
        let out = outputURL ?? video.deletingPathExtension().appendingPathExtension("scenepack.\(ext)")
        let videoArg = selectedVideoURLs.count > 1 ? selectedVideoURLs.map { $0.path }.joined(separator: ";") : video.path
        let hw = SystemHardwareInfo.current()
        logLines.append("[SYSTEM] Target: \(out.lastPathComponent) | Volume: \(hw.diskSummary)")
        logLines.append("[CONFIG] Render Engine: Codec: \(settings.videoCodec.cliValue) | Container: .\(settings.containerFormat.fileExtension) | Quality: \(settings.quality.rawValue)")
        logLines.append("[CONFIG] Automations: Snap Cuts: \(settings.snapCuts ? "ON" : "OFF") | Clips Folder: \(settings.exportClipsFolder ? "ON" : "OFF") | Timeline XML: \(settings.exportXml ? "ON" : "OFF")")
        logLines.append("[INFO] Starting hardware-accelerated render of \(selected.count) clip(s) to: \(out.lastPathComponent)")

        var args: [String] = [
            "-v", videoArg,
            "-o", out.path,
            "--mode", mode.rawValue,
            "--aspect", settings.aspect.rawValue,
            "--quality", settings.quality.rawValue,
            "--video-codec", settings.videoCodec.cliValue,
            "--container", settings.containerFormat.fileExtension,
            "--audio-track", String(settings.audioTrackIndex)
        ]
        if settings.exportClipsFolder {
            args.append("--export-clips-folder")
        }
        if settings.exportXml {
            args.append("--export-xml")
        } else {
            args.append("--no-export-xml")
        }
        if settings.preventSleep {
            args.append("--prevent-sleep")
        }
        if !referenceImageURLs.isEmpty {
            let imgArg = referenceImageURLs.count > 1 ? referenceImageURLs.map { $0.path }.joined(separator: ";") : referenceImageURLs[0].path
            args += ["-i", imgArg]
        } else if let char = selectedCharacterProfile {
            args += ["-i", char.cropPath]
        }

        // Export reviewed intervals to temporary JSON to eliminate redundant re-scanning!
        let tempJsonURL = FileManager.default.temporaryDirectory.appendingPathComponent("focus_render_intervals_\(UUID().uuidString).json")
        let clipsDicts: [[String: Any]] = selected.map { clip in
            let src = clip.source.isEmpty ? video.path : clip.source
            return [
                "source": src,
                "start": clip.start,
                "end": clip.end,
                "avg_x": clip.avgX
            ]
        }
        if let jsonData = try? JSONSerialization.data(withJSONObject: clipsDicts) {
            try? jsonData.write(to: tempJsonURL)
            args += ["--intervals-json-file", tempJsonURL.path]
        }

        Task { [weak self] in
            guard let self else { return }
            do {
                try await ProcessBridge.shared.run(arguments: args) { [weak self] event in
                    guard let self else { return }
                    Task { @MainActor in
                        self.handleBridgeEvent(event)
                    }
                }
            } catch {
                await MainActor.run {
                    self.isProcessing = false
                    self.processingStatus = "Render error: \(error.localizedDescription)"
                    self.logLines.append("[ERROR] Render execution failed: \(error.localizedDescription)")
                    SleepManager.shared.allowSleep()
                    self.showToast("Render failed: \(error.localizedDescription)", icon: "xmark.octagon")
                }
            }
        }
    }

    public func cancel() {
        Task {
            await ProcessBridge.shared.cancel()
        }
        isProcessing = false
        processingStatus = "Cancelled"
        episodeProgressBadge = nil
        episodeProgressBar = 0.0
        currentEpisodeEta = nil
        seasonBatchEta = nil
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
        case .episodeProgress(let cur, let tot, let name, let epProg, let totProg, let epEta, let batchEta):
            self.episodeProgressBadge = "Episode [\(cur)/\(tot)]: \(name)"
            self.episodeProgressBar = epProg
            self.progressValue = totProg
            self.currentEpisodeEta = epEta
            self.seasonBatchEta = batchEta
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
            self.currentEpisodeEta = nil
            self.seasonBatchEta = nil
            self.processingStatus = "Scan complete! Found \(clips.count) clip(s)."
            self.logLines.append("[INFO] Scan finished successfully with \(clips.count) candidate clip(s).")
            SleepManager.shared.allowSleep()
            if settings.autoRender && !clips.isEmpty {
                startRender()
            }
        case .renderComplete(let out):
            self.isProcessing = false
            self.currentEpisodeEta = nil
            self.seasonBatchEta = nil
            self.progressValue = 1.0
            self.processingStatus = "Render complete! Saved to \(URL(fileURLWithPath: out).lastPathComponent)"
            self.logLines.append("[SUCCESS] Scenepack successfully rendered: \(out)")
            SleepManager.shared.allowSleep()
            NSSound(named: "Glass")?.play()
            showToast("Scenepack successfully rendered!", icon: "checkmark.seal.fill")
        case .audioTracks(let tracks):
            self.audioTracks = tracks + [AudioTrackItem(index: -1, label: "Keep All Audio Tracks (Multi-Audio)")]
        case .masterConcatComplete(let out):
            self.isProcessing = false
            self.currentEpisodeEta = nil
            self.seasonBatchEta = nil
            self.processingStatus = "Master scenepack created: \(URL(fileURLWithPath: out).lastPathComponent)"
            SleepManager.shared.allowSleep()
        case .error(let msg):
            self.isProcessing = false
            self.currentEpisodeEta = nil
            self.seasonBatchEta = nil
            self.processingStatus = "Error: \(msg)"
            SleepManager.shared.allowSleep()
            showToast("Error: \(msg)", icon: "xmark.octagon")
        }
    }

    public func generateFullDiagnosticReport() -> String {
        let hw = SystemHardwareInfo.current()
        let diag = engineDiagnostics
        let dateStr = ISO8601DateFormatter().string(from: Date())

        let inputNames = selectedVideoURLs.map { $0.lastPathComponent }.joined(separator: ", ")
        let inputStr = inputNames.isEmpty ? "None" : inputNames
        let refNames = referenceImageURLs.map { $0.lastPathComponent }.joined(separator: ", ")
        let refStr: String
        if !refNames.isEmpty {
            refStr = refNames
        } else if let profile = selectedCharacterProfile {
            refStr = "Character Profile #\(profile.id) (\(profile.count) sample frames)"
        } else {
            refStr = "All Detected Faces"
        }

        var report = """
        ================================================================================
        FOCUS AI STUDIO v2.4.0 — FULL SYSTEM & DIAGNOSTIC REPORT
        Generated: \(dateStr)
        ================================================================================

        [HARDWARE & SYSTEM SPECIFICATIONS]
        • Operating System     : macOS \(hw.osVersion)
        • Processor (CPU)      : \(hw.cpuSummary)
        • Physical Memory      : \(hw.ramSummary)
        • Primary Storage      : \(hw.diskSummary)
        • Hardware Accel       : Apple VideoToolbox (H.264 / HEVC / ProRes)

        [RUNTIME & ENGINE ENVIRONMENT]
        • Engine Type          : \(diag.engineType)
        • Engine Ready         : \(diag.isReady ? "YES (Verified)" : "NO (Incomplete)")
        • Python Executable    : \(diag.pythonPath)
        • FFmpeg Binary Path   : \(diag.ffmpegPath ?? "Auto-Download / System")
        • FFprobe Binary Path  : \(ProcessBridge.resolveFFprobeExecutable() ?? "Auto-Download / System")
        • Power Sleep Inhibit  : \(settings.preventSleep ? "Active (IOKit Assertion)" : "Disabled")

        [ACTIVE SESSION CONFIGURATION]
        • Input Video(s)       : \(inputStr)
        • Target Reference     : \(refStr)
        • Detection Mode       : \(mode.rawValue) (\(mode.label))
        • Timing Margins       : Lead-In: \(String(format: "%.1f", settings.padBefore))s | Lead-Out: \(String(format: "%.1f", settings.padAfter))s | Cut Gap: \(String(format: "%.1f", settings.maxGap))s
        • Clip Duration Filter : Min Scene: \(String(format: "%.1f", settings.minScene))s | Scan Step: \(settings.frameSkip) frames
        • Face Distance Tol.   : \(String(format: "%.2f", settings.tolerance))
        • Video Compression    : Codec: \(settings.videoCodec.rawValue) | Container: .\(settings.containerFormat.fileExtension) | Quality: \(settings.quality.rawValue)
        • Output Aspect Ratio  : \(settings.aspect.rawValue)
        • Audio Track Index    : \(settings.audioTrackIndex == -1 ? "All Tracks (Multi-Audio)" : "Track \(settings.audioTrackIndex + 1)")
        • Voice Activity (VAD) : \(settings.vadEnabled ? "ON (Buffer: \(settings.vadBuffer)ms)" : "OFF")
        • Speaker Voice Filter : \(settings.vadSpeakerEnabled ? "ON (Cosine Threshold: \(String(format: "%.2f", settings.vadSpeakerThreshold)))" : "OFF")
        • Snap to Shot Cuts    : \(settings.snapCuts ? "ON" : "OFF")
        • Skip Intro / Outro   : Intro: \(settings.skipIntro ? "YES" : "NO") | Outro: \(settings.skipOutro ? "YES" : "NO") | Mode: \(settings.introMode)
        • Export Timeline XML  : \(settings.exportXml ? "YES (Premiere Pro / DaVinci XML)" : "NO")
        • Export Clips Folder  : \(settings.exportClipsFolder ? "YES (Individual Scenes)" : "NO")

        [RECENT LOG CONSOLE BUFFER (\(logLines.count) Lines)]
        """

        let recentLogs = logLines.suffix(120)
        if recentLogs.isEmpty {
            report += "\n(No log lines recorded in current session)\n"
        } else {
            report += "\n"
            for (idx, line) in recentLogs.enumerated() {
                report += String(format: "%03d: %@\n", idx + 1, line)
            }
        }
        report += "================================================================================\n"
        return report
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
