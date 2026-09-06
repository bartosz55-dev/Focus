import SwiftUI
import AppKit

public struct SettingsView: View {
    @ObservedObject var appState: AppState

    @State private var manualSearch: String = ""
    @State private var logFilter: String = "ALL"

    private let standardSwatches = [
        ("Violet", "#8B5CF6"),
        ("Blue", "#2563EB"),
        ("Emerald", "#10B981"),
        ("Indigo", "#6366F1"),
        ("Rose", "#EC4899"),
        ("Orange", "#F97316"),
        ("Crimson", "#EF4444"),
        ("Amber", "#F59E0B")
    ]

    public init(appState: AppState) {
        self.appState = appState
    }

    public var body: some View {
        VStack(spacing: 0) {
            // Top Liquid Glass Sub-Navigation Bar
            HStack {
                Text(appState.currentLanguage == "Polski" ? "Ustawienia i Preferencje" : "Settings & Preferences")
                    .font(.system(size: 20, weight: .bold))

                Spacer()

                LiquidGlassCapsule {
                    HStack(spacing: 4) {
                        ForEach(SettingsSubTab.allCases) { tab in
                            LiquidGlassButton(
                                icon: tab.icon,
                                title: tabTitle(tab),
                                tooltip: tab.rawValue,
                                isActive: appState.settingsSubTab == tab,
                                accentColor: appState.accentColor
                            ) {
                                withAnimation(.spring(response: 0.3, dampingFraction: 0.8)) {
                                    appState.settingsSubTab = tab
                                }
                            }
                        }
                    }
                }
                .fixedSize(horizontal: true, vertical: false)
            }
            .padding(.horizontal, 24)
            .padding(.top, 18)
            .padding(.bottom, 14)

            Divider()

            // Active Tab Content
            ScrollView {
                VStack(alignment: .leading, spacing: 18) {
                    switch appState.settingsSubTab {
                    case .general:
                        generalAndThemeSection
                    case .manual:
                        userManualSection
                    case .changelog:
                        changelogSection
                    case .diagnostics:
                        diagnosticsSection
                    case .about:
                        HStack {
                            Spacer()
                            AboutAppView(appState: appState)
                            Spacer()
                        }
                        .padding(.top, 10)
                    }
                }
                .padding(24)
            }
        }
    }

    private func tabTitle(_ tab: SettingsSubTab) -> String {
        switch tab {
        case .general: return appState.currentLanguage == "Polski" ? "Wygląd i System" : "General"
        case .manual: return appState.currentLanguage == "Polski" ? "Instrukcja" : "Manual"
        case .changelog: return "Changelog"
        case .diagnostics: return "Diagnostics"
        case .about: return appState.currentLanguage == "Polski" ? "O Programie" : "About"
        }
    }

    // MARK: - 1. General & Theme Section
    private var generalAndThemeSection: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Appearance Mode Selector (Light, Dark, Auto)
            GlassCard(title: appState.currentLanguage == "Polski" ? "Tryb Wyglądu (Motyw)" : "Appearance Mode", icon: "circle.lefthalf.filled") {
                VStack(alignment: .leading, spacing: 12) {
                    Text(appState.currentLanguage == "Polski" ? "Wybierz preferowany schemat kolorystyczny okna:" : "Select your preferred application color scheme:")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)

                    HStack(spacing: 12) {
                        ThemeOptionCard(
                            title: appState.currentLanguage == "Polski" ? "Ciemny" : "Dark",
                            icon: "moon.fill",
                            isSelected: appState.appearanceMode == "Dark",
                            accentColor: appState.accentColor
                        ) {
                            appState.appearanceMode = "Dark"
                        }

                        ThemeOptionCard(
                            title: appState.currentLanguage == "Polski" ? "Jasny" : "Light",
                            icon: "sun.max.fill",
                            isSelected: appState.appearanceMode == "Light",
                            accentColor: appState.accentColor
                        ) {
                            appState.appearanceMode = "Light"
                        }

                        ThemeOptionCard(
                            title: appState.currentLanguage == "Polski" ? "Systemowy (Auto)" : "System (Auto)",
                            icon: "gearshape.circle",
                            isSelected: appState.appearanceMode == "System",
                            accentColor: appState.accentColor
                        ) {
                            appState.appearanceMode = "System"
                        }
                    }
                }
                .padding(.vertical, 4)
            }

            // Accent Color
            GlassCard(title: appState.localized("select_accent"), icon: "paintpalette.fill") {
                VStack(alignment: .leading, spacing: 10) {
                    HStack(spacing: 10) {
                        ForEach(standardSwatches, id: \.1) { name, hex in
                            Circle()
                                .fill(Color(hex: hex))
                                .frame(width: 26, height: 26)
                                .overlay(
                                    Circle()
                                        .stroke(Color.white, lineWidth: appState.accentColorHex.uppercased() == hex.uppercased() ? 2.5 : 0)
                                )
                                .shadow(color: Color(hex: hex).opacity(0.4), radius: 4, x: 0, y: 2)
                                .onTapGesture {
                                    withAnimation(.spring(response: 0.25, dampingFraction: 0.75)) {
                                        appState.accentColorHex = hex
                                    }
                                }
                                .help(name)
                        }

                        Divider()
                            .frame(height: 24)

                        // Custom color picker
                        ColorPicker("", selection: Binding(
                            get: { appState.accentColor },
                            set: { col in
                                if let hex = col.toHex() {
                                    appState.accentColorHex = hex
                                }
                            }
                        ))
                        .labelsHidden()
                        .help("Pick custom HEX color")

                        Text(appState.accentColorHex.uppercased())
                            .font(.system(size: 11, weight: .bold, design: .monospaced))
                            .foregroundColor(.secondary)
                    }
                }
                .padding(.vertical, 4)
            }

            // Interface Language
            GlassCard(title: appState.localized("lang_section"), icon: "globe") {
                HStack {
                    Text(appState.localized("interface_lang"))
                        .font(.system(size: 12))
                    Spacer()
                    Picker("", selection: $appState.currentLanguage) {
                        Text("English").tag("English")
                        Text("Polski").tag("Polski")
                        Text("Deutsch").tag("Deutsch")
                        Text("Español").tag("Español")
                        Text("Français").tag("Français")
                        Text("日本語").tag("日本語")
                    }
                    .frame(width: 140)
                }
                .padding(.vertical, 4)
            }

            // Power & Sleep
            GlassCard(title: appState.localized("power_sleep"), icon: "bolt.badge.clock") {
                VStack(alignment: .leading, spacing: 6) {
                    Toggle(appState.localized("sleep_toggle"), isOn: $appState.settings.preventSleep)
                        .toggleStyle(.switch)
                        .tint(appState.accentColor)

                    Text(appState.localized("sleep_desc"))
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
                .padding(.vertical, 4)
            }
        }
    }

    // MARK: - 2. User Manual Section
    private var userManualSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            // Search Bar
            HStack {
                Image(systemName: "magnifyingglass")
                    .foregroundColor(.secondary)
                TextField(appState.currentLanguage == "Polski" ? "Szukaj w podręczniku..." : "Search user manual...", text: $manualSearch)
                    .textFieldStyle(.plain)
                if !manualSearch.isEmpty {
                    Button(action: { manualSearch = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(10)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(Color(nsColor: .controlBackgroundColor).opacity(0.7))
            )

            // 10 Chapters
            ForEach(filteredManualChapters, id: \.id) { ch in
                DisclosureGroup(
                    content: {
                        Text(ch.content)
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                            .lineSpacing(4)
                            .padding(.top, 8)
                            .frame(maxWidth: .infinity, alignment: .leading)
                    },
                    label: {
                        HStack(spacing: 10) {
                            Image(systemName: ch.icon)
                                .foregroundColor(appState.accentColor)
                                .frame(width: 22)
                            Text(ch.title)
                                .font(.system(size: 13, weight: .semibold))
                                .foregroundColor(.primary)
                        }
                    }
                )
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color(nsColor: .controlBackgroundColor).opacity(0.4))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                )
            }
        }
    }

    private var filteredManualChapters: [ManualChapter] {
        let all = manualChapters(lang: appState.currentLanguage)
        if manualSearch.isEmpty { return all }
        let q = manualSearch.lowercased()
        return all.filter { $0.title.lowercased().contains(q) || $0.content.lowercased().contains(q) }
    }

    // MARK: - 3. Changelog Section
    private var changelogSection: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(appState.currentLanguage == "Polski" ? "Kronika Rozwoju Projektu" : "Project Release Chronicle")
                .font(.system(size: 16, weight: .bold))

            ForEach(changelogEntries, id: \.version) { item in
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Text(item.version)
                            .font(.system(size: 13, weight: .bold, design: .monospaced))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(
                                Capsule().fill(appState.accentColor.opacity(0.2))
                            )
                            .foregroundColor(appState.accentColor)

                        Text(item.date)
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)

                        Spacer()
                    }

                    Text(item.title)
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(.primary)

                    VStack(alignment: .leading, spacing: 4) {
                        ForEach(item.points, id: \.self) { pt in
                            HStack(alignment: .top, spacing: 6) {
                                Text("•")
                                    .foregroundColor(appState.accentColor)
                                Text(pt)
                                    .font(.system(size: 11))
                                    .foregroundColor(.secondary)
                            }
                        }
                    }
                }
                .padding(14)
                .background(
                    RoundedRectangle(cornerRadius: 10, style: .continuous)
                        .fill(Color(nsColor: .controlBackgroundColor).opacity(0.4))
                        .overlay(
                            RoundedRectangle(cornerRadius: 10, style: .continuous)
                                .stroke(Color.white.opacity(0.08), lineWidth: 1)
                        )
                )
            }
        }
    }

    // MARK: - 4. Diagnostics & Logs Section
    private var diagnosticsSection: some View {
        VStack(alignment: .leading, spacing: 16) {
            // System Hardware & Engine Cards
            LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 10) {
                MetricCard(title: "Hardware Accel", val: "VideoToolbox", status: "Active", icon: "bolt.fill", color: .green)
                MetricCard(title: "Backend Bridge", val: "Python CLI", status: "Standby", icon: "cpu", color: .blue)
                MetricCard(title: "Power Inhibit", val: appState.settings.preventSleep ? "IOKit Assert" : "Standard", status: appState.settings.preventSleep ? "Preventing Sleep" : "Off", icon: "power", color: appState.settings.preventSleep ? .orange : .secondary)
                MetricCard(title: "Active Logs", val: "\(appState.logLines.count) Lines", status: "Real-time", icon: "terminal.fill", color: appState.accentColor)
            }

            // Toolbar: Filter + Actions
            HStack {
                Text("System Log Stream")
                    .font(.system(size: 13, weight: .bold))

                Spacer()

                Picker("", selection: $logFilter) {
                    Text("All Logs").tag("ALL")
                    Text("Info").tag("INFO")
                    Text("Warnings").tag("WARNING")
                    Text("Errors").tag("ERROR")
                }
                .frame(width: 110)

                Button("Copy All") {
                    let text = appState.logLines.joined(separator: "\n")
                    NSPasteboard.general.clearContents()
                    NSPasteboard.general.setString(text, forType: .string)
                    appState.showToast("Logs copied to clipboard!", icon: "doc.on.doc")
                }
                .controlSize(.small)

                Button("Clear") {
                    appState.logLines.removeAll()
                }
                .controlSize(.small)
            }

            // Monospace Log Console
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 2) {
                        if filteredLogs.isEmpty {
                            Text("No log messages matching filter")
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundColor(.secondary)
                                .padding(12)
                        } else {
                            ForEach(filteredLogs.indices, id: \.self) { idx in
                                let line = filteredLogs[idx]
                                Text(line)
                                    .font(.system(size: 11, design: .monospaced))
                                    .foregroundColor(logColor(line))
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .id(idx)
                            }
                        }
                    }
                    .padding(12)
                }
                .frame(minHeight: 280, maxHeight: 380)
                .background(Color.black.opacity(0.85))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color.white.opacity(0.1), lineWidth: 1)
                )
            }
        }
    }

    private var filteredLogs: [String] {
        if logFilter == "ALL" { return appState.logLines }
        return appState.logLines.filter { $0.contains(logFilter) }
    }

    private func logColor(_ line: String) -> Color {
        if line.contains("ERROR") { return .red }
        if line.contains("WARNING") { return .orange }
        if line.contains("Verified") || line.contains("Successfully") { return .green }
        return .green.opacity(0.85)
    }
}

// MARK: - Supporting Sub-Views & Data Models

private struct ThemeOptionCard: View {
    let title: String
    let icon: String
    let isSelected: Bool
    let accentColor: Color
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 20, weight: .semibold))
                    .foregroundColor(isSelected ? accentColor : .secondary)

                Text(title)
                    .font(.system(size: 11, weight: isSelected ? .bold : .medium))
                    .foregroundColor(isSelected ? .primary : .secondary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 14)
            .background(
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(Color(nsColor: .controlBackgroundColor).opacity(0.6))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8, style: .continuous)
                            .stroke(isSelected ? accentColor : Color.white.opacity(0.08), lineWidth: isSelected ? 2 : 1)
                    )
            )
        }
        .buttonStyle(.plain)
    }
}

private struct MetricCard: View {
    let title: String
    let val: String
    let status: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            HStack {
                Image(systemName: icon)
                    .foregroundColor(color)
                    .font(.system(size: 13))
                Spacer()
                Text(status)
                    .font(.system(size: 9, weight: .bold))
                    .foregroundColor(color)
            }

            Text(val)
                .font(.system(size: 13, weight: .bold))
                .foregroundColor(.primary)
                .lineLimit(1)

            Text(title)
                .font(.system(size: 10))
                .foregroundColor(.secondary)
        }
        .padding(10)
        .background(
            RoundedRectangle(cornerRadius: 8, style: .continuous)
                .fill(Color(nsColor: .controlBackgroundColor).opacity(0.5))
                .overlay(
                    RoundedRectangle(cornerRadius: 8, style: .continuous)
                        .stroke(Color.white.opacity(0.08), lineWidth: 1)
                )
        )
    }
}

private struct ManualChapter: Identifiable {
    let id: Int
    let icon: String
    let title: String
    let content: String
}

private struct ChangelogItem {
    let version: String
    let date: String
    let title: String
    let points: [String]
}

private func manualChapters(lang: String) -> [ManualChapter] {
    if lang == "Polski" {
        return [
            ManualChapter(id: 1, icon: "person.crop.rectangle.stack", title: "1. Wprowadzenie i Wybór Trybu (Live Action vs 2D Anime)", content: "Focus oferuje dwa niezależne silniki detekcji twarzy:\n• Live Action / Real Faces: Wykorzystuje głębokie modele neuronowe (68 punktów charakterystycznych dlib), rozpoznając aktorów i ludzi pod trudnymi kątami oraz w dynamicznym oświetleniu.\n• 2D Animation / Anime: Dedykowany klasyfikator kaskadowy LBP wytrenowany pod kątem rysunku ręcznego, oczu i konturów postaci anime."),
            ManualChapter(id: 2, icon: "wand.and.stars", title: "2. Wskazanie Celu i Skanowanie Materiału", content: "Możesz wybrać pojedynczy odcinek lub CAŁY folder sezonu jednym kliknięciem (Browse...). Następnie wskaż wyraźne zdjęcie referencyjne twarzy postaci lub wybierz profil z Galerii Postaci. Kliknij 'Scan and Analyze Video', aby uruchomić automatyczne wykrywanie."),
            ManualChapter(id: 3, icon: "folder.badge.gearshape", title: "3. Przetwarzanie Wielu Odcinków (Batch & Seasons)", content: "Aplikacja automatycznie rozpoznaje konwencje nazewnictwa S01E01, S01E02, sortując pliki w idealnej kolejności fabularnej. Możesz połączyć wszystkie sceny w jeden zbiorczy Master Scenepack."),
            ManualChapter(id: 4, icon: "speaker.wave.3", title: "4. Ścieżki Dźwiękowe i Zachowanie Wielu Audio", content: "Wybierz konkretny strumień audio (np. oryginalny japoński dubbing) LUB wybierz opcję 'Keep All Audio Tracks (Multi-Audio)'. Opcja multi-audio zachowuje wszystkie ścieżki w wyeksportowanym pliku, pozwalając na przełączanie lektora bezpośrednio w programie montażowym (Premiere Pro / After Effects)."),
            ManualChapter(id: 5, icon: "slider.horizontal.3", title: "5. Parametry Strojenia (Margins, Frame Skip, Gap Bridge)", content: "• Pad Before / Pad After: Margines bezpieczeństwa przed i po ujęciu postaci.\n• Gap Bridge: Łączy ujęcia, gdy postać mrugnie lub odwróci wzrok na 1-2 sekundy.\n• Min Scene: Odrzuca przypadkowe mikroujęcia krótsze niż zadany próg.\n• Frame Skip: Przyspiesza analizę klatek wideo."),
            ManualChapter(id: 6, icon: "waveform.badge.mic", title: "6. Ochrona Dialogów (VAD) i Weryfikacja Głosu (MFCC)", content: "Inteligentne VAD (Voice Activity Detection) przyciąga punkty cięcia do naturalnych przerw w mowie, eliminując ucinanie wypowiedzi w pół słowa. Weryfikacja głosu dopasowuje tembr postaci, odrzucając sceny, w których mówi wyłącznie narrator z tła."),
            ManualChapter(id: 7, icon: "forward.frame", title: "7. Pomijanie Czołówek (Intro i Outro)", content: "Bada metadane rozdziałów MKV/MP4 (Opening, Ending, OP, ED) i automatycznie pomija je podczas skanowania, przyspieszając pracę o 15% i eliminując czołówki z gotowego scenepacka."),
            ManualChapter(id: 8, icon: "aspectratio", title: "8. Format Płótna i Kadrowanie (16:9 / 9:16)", content: "• 16:9 Original: Oryginalny format kinowy.\n• 9:16 Vertical (Character Tracking): Śledzi twarz postaci w pionowym kadrze do rolek i TikToków.\n• 9:16 Vertical (Blurred Background): Wideo z estetycznym rozmytym tłem."),
            ManualChapter(id: 9, icon: "bolt.fill", title: "9. Jakość Eksportu i Akceleracja Apple Silicon", content: "Domyślnie silnik wykorzystuje sprzętowe kodowanie Apple VideoToolbox (h264_videotoolbox). Tryb Auto dobiera optymalny bitrate z zapasem +15%, a tryb Maximum zapewnia krystaliczną jakość studyjną."),
            ManualChapter(id: 10, icon: "power", title: "10. Blokada Uśpienia i Automatyzacja", content: "Funkcja Inhibit Sleep blokuje usypianie systemu macOS (poprzez asercję IOKit), zapewniając nieprzerwane działanie podczas długich nocnych eksportów. Funkcja Auto-Render pozwala na natychmiastowe generowanie scenepacka bez oczekiwania na akceptację klipów.")
        ]
    } else {
        return [
            ManualChapter(id: 1, icon: "person.crop.rectangle.stack", title: "1. Introduction & Detection Modes (Real Faces vs Anime)", content: "Focus features two dedicated face tracking engines:\n• Live Action / Real Faces: Deep neural models (dlib 68-point landmarks) tracking actors across dynamic lighting and angles.\n• 2D Animation / Anime: Specialized Haar/LBP cascade classifier tuned for 2D animated eyes and contours."),
            ManualChapter(id: 2, icon: "wand.and.stars", title: "2. Target Selection & Video Scanning", content: "Select a single video or an entire season folder with one click (Browse...). Choose a reference face image or select an existing profile from the Gallery. Click 'Scan and Analyze Video' to start."),
            ManualChapter(id: 3, icon: "folder.badge.gearshape", title: "3. Multi-Episode Batch & Season Processing", content: "Automatically identifies S01E01 episode patterns and orders scenes chronologically. Consolidates all character appearances into a single Master Scenepack."),
            ManualChapter(id: 4, icon: "speaker.wave.3", title: "4. Audio Tracks & Multi-Audio Preservation", content: "Select a single audio stream or choose 'Keep All Audio Tracks (Multi-Audio)'. Multi-audio maintains all original audio streams in the exported file for flexible editing in Premiere Pro / After Effects."),
            ManualChapter(id: 5, icon: "slider.horizontal.3", title: "5. Detection Tuning (Margins, Frame Skip, Gap Bridge)", content: "• Pad Before / Pad After: Safety margin padding before and after character appearance.\n• Gap Bridge: Bridges gaps when the character blinks or looks away.\n• Min Scene: Filters out micro-shots shorter than the threshold.\n• Frame Skip: Speeds up analysis."),
            ManualChapter(id: 6, icon: "waveform.badge.mic", title: "6. Dialogue Protection (VAD) & Speaker Verification", content: "Voice Activity Detection snaps cut points to natural silence gaps so dialogue is never cut in half. MFCC voice verification matches vocal timbre to reject narrator-only audio."),
            ManualChapter(id: 7, icon: "forward.frame", title: "7. Intro & Outro Skipping (Opening & Ending)", content: "Reads MKV/MP4 chapter markers (Opening, Ending, OP, ED) to skip intros during scanning, saving 15% scan time."),
            ManualChapter(id: 8, icon: "aspectratio", title: "8. Canvas Framing (16:9 / 9:16 Vertical)", content: "• 16:9 Original: Cinema widescreen format.\n• 9:16 Vertical (Character Tracking): Smoothly centers character face in portrait mode for TikTok/Shorts/Reels.\n• 9:16 Vertical (Blurred Background): Padded portrait layout with blurred background."),
            ManualChapter(id: 9, icon: "bolt.fill", title: "9. Export Quality & Hardware Acceleration", content: "Powered by Apple VideoToolbox hardware encoding. Auto mode matches source bitrate with +15% quality headroom; Maximum mode delivers master-grade CRF 14 exports."),
            ManualChapter(id: 10, icon: "power", title: "10. System Sleep Inhibition & Auto-Render", content: "Native IOKit power assertion prevents macOS from sleeping during long processing sessions. Auto-Render immediately exports clips after analysis.")
        ]
    }
}

private let changelogEntries: [ChangelogItem] = [
    ChangelogItem(
        version: "v2.0.0",
        date: "2026-09-06",
        title: "Native macOS SwiftUI 6 Engine & Dual Ecosystem",
        points: [
            "Native macOS app written in pure SwiftUI 6 with instant sub-100ms startup and ~50MB RAM footprint.",
            "Apple VideoToolbox hardware acceleration and AVKit native video player.",
            "Consolidated Settings Hub with Light/Dark/System theme selector, full 10-chapter guide and changelog.",
            "Apple HIG Liquid Glass pill toolbars and 120Hz ProMotion spring animations.",
            "Native folder selection and single-click destination save panels."
        ]
    ),
    ChangelogItem(
        version: "v1.43",
        date: "2026-09-06",
        title: "Unified Icons, Power Inhibit & Multi-Audio",
        points: [
            "macOS obsidian glass squircle app icon matching native system dock aesthetics.",
            "Cross-platform SleepInhibitor (caffeinate on macOS, SetThreadExecutionState on Windows).",
            "Multi-audio stream preservation (Keep All Audio Tracks).",
            "Auto-render after scan and bulk review selection.",
            "Refined 2x2 detection tuning grid with exact unit badges."
        ]
    ),
    ChangelogItem(
        version: "v1.42",
        date: "2026-09-03",
        title: "Comprehensive Code Audit & Memory Hardening",
        points: [
            "Fixed random segmentation faults in mini-previews via QImage buffer copying.",
            "Decoupled VAD speaker verification from silence gaps.",
            "Removed unused dependencies (scipy, python_speech_features) in favor of pure NumPy MFCC."
        ]
    )
]
