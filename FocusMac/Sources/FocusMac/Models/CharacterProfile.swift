import Foundation

public struct CharacterProfile: Identifiable, Hashable, Codable, Sendable {
    public let id: Int
    public let count: Int
    public let cropPath: String

    enum CodingKeys: String, CodingKey {
        case id
        case count
        case cropPath = "crop_path"
    }

    public init(id: Int, count: Int, cropPath: String) {
        self.id = id
        self.count = count
        self.cropPath = cropPath
    }
}
