import SwiftUI

public struct ModeSwitchView: View {
    @ObservedObject var appState: AppState

    public init(appState: AppState) {
        self.appState = appState
    }

    public var body: some View {
        HStack(spacing: 10) {
            // Option 1: Live Action / Real Faces
            Button(action: {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.75)) {
                    appState.mode = .realFaces
                }
            }) {
                HStack(spacing: 6) {
                    Image(systemName: "person.crop.rectangle")
                        .font(.system(size: 11, weight: .semibold))
                    Text(appState.localized("mode_real_faces"))
                        .font(.system(size: 11, weight: appState.mode == .realFaces ? .bold : .regular))
                }
                .foregroundColor(appState.mode == .realFaces ? .white : .secondary)
            }
            .buttonStyle(.plain)

            // Native Apple Switch Toggle
            Toggle("", isOn: Binding(
                get: { appState.mode == .anime },
                set: { isAnime in
                    withAnimation(.spring(response: 0.3, dampingFraction: 0.75)) {
                        appState.mode = isAnime ? .anime : .realFaces
                    }
                }
            ))
            .toggleStyle(.switch)
            .tint(appState.accentColor)
            .labelsHidden()

            // Option 2: 2D Animation / Anime
            Button(action: {
                withAnimation(.spring(response: 0.3, dampingFraction: 0.75)) {
                    appState.mode = .anime
                }
            }) {
                HStack(spacing: 6) {
                    Image(systemName: "sparkles.tv")
                        .font(.system(size: 11, weight: .semibold))
                    Text(appState.localized("mode_anime"))
                        .font(.system(size: 11, weight: appState.mode == .anime ? .bold : .regular))
                }
                .foregroundColor(appState.mode == .anime ? appState.accentColor : .secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background {
            Capsule(style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor).opacity(0.6))
                .overlay(
                    Capsule(style: .continuous)
                        .stroke(Color.white.opacity(0.12), lineWidth: 1)
                )
        }
    }
}
