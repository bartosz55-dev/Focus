import SwiftUI

public struct ToastBanner: View {
    public let message: String
    public let icon: String
    public var accentColor: Color = .purple

    public init(message: String, icon: String, accentColor: Color = .purple) {
        self.message = message
        self.icon = icon
        self.accentColor = accentColor
    }

    public var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .foregroundColor(accentColor)
                .font(.system(size: 14, weight: .bold))
            Text(message)
                .font(.system(size: 12, weight: .medium))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 18)
        .padding(.vertical, 9)
        .background {
            Capsule(style: .continuous)
                .fill(.ultraThinMaterial)
                .overlay(
                    Capsule(style: .continuous)
                        .fill(Color.black.opacity(0.5))
                )
                .overlay(
                    Capsule(style: .continuous)
                        .stroke(accentColor.opacity(0.6), lineWidth: 1)
                )
                .shadow(color: Color.black.opacity(0.3), radius: 10, x: 0, y: 5)
        }
        .transition(.asymmetric(
            insertion: .move(edge: .top).combined(with: .opacity),
            removal: .move(edge: .top).combined(with: .opacity)
        ))
    }
}
