import SwiftUI

/// Apple physics spring button style providing subtle tactile depression and recovery.
public struct AppleSpringButtonStyle: ButtonStyle {
    public init() {}

    public func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .scaleEffect(configuration.isPressed ? 0.95 : 1.0)
            .animation(.spring(response: 0.26, dampingFraction: 0.72), value: configuration.isPressed)
    }
}

/// Liquid Glass frosted capsule container matching the native macOS Sequoia / Tahoe design language.
public struct LiquidGlassCapsule<Content: View>: View {
    let content: Content

    public init(@ViewBuilder content: () -> Content) {
        self.content = content()
    }

    public var body: some View {
        content
            .padding(.horizontal, 6)
            .padding(.vertical, 4)
            .background(
                Capsule(style: .continuous)
                    .fill(.ultraThinMaterial)
                    .overlay(
                        Capsule(style: .continuous)
                            .strokeBorder(
                                LinearGradient(
                                    colors: [
                                        Color.white.opacity(0.32),
                                        Color.white.opacity(0.10),
                                        Color.black.opacity(0.18)
                                    ],
                                    startPoint: .top,
                                    endPoint: .bottom
                                ),
                                lineWidth: 1
                            )
                    )
                    .shadow(color: Color.black.opacity(0.22), radius: 8, x: 0, y: 3)
            )
    }
}

/// Interactive button designed for placement inside a Liquid Glass capsule toolbar.
public struct LiquidGlassButton: View {
    let icon: String
    let title: String?
    let tooltip: String
    let isActive: Bool
    let accentColor: Color
    let action: () -> Void

    @State private var isHovered: Bool = false

    public init(
        icon: String,
        title: String? = nil,
        tooltip: String,
        isActive: Bool = false,
        accentColor: Color = .purple,
        action: @escaping () -> Void
    ) {
        self.icon = icon
        self.title = title
        self.tooltip = tooltip
        self.isActive = isActive
        self.accentColor = accentColor
        self.action = action
    }

    public var body: some View {
        Button(action: action) {
            HStack(spacing: 5) {
                Image(systemName: icon)
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(isActive ? .white : (isHovered ? .primary : .secondary))

                if let title = title {
                    Text(title)
                        .font(.system(size: 11, weight: isActive ? .semibold : .medium))
                        .foregroundColor(isActive ? .white : (isHovered ? .primary : .secondary))
                        .lineLimit(1)
                        .fixedSize(horizontal: true, vertical: false)
                }
            }
            .padding(.horizontal, title != nil ? 10 : 8)
            .padding(.vertical, 5)
            .contentShape(Rectangle())
            .background(
                RoundedRectangle(cornerRadius: 6, style: .continuous)
                    .fill(isActive ? accentColor : (isHovered ? Color.white.opacity(0.14) : Color.clear))
            )
        }
        .buttonStyle(AppleSpringButtonStyle())
        .help(tooltip)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}
