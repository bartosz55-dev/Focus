import SwiftUI
import AVKit

public struct NativeVideoPlayerView: View {
    public let clip: ClipInterval
    public let videoURL: URL
    public let onDismiss: () -> Void

    @State private var player: AVPlayer?

    public var body: some View {
        VStack(spacing: 12) {
            HStack {
                Text("Clip Preview: \(String(format: "%.2fs - %.2fs (%.2fs)", clip.start, clip.end, clip.duration))")
                    .font(.system(size: 13, weight: .bold))
                Spacer()
                Button("Done") {
                    player?.pause()
                    onDismiss()
                }
                .buttonStyle(.borderedProminent)
                .tint(.purple)
                .controlSize(.small)
            }
            .padding(.horizontal, 16)
            .padding(.top, 14)

            if let player {
                VideoPlayer(player: player)
                    .frame(minWidth: 480, minHeight: 270)
                    .cornerRadius(8)
                    .padding(.horizontal, 16)
            } else {
                ProgressView()
                    .frame(width: 480, height: 270)
            }
        }
        .padding(.bottom, 16)
        .frame(width: 520, height: 340)
        .background(.ultraThinMaterial)
        .onAppear {
            setupPlayer()
        }
        .onDisappear {
            player?.pause()
            player = nil
        }
    }

    private func setupPlayer() {
        let p = AVPlayer(url: videoURL)
        let startTime = CMTime(seconds: clip.start, preferredTimescale: 600)
        p.seek(to: startTime, toleranceBefore: .zero, toleranceAfter: .zero)
        p.play()
        self.player = p
    }
}
