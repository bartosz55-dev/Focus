import SwiftUI

public struct ModeSwitchView: View {
    @ObservedObject var appState: AppState

    public init(appState: AppState) {
        self.appState = appState
    }

    public var body: some View {
        HStack(spacing: 4) {
            // Mode A: Live Action / Real Faces
            Button(action: {
                withAnimation(.spring(response: 0.28, dampingFraction: 0.8)) {
                    appState.mode = .realFaces
                }
            }) {
                HStack(spacing: 6) {
                    Image(systemName: "person.crop.rectangle")
                        .font(.system(size: 11, weight: .semibold))
                    Text(appState.localized("mode_real_faces"))
                        .font(.system(size: 11, weight: appState.mode == .realFaces ? .bold : .medium))
                }
                .foregroundColor(appState.mode == .realFaces ? .white : .secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .contentShape(Rectangle())
                .background(
                    RoundedRectangle(cornerRadius: 6, style: .continuous)
                        .fill(appState.mode == .realFaces ? appState.accentColor : Color.clear)
                )
            }
            .buttonStyle(.plain)

            // Mode B: 2D Animation / Anime
            Button(action: {
                withAnimation(.spring(response: 0.28, dampingFraction: 0.8)) {
                    appState.mode = .anime
                }
            }) {
                HStack(spacing: 6) {
                    Image(systemName: "sparkles.tv")
                        .font(.system(size: 11, weight: .semibold))
                    Text(appState.localized("mode_anime"))
                        .font(.system(size: 11, weight: appState.mode == .anime ? .bold : .medium))
                }
                .foregroundColor(appState.mode == .anime ? .white : .secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .contentShape(Rectangle())
                .background(
                    RoundedRectangle(cornerRadius: 6, style: .continuous)
                        .fill(appState.mode == .anime ? appState.accentColor : Color.clear)
                )
            }
            .buttonStyle(.plain)
        }
        .padding(3)
        .background(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor).opacity(0.7))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(Color.white.opacity(0.1), lineWidth: 1)
                )
        )
    }
}
