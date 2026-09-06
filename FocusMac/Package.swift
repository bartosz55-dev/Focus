// swift-tools-version: 5.9
import PackageDescription

let package = Package(
    name: "FocusMac",
    platforms: [
        .macOS(.v13)
    ],
    products: [
        .executable(
            name: "FocusMac",
            targets: ["FocusMac"]
        )
    ],
    targets: [
        .executableTarget(
            name: "FocusMac",
            path: "Sources/FocusMac"
        )
    ]
)
