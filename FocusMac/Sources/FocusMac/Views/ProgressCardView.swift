import SwiftUI

public struct ProgressCardView: View {
    @ObservedObject var appState: AppState

    @State private var isPulsing: Bool = false

    public var body: some View {
        GlassCard {
            VStack(spacing: 14) {
                HStack(spacing: 14) {
                    // Main Action Button with Apple Spring Physics
                    Button(action: {
                        appState.startScan()
                    }) {
                        HStack(spacing: 8) {
                            Image(systemName: appState.isProcessing ? "hourglass" : "wand.and.rays")
                                .font(.system(size: 14, weight: .bold))
                                .rotationEffect(Angle.degrees(appState.isProcessing && isPulsing ? 180 : 0))
                                .animation(
                                    appState.isProcessing
                                        ? Animation.linear(duration: 1.5).repeatForever(autoreverses: false)
                                        : .default,
                                    value: isPulsing
                                )

                            Text(appState.isProcessing ? appState.processingStatus : appState.localized("scan_button"))
                                .font(.system(size: 13, weight: .bold))
                        }
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                .fill(
                                    LinearGradient(
                                        colors: [
                                            appState.accentColor,
                                            appState.accentColor.opacity(0.85)
                                        ],
                                        startPoint: .top,
                                        endPoint: .bottom
                                    )
                                )
                                .shadow(color: appState.accentColor.opacity(appState.isProcessing ? 0.6 : 0.25), radius: appState.isProcessing ? 10 : 4, x: 0, y: 2)
                        )
                    }
                    .buttonStyle(AppleSpringButtonStyle())
                    .disabled(appState.isProcessing)

                    if appState.isProcessing {
                        Button(action: {
                            appState.cancel()
                        }) {
                            Text(appState.localized("cancel_button"))
                                .font(.system(size: 12, weight: .semibold))
                                .foregroundColor(.red)
                                .padding(.horizontal, 14)
                                .padding(.vertical, 9)
                                .background(
                                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                                        .fill(Color.red.opacity(0.12))
                                        .overlay(
                                            RoundedRectangle(cornerRadius: 8, style: .continuous)
                                                .stroke(Color.red.opacity(0.3), lineWidth: 1)
                                        )
                                )
                        }
                        .buttonStyle(AppleSpringButtonStyle())
                        .transition(.scale.combined(with: .opacity))
                    }
                }

                // Progress Bar and ETA
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        if let badge = appState.episodeProgressBadge {
                            Text(badge)
                                .font(.system(size: 11, weight: .bold))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 2)
                                .background(Capsule().fill(appState.accentColor.opacity(0.3)))
                        }

                        Text(appState.processingStatus)
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.secondary)
                            .lineLimit(1)

                        Spacer()

                        Text("\(Int(appState.progressValue * 100))%")
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundColor(appState.accentColor)
                    }

                    // Fluid Animated Progress Bar
                    GeometryReader { geo in
                        ZStack(alignment: .leading) {
                            RoundedRectangle(cornerRadius: 4)
                                .fill(Color.white.opacity(0.1))
                                .frame(height: 6)

                            RoundedRectangle(cornerRadius: 4)
                                .fill(
                                    LinearGradient(
                                        colors: [appState.accentColor, appState.accentColor.opacity(0.8)],
                                        startPoint: .leading,
                                        endPoint: .trailing
                                    )
                                )
                                .frame(width: max(0, min(geo.size.width * CGFloat(appState.progressValue), geo.size.width)), height: 6)
                                .animation(.spring(response: 0.35, dampingFraction: 0.8), value: appState.progressValue)
                        }
                    }
                    .frame(height: 6)
                }
            }
        }
        .onChange(of: appState.isProcessing) { processing in
            if processing {
                isPulsing = true
            } else {
                isPulsing = false
            }
        }
    }
}
