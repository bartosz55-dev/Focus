import Foundation

public struct CustomPreset: Identifiable, Codable, Sendable {
    public var id: String { name }
    public let name: String
    public var settings: ScanSettings

    public init(name: String, settings: ScanSettings) {
        self.name = name
        self.settings = settings
    }
}

public enum PresetManager {
    public static var presetsFileURL: URL {
        FileManager.default.homeDirectoryForCurrentUser.appendingPathComponent(".focus_presets.json")
    }

    public static func loadPresets() -> [String: [String: Any]] {
        let url = presetsFileURL
        guard FileManager.default.fileExists(atPath: url.path) else { return [:] }
        do {
            let data = try Data(contentsOf: url)
            if let json = try JSONSerialization.jsonObject(with: data) as? [String: [String: Any]] {
                return json
            }
        } catch {
            print("Failed to load presets: \(error)")
        }
        return [:]
    }

    public static func savePreset(name: String, settings: ScanSettings) {
        var presets = loadPresets()
        let dict: [String: Any] = [
            "pad_before": settings.padBefore,
            "pad_after": settings.padAfter,
            "max_gap": settings.maxGap,
            "min_scene": settings.minScene,
            "frame_skip": settings.frameSkip,
            "aspect": settings.aspect.rawValue,
            "quality": settings.quality.rawValue,
            "vad_enabled": settings.vadEnabled,
            "vad_buffer": settings.vadBuffer,
            "vad_speaker": settings.vadSpeakerEnabled,
            "vad_threshold": Int(settings.vadSpeakerThreshold * 100),
            "skip_intro": settings.skipIntro,
            "skip_outro": settings.skipOutro,
            "intro_mode": settings.introMode,
            "intro_dur": settings.introDuration,
            "auto_render": settings.autoRender
        ]
        presets[name] = dict
        do {
            let data = try JSONSerialization.data(withJSONObject: presets, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: presetsFileURL, options: .atomic)
        } catch {
            print("Failed to save preset: \(error)")
        }
    }

    public static func deletePreset(name: String) {
        var presets = loadPresets()
        presets.removeValue(forKey: name)
        do {
            let data = try JSONSerialization.data(withJSONObject: presets, options: [.prettyPrinted, .sortedKeys])
            try data.write(to: presetsFileURL, options: .atomic)
        } catch {
            print("Failed to delete preset: \(error)")
        }
    }
}
