import SwiftUI

public struct TuningSectionView: View {
    @ObservedObject var appState: AppState

    public var body: some View {
        GlassCard(title: "Scene & Detection Tuning", icon: "slider.horizontal.3") {
            HStack(alignment: .top, spacing: 12) {
                // Column 1: Scene Timing & Dialogue Speech Intelligence
                VStack(spacing: 10) {
                    // 1A: Scene Timing & Cut Tolerance
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 6) {
                            Image(systemName: "clock")
                                .foregroundColor(appState.accentColor)
                                .font(.system(size: 11, weight: .bold))
                            Text(appState.localized("timing_margins"))
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.primary)
                        }

                        HStack(spacing: 8) {
                            TuningItem(label: appState.localized("pad_before"), value: $appState.settings.padBefore, unit: appState.localized("unit_seconds"), accentColor: appState.accentColor)
                            TuningItem(label: appState.localized("pad_after"), value: $appState.settings.padAfter, unit: appState.localized("unit_seconds"), accentColor: appState.accentColor)
                            TuningItem(label: appState.localized("gap_bridge"), value: $appState.settings.maxGap, unit: appState.localized("unit_seconds"), accentColor: appState.accentColor)
                            TuningItem(label: appState.localized("min_scene"), value: $appState.settings.minScene, unit: appState.localized("unit_seconds"), accentColor: appState.accentColor)
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(Color.primary.opacity(0.03))
                            .overlay(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                            )
                    )

                    // 1B: Dialogue & Audio Intelligence
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 6) {
                            Image(systemName: "waveform")
                                .foregroundColor(appState.accentColor)
                                .font(.system(size: 11, weight: .bold))
                            Text(appState.localized("dialogue_vad"))
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.primary)
                        }

                        VStack(alignment: .leading, spacing: 6) {
                            HStack(spacing: 12) {
                                Toggle(appState.localized("vad_speech"), isOn: $appState.settings.vadEnabled)
                                    .toggleStyle(.checkbox)
                                    .font(.system(size: 11, weight: .medium))

                                Spacer()

                                if appState.settings.vadEnabled {
                                    HStack(spacing: 4) {
                                        Text(appState.localized("buffer"))
                                            .font(.system(size: 10, weight: .semibold))
                                            .foregroundColor(.secondary)
                                        TextField("", value: $appState.settings.vadBuffer, formatter: NumberFormatter())
                                            .textFieldStyle(.roundedBorder)
                                            .font(.system(size: 11, weight: .medium, design: .monospaced))
                                            .frame(width: 46)
                                        Text(appState.localized("unit_ms"))
                                            .font(.system(size: 10, weight: .bold))
                                            .foregroundColor(appState.accentColor)
                                    }
                                }
                            }

                            if appState.settings.vadEnabled {
                                HStack(spacing: 10) {
                                    Toggle(appState.localized("voice_similarity"), isOn: $appState.settings.vadSpeakerEnabled)
                                        .toggleStyle(.checkbox)
                                        .font(.system(size: 11, weight: .medium))

                                    Spacer()

                                    if appState.settings.vadSpeakerEnabled {
                                        HStack(spacing: 6) {
                                            Slider(value: $appState.settings.vadSpeakerThreshold, in: 0.3...0.95, step: 0.01)
                                                .frame(width: 80)
                                            Text("\(Int(appState.settings.vadSpeakerThreshold * 100))%")
                                                .font(.system(size: 10, weight: .bold, design: .monospaced))
                                                .foregroundColor(appState.accentColor)
                                                .frame(width: 32, alignment: .trailing)
                                        }
                                    }
                                }
                            }

                            HStack(spacing: 8) {
                                Text(appState.localized("audio_track"))
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                Picker("", selection: $appState.settings.audioTrackIndex) {
                                    ForEach(appState.audioTracks) { track in
                                        Text(track.label).tag(track.index)
                                    }
                                }
                                .pickerStyle(.menu)
                                .frame(maxWidth: .infinity)
                            }
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(Color.primary.opacity(0.03))
                            .overlay(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                            )
                    )
                }
                .frame(maxWidth: .infinity)

                // Column 2: Video Framing, Codecs & Automations
                VStack(spacing: 10) {
                    // 2A: Framing & Master Video Export
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 6) {
                            Image(systemName: "film")
                                .foregroundColor(appState.accentColor)
                                .font(.system(size: 11, weight: .bold))
                            Text(appState.localized("scan_speed"))
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.primary)
                        }

                        // Row 1: Scan Interval, Aspect Ratio, Export Quality
                        HStack(spacing: 8) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(appState.localized("frame_skip"))
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                                HStack(spacing: 4) {
                                    TextField("", value: $appState.settings.frameSkip, formatter: NumberFormatter())
                                        .textFieldStyle(.roundedBorder)
                                        .font(.system(size: 11, weight: .medium, design: .monospaced))
                                        .frame(maxWidth: .infinity)
                                    Text(appState.localized("unit_frames"))
                                        .font(.system(size: 10, weight: .bold))
                                        .foregroundColor(appState.accentColor)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(appState.localized("aspect_ratio"))
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                                Picker("", selection: $appState.settings.aspect) {
                                    ForEach(AspectRatioOption.allCases) { opt in
                                        Text(opt.rawValue).tag(opt)
                                    }
                                }
                                .pickerStyle(.menu)
                                .frame(maxWidth: .infinity)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(appState.localized("export_quality"))
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                                Picker("", selection: $appState.settings.quality) {
                                    ForEach(ExportQualityOption.allCases) { opt in
                                        Text(opt.rawValue).tag(opt)
                                    }
                                }
                                .pickerStyle(.menu)
                                .frame(maxWidth: .infinity)
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }

                        // Row 2: Video Codec, Container Format
                        HStack(spacing: 8) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(appState.localized("video_codec"))
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                Picker("", selection: $appState.settings.videoCodec) {
                                    ForEach(VideoCodecOption.allCases) { opt in
                                        Text(opt.rawValue).tag(opt)
                                    }
                                }
                                .pickerStyle(.menu)
                                .frame(maxWidth: .infinity)
                                .onChange(of: appState.settings.videoCodec) { newCodec in
                                    if newCodec == .prores && appState.settings.containerFormat == .mp4 {
                                        appState.settings.containerFormat = .mov
                                        appState.updateOutputContainerExtension(.mov)
                                        appState.showToast("ProRes: Container switched to QuickTime MOV", icon: "video.badge.checkmark")
                                    }
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)

                            VStack(alignment: .leading, spacing: 4) {
                                Text(appState.localized("container_format"))
                                    .font(.system(size: 10, weight: .semibold))
                                    .foregroundColor(.secondary)
                                Picker("", selection: $appState.settings.containerFormat) {
                                    ForEach(ContainerFormatOption.allCases) { opt in
                                        Text(opt.rawValue).tag(opt)
                                    }
                                }
                                .pickerStyle(.menu)
                                .frame(maxWidth: .infinity)
                                .onChange(of: appState.settings.containerFormat) { newFormat in
                                    appState.updateOutputContainerExtension(newFormat)
                                }
                            }
                            .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(Color.primary.opacity(0.03))
                            .overlay(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                            )
                    )

                    // 2B: Pipeline Automations & NLE Export
                    VStack(alignment: .leading, spacing: 8) {
                        HStack(spacing: 6) {
                            Image(systemName: "sparkles")
                                .foregroundColor(appState.accentColor)
                                .font(.system(size: 11, weight: .bold))
                            Text(appState.localized("automation_audio"))
                                .font(.system(size: 11, weight: .bold))
                                .foregroundColor(.primary)
                        }

                        VStack(alignment: .leading, spacing: 8) {
                            HStack(spacing: 10) {
                                Toggle(appState.localized("snap_cuts"), isOn: $appState.settings.snapCuts)
                                    .toggleStyle(.checkbox)
                                    .font(.system(size: 11, weight: .medium))
                                    .help("Snap scene clip boundaries to camera cut changes")
                                    .frame(maxWidth: .infinity, alignment: .leading)

                                Toggle(appState.localized("skip_intro"), isOn: $appState.settings.skipIntro)
                                    .toggleStyle(.checkbox)
                                    .font(.system(size: 11, weight: .medium))
                                    .frame(maxWidth: .infinity, alignment: .leading)

                                Toggle(appState.localized("skip_outro"), isOn: $appState.settings.skipOutro)
                                    .toggleStyle(.checkbox)
                                    .font(.system(size: 11, weight: .medium))
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }

                            HStack(spacing: 10) {
                                Toggle(appState.localized("auto_render"), isOn: $appState.settings.autoRender)
                                    .toggleStyle(.checkbox)
                                    .font(.system(size: 11, weight: .bold))
                                    .tint(appState.accentColor)
                                    .frame(maxWidth: .infinity, alignment: .leading)

                                Toggle(appState.localized("export_clips_folder"), isOn: $appState.settings.exportClipsFolder)
                                    .toggleStyle(.checkbox)
                                    .font(.system(size: 11, weight: .medium))
                                    .frame(maxWidth: .infinity, alignment: .leading)

                                Toggle(appState.localized("export_xml"), isOn: $appState.settings.exportXml)
                                    .toggleStyle(.checkbox)
                                    .font(.system(size: 11, weight: .medium))
                                    .help("Export .xml FCPXML timeline for Premiere Pro & DaVinci Resolve")
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                        }
                    }
                    .padding(10)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
                    .background(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .fill(Color.primary.opacity(0.03))
                            .overlay(
                                RoundedRectangle(cornerRadius: 10, style: .continuous)
                                    .stroke(Color.primary.opacity(0.08), lineWidth: 1)
                            )
                    )
                }
                .frame(maxWidth: .infinity)
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
                .lineLimit(1)

            HStack(spacing: 4) {
                TextField("", value: $value, format: .number.precision(.fractionLength(1)))
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 11, weight: .medium, design: .monospaced))
                    .frame(maxWidth: .infinity)

                Text(unit)
                    .font(.system(size: 10, weight: .bold))
                    .foregroundColor(accentColor)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }
}
