import SwiftUI

public struct TuningSectionView: View {
    @ObservedObject var appState: AppState

    private let gridColumns = [
        GridItem(.flexible(), spacing: 12),
        GridItem(.flexible(), spacing: 12)
    ]

    public var body: some View {
        GlassCard(title: "Scene & Detection Tuning", icon: "slider.horizontal.3") {
            LazyVGrid(columns: gridColumns, spacing: 12) {
                // Section 1: Timing & Scene Margins
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 6) {
                        Image(systemName: "clock")
                            .foregroundColor(appState.accentColor)
                            .font(.system(size: 12, weight: .bold))
                        Text(appState.localized("timing_margins"))
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(.primary)
                    }

                    HStack(spacing: 8) {
                        TuningItem(label: appState.localized("pad_before"), value: $appState.settings.padBefore, unit: "s", accentColor: appState.accentColor)
                        TuningItem(label: appState.localized("pad_after"), value: $appState.settings.padAfter, unit: "s", accentColor: appState.accentColor)
                        TuningItem(label: appState.localized("gap_bridge"), value: $appState.settings.maxGap, unit: "s", accentColor: appState.accentColor)
                        TuningItem(label: appState.localized("min_scene"), value: $appState.settings.minScene, unit: "s", accentColor: appState.accentColor)
                    }
                }
                .padding(12)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color.white.opacity(0.03))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                )

                // Section 2: Scan Speed & Video Framing
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 6) {
                        Image(systemName: "speedometer")
                            .foregroundColor(appState.accentColor)
                            .font(.system(size: 12, weight: .bold))
                        Text(appState.localized("scan_speed"))
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(.primary)
                    }

                    HStack(spacing: 12) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(appState.localized("frame_skip"))
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.secondary)
                            HStack(spacing: 4) {
                                TextField("", value: $appState.settings.frameSkip, formatter: NumberFormatter())
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 48)
                                Text("fps")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(appState.accentColor)
                            }
                        }

                        VStack(alignment: .leading, spacing: 4) {
                            Text(appState.localized("aspect_ratio"))
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
                            Text(appState.localized("export_quality"))
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
                .padding(12)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color.white.opacity(0.03))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                )

                // Section 3: Dialogue Protection & Voice Verification
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 6) {
                        Image(systemName: "waveform")
                            .foregroundColor(appState.accentColor)
                            .font(.system(size: 12, weight: .bold))
                        Text(appState.localized("dialogue_vad"))
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(.primary)
                    }

                    HStack(spacing: 12) {
                        Toggle(appState.localized("vad_speech"), isOn: $appState.settings.vadEnabled)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .medium))

                        if appState.settings.vadEnabled {
                            HStack(spacing: 4) {
                                Text(appState.localized("buffer"))
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                TextField("", value: $appState.settings.vadBuffer, formatter: NumberFormatter())
                                    .textFieldStyle(.roundedBorder)
                                    .frame(width: 48)
                                Text("ms")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(appState.accentColor)
                            }

                            Toggle(appState.localized("voice_similarity"), isOn: $appState.settings.vadSpeakerEnabled)
                                .toggleStyle(.checkbox)
                                .font(.system(size: 11, weight: .medium))

                            if appState.settings.vadSpeakerEnabled {
                                HStack(spacing: 4) {
                                    Slider(value: $appState.settings.vadSpeakerThreshold, in: 0.3...0.95, step: 0.01)
                                        .frame(width: 70)
                                    Text("\(Int(appState.settings.vadSpeakerThreshold * 100))%")
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(appState.accentColor)
                                }
                            }
                        }
                    }
                }
                .padding(12)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color.white.opacity(0.03))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                )

                // Section 4: Automation & Audio Tracks
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 6) {
                        Image(systemName: "forward.fill")
                            .foregroundColor(appState.accentColor)
                            .font(.system(size: 12, weight: .bold))
                        Text(appState.localized("automation_audio"))
                            .font(.system(size: 12, weight: .bold))
                            .foregroundColor(.primary)
                    }

                    HStack(spacing: 12) {
                        Toggle(appState.localized("skip_intro"), isOn: $appState.settings.skipIntro)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .medium))

                        Toggle(appState.localized("skip_outro"), isOn: $appState.settings.skipOutro)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .medium))

                        Toggle(appState.localized("auto_render"), isOn: $appState.settings.autoRender)
                            .toggleStyle(.checkbox)
                            .font(.system(size: 11, weight: .bold))
                            .tint(appState.accentColor)

                        Spacer()

                        HStack(spacing: 4) {
                            Text(appState.localized("audio_track"))
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.secondary)
                            Picker("", selection: $appState.settings.audioTrackIndex) {
                                ForEach(appState.audioTracks) { track in
                                    Text(track.label).tag(track.index)
                                }
                            }
                            .pickerStyle(.menu)
                            .frame(maxWidth: 160)
                        }
                    }
                }
                .padding(12)
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color.white.opacity(0.03))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                )
            }
        }
    }
}

struct TuningItem: View {
    let label: String
    @Binding var value: Double
    let unit: String
    let accentColor: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 10, weight: .semibold))
                .foregroundColor(.secondary)

            HStack(spacing: 4) {
                TextField("", value: $value, format: .number.precision(.fractionLength(1)))
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 48)

                Text(unit)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(accentColor)
            }
        }
    }
}
