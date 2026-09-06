import SwiftUI

public struct ProgressCardView: View {
    @ObservedObject var appState: AppState

    public var body: some View {
        GlassCard {
            VStack(spacing: 12) {
                HStack(spacing: 14) {
                    // Main Action Button
                    Button(action: {
                        appState.startScan()
                    }) {
                        HStack(spacing: 8) {
                            Image(systemName: "wand.and.rays")
                                .font(.system(size: 14, weight: .bold))
                            Text(appState.isProcessing ? "Processing Video..." : "Scan and Analyze Video")
                                .font(.system(size: 13, weight: .bold))
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.purple)
                    .disabled(appState.isProcessing)

                    if appState.isProcessing {
                        Button("Cancel") {
                            appState.cancel()
                        }
                        .buttonStyle(.bordered)
                        .controlSize(.large)
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
                                .background(Capsule().fill(Color.purple.opacity(0.3)))
                        }

                        Text(appState.processingStatus)
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.secondary)
                            .lineLimit(1)

                        Spacer()

                        Text("\(Int(appState.progressValue * 100))%")
                            .font(.system(size: 11, weight: .bold))
                            .foregroundColor(.purple)
                    }

                    ProgressView(value: appState.progressValue, total: 1.0)
                        .tint(.purple)
                }
            }
        }
    }
}
