import SwiftUI

public struct ToastBanner: View {
    public let message: String
    public let icon: String

    public var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .foregroundColor(.purple)
                .font(.system(size: 15, weight: .bold))
            Text(message)
                .font(.system(size: 13, weight: .medium))
                .foregroundColor(.white)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background {
            Capsule(style: .continuous)
                .fill(Color(nsColor: .windowBackgroundColor).opacity(0.85))
                .background(.ultraThinMaterial)
                .overlay(
                    Capsule(style: .continuous)
                        .stroke(Color.purple.opacity(0.5), lineWidth: 1)
                )
                .shadow(color: Color.purple.opacity(0.3), radius: 12, x: 0, y: 4)
        }
        .transition(.asymmetric(
            insertion: .move(edge: .top).combined(with: .opacity),
            removal: .move(edge: .top).combined(with: .opacity)
        ))
    }
}
