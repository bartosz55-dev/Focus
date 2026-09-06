import SwiftUI

public struct TuningSectionView: View {
    @ObservedObject var appState: AppState

    public var body: some View {
        GlassCard(title: "Scene & Detection Tuning", icon: "slider.horizontal.3") {
            VStack(spacing: 12) {
                // Section A: Timing & Scene Margins
                VStack(alignment: .leading, spacing: 8) {
                    Label("⏱️ Timing & Scene Margins", systemImage: "clock")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.purple)

                    HStack(spacing: 12) {
                        TuningItem(label: "Pad Before", value: $appState.settings.padBefore, unit: "s", step: 0.5, min: 0.0)
                        TuningItem(label: "Pad After", value: $appState.settings.padAfter, unit: "s", step: 0.5, min: 0.0)
                        TuningItem(label: "Gap Bridge", value: $appState.settings.maxGap, unit: "s", step: 0.5, min: 0.0)
                        TuningItem(label: "Min Scene", value: $appState.settings.minScene, unit: "s", step: 0.5, min: 0.5)
                    }
                }
                .padding(10)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color.white.opacity(0.04)))

                // Section B: Scan Speed & Framing
                VStack(alignment: .leading, spacing: 8) {
                    Label("🎯 Scan Speed & Video Framing", systemImage: "speedometer")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.purple)

                    HStack(spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text("Frame Skip")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.secondary)
                            HStack {
                                TextField("", value: $appState.settings.frameSkip, formatter: NumberFormatter())
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 55)
                                Text("frames")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(.purple)
                            }
                        }

                        VStack(alignment: .leading, spacing: 4) {
                            Text("Aspect Ratio")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.secondary)
                            Picker("", selection: $appState.settings.aspect) {
                                ForEach(AspectRatioOption.allCases) { opt in
                                    Text(opt.rawValue).tag(opt)
                                }
                            }
                            .pickerStyle(.menu)
                        }

                        VStack(alignment: .leading, spacing: 4) {
                            Text("Export Quality")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.secondary)
                            Picker("", selection: $appState.settings.quality) {
                                ForEach(ExportQualityOption.allCases) { opt in
                                    Text(opt.rawValue).tag(opt)
                                }
                            }
                            .pickerStyle(.menu)
                        }
                    }
                }
                .padding(10)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color.white.opacity(0.04)))

                // Section C: Dialogue Protection (VAD) & Voice Verification
                VStack(alignment: .leading, spacing: 8) {
                    Label("🎙️ Dialogue Protection & Voice Verification", systemImage: "waveform")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.purple)

                    HStack(spacing: 16) {
                        Toggle("VAD Speech Protection", isOn: $appState.settings.vadEnabled)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .medium))

                        if appState.settings.vadEnabled {
                            HStack(spacing: 4) {
                                Text("Buffer:")
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                TextField("", value: $appState.settings.vadBuffer, formatter: NumberFormatter())
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 55)
                                Text("ms")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(.purple)
                            }

                            Toggle("Voice Similarity", isOn: $appState.settings.vadSpeakerEnabled)
                                .toggleStyle(.checkbox)
                                .font(.system(size: 11, weight: .medium))

                            if appState.settings.vadSpeakerEnabled {
                                HStack(spacing: 6) {
                                    Slider(value: $appState.settings.vadSpeakerThreshold, in: 0.3...0.95, step: 0.01)
                                        .frame(width: 90)
                                    Text("\(Int(appState.settings.vadSpeakerThreshold * 100))%")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(.purple)
                                }
                            }
                        }
                    }
                }
                .padding(10)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color.white.opacity(0.04)))

                // Section D: Automation & Audio
                VStack(alignment: .leading, spacing: 8) {
                    Label("⏭️ Automation & Audio Tracks", systemImage: "forward.fill")
                        .font(.system(size: 11, weight: .bold))
                        .foregroundColor(.purple)

                    HStack(spacing: 16) {
                        Toggle("Skip Intro", isOn: $appState.settings.skipIntro)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .medium))

                        Toggle("Skip Outro", isOn: $appState.settings.skipOutro)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .medium))

                        Toggle("Auto-Render after scan", isOn: $appState.settings.autoRender)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .bold))
                            .tint(.purple)

                        Spacer()

                        HStack(spacing: 6) {
                            Text("Audio Track:")
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.secondary)
                            Picker("", selection: $appState.settings.audioTrackIndex) {
                                ForEach(appState.audioTracks) { track in
                                    Text(track.label).tag(track.index)
                                }
                            }
                            .pickerStyle(.menu)
                            .frame(maxWidth: 220)
                        }
                    }
                }
                .padding(10)
                .background(RoundedRectangle(cornerRadius: 8).fill(Color.white.opacity(0.04)))
            }
        }
    }
}

struct TuningItem: View {
    let label: String
    @Binding var value: Double
    let unit: String
    let step: Double
    let min: Double

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 10, weight: .semibold))
                .foregroundColor(.secondary)

            HStack(spacing: 4) {
                TextField("", value: $value, format: .number.precision(.fractionLength(1)))
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 55)

                Text(unit)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(.purple)
            }
        }
    }
}
