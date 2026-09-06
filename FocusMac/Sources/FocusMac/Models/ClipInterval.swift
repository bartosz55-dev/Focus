import Foundation

public struct ClipInterval: Identifiable, Hashable, Codable, Sendable {
    public let id: Int
    public let source: String
    public let start: Double
    public let end: Double
    public let duration: Double
    public let avgX: Double
    public let thumbPath: String
    public var isSelected: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case source
        case start
        case end
        case duration
        case avgX = "avg_x"
        case thumbPath = "thumb_path"
        case isSelected
    }

    public init(
        id: Int,
        source: String = "",
        start: Double,
        end: Double,
        duration: Double,
        avgX: Double = 0.5,
        thumbPath: String = "",
        isSelected: Bool = true
    ) {
        self.id = id
        self.source = source
        self.start = start
        self.end = end
        self.duration = duration
        self.avgX = avgX
        self.thumbPath = thumbPath
        self.isSelected = isSelected
    }

    public init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        self.id = try container.decode(Int.self, forKey: .id)
        self.source = (try? container.decode(String.self, forKey: .source)) ?? ""
        self.start = try container.decode(Double.self, forKey: .start)
        self.end = try container.decode(Double.self, forKey: .end)
        self.duration = (try? container.decode(Double.self, forKey: .duration)) ?? max(0.0, end - start)
        self.avgX = (try? container.decode(Double.self, forKey: .avgX)) ?? 0.5
        self.thumbPath = (try? container.decode(String.self, forKey: .thumbPath)) ?? ""
        self.isSelected = (try? container.decode(Bool.self, forKey: .isSelected)) ?? true
    }
}
