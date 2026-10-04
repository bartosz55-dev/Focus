import Foundation

public enum DetectionMode: String, CaseIterable, Identifiable, Codable, Sendable {
    case anime = "Anime"
    case realFaces = "Real Faces"

    public var id: String { rawValue }
    
    public var icon: String {
        switch self {
        case .anime: return "sparkles.tv"
        case .realFaces: return "person.crop.rectangle.stack"
        }
    }
    
    public var label: String {
        switch self {
        case .anime: return "2D Animation / Anime"
        case .realFaces: return "Live Action / 3D"
        }
    }
}

public enum AspectRatioOption: String, CaseIterable, Identifiable, Codable, Sendable {
    case original = "16:9 Original"
    case verticalAutoTrack = "9:16 Vertical (Auto-Track)"
    case verticalBlurred = "9:16 Blurred Background"

    public var id: String { rawValue }
}

public enum ExportQualityOption: String, CaseIterable, Identifiable, Codable, Sendable {
    case matchSource = "Auto (Match Source Bitrate)"
    case maximum = "Maximum (Master / CRF 14 / 35 Mbps)"
    case high = "High (Crystal Clear / CRF 16 / 20 Mbps)"
    case medium = "Medium (Standard / CRF 20 / 10 Mbps)"
    case draft = "Draft / Fast (CRF 24 / 4 Mbps)"

    public var id: String { rawValue }

    public init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        let raw = try container.decode(String.self)
        self = Self.parse(raw)
    }

    public static func parse(_ str: String) -> ExportQualityOption {
        let lower = str.lowercased()
        if lower.contains("max") || lower.contains("master") || lower.contains("14") {
            return .maximum
        } else if lower.contains("high") || lower.contains("16") || lower.contains("17") || lower.contains("crystal") {
            return .high
        } else if lower.contains("draft") || lower.contains("low") || lower.contains("24") || lower.contains("fast") {
            return .draft
        } else if lower.contains("medium") || lower.contains("standard") || lower.contains("20") {
            return .medium
        } else {
            return .matchSource
        }
    }
}

public enum VideoCodecOption: String, CaseIterable, Identifiable, Codable, Sendable {
    case auto = "Auto (Fastest Hardware H.264)"
    case h264 = "H.264 / AVC (Universal Compatibility)"
    case hevc = "H.265 / HEVC (High Efficiency)"
    case av1 = "AV1 (Next-Gen Open Standard)"
    case prores = "Apple ProRes (Editing Master)"

    public var id: String { rawValue }

    public var cliValue: String {
        switch self {
        case .auto: return "auto"
        case .h264: return "h264"
        case .hevc: return "hevc"
        case .av1: return "av1"
        case .prores: return "prores"
        }
    }

    public static func parse(_ str: String) -> VideoCodecOption {
        let lower = str.lowercased()
        if lower.contains("auto") {
            return .auto
        } else if lower.contains("hevc") || lower.contains("265") {
            return .hevc
        } else if lower.contains("av1") {
            return .av1
        } else if lower.contains("prores") {
            return .prores
        } else if lower.contains("264") || lower.contains("avc") {
            return .h264
        } else {
            return .auto
        }
    }
}

public enum ContainerFormatOption: String, CaseIterable, Identifiable, Codable, Sendable {
    case mp4 = "MP4 (.mp4)"
    case mkv = "MKV (.mkv)"
    case mov = "MOV (.mov)"

    public var id: String { rawValue }

    public var fileExtension: String {
        switch self {
        case .mp4: return "mp4"
        case .mkv: return "mkv"
        case .mov: return "mov"
        }
    }

    public static func parse(_ str: String) -> ContainerFormatOption {
        let lower = str.lowercased()
        if lower.contains("mkv") {
            return .mkv
        } else if lower.contains("mov") {
            return .mov
        } else {
            return .mp4
        }
    }
}

public struct AudioTrackItem: Identifiable, Hashable, Codable, Sendable {
    public let index: Int
    public let label: String
    
    public var id: Int { index }
}

public struct ScanSettings: Codable, Sendable {
    public var padBefore: Double = 2.0
    public var padAfter: Double = 2.0
    public var maxGap: Double = 1.5
    public var minScene: Double = 1.0
    public var frameSkip: Int = 15
    public var vadEnabled: Bool = true
    public var vadBuffer: Int = 300
    public var vadSpeakerEnabled: Bool = true
    public var vadSpeakerThreshold: Double = 0.68
    public var skipIntro: Bool = true
    public var skipOutro: Bool = false
    public var introMode: String = "Auto Chapters (MKV/MP4)"
    public var introDuration: Double = 90.0
    public var aspect: AspectRatioOption = .original
    public var quality: ExportQualityOption = .matchSource
    public var videoCodec: VideoCodecOption = .auto
    public var containerFormat: ContainerFormatOption = .mp4
    public var audioTrackIndex: Int = 0
    public var autoRender: Bool = false
    public var exportClipsFolder: Bool = false
    public var exportXml: Bool = false
    public var snapCuts: Bool = true
    public var preventSleep: Bool = true

    public init() {}
}
