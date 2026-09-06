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
    case high = "High (CRF 16)"
    case medium = "Medium (CRF 20)"
    case low = "Low (CRF 24)"

    public var id: String { rawValue }
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
    public var audioTrackIndex: Int = 0
    public var autoRender: Bool = false
    public var preventSleep: Bool = true

    public init() {}
}
