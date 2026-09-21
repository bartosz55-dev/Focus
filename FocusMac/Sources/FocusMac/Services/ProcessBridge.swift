import Foundation

public enum BridgeEvent: Sendable {
    case log(String)
    case progress(value: Double, status: String)
    case episodeProgress(current: Int, total: Int, name: String, epProgress: Double, totalProgress: Double, epEta: String?, batchEta: String?)
    case galleryProgress(value: Double, status: String)
    case galleryStatus(String)
    case galleryResults([CharacterProfile])
    case reviewReady([ClipInterval])
    case renderComplete(String)
    case audioTracks([AudioTrackItem])
    case masterConcatComplete(String)
    case error(String)
}

private final class ThreadSafeLogBuffer: @unchecked Sendable {
    private let lock = NSLock()
    private var lines: [String] = []

    func append(_ line: String) {
        lock.lock()
        lines.append(line)
        if lines.count > 100 {
            lines.removeFirst()
        }
        lock.unlock()
    }

    func suffixJoined(_ count: Int, separator: String = "\n") -> String {
        lock.lock()
        defer { lock.unlock() }
        return lines.suffix(count).joined(separator: separator)
    }
}

private final class ThreadSafeResumeFlag: @unchecked Sendable {
    private let lock = NSLock()
    private var didResume = false

    func resumeOnce(_ block: () -> Void) {
        lock.lock()
        defer { lock.unlock() }
        guard !didResume else { return }
        didResume = true
        block()
    }
}

public actor ProcessBridge {
    public static let shared = ProcessBridge()
    private var currentProcess: Process?

    private init() {}

    public static func resolveScriptPath() -> String {
        var candidates: [String] = []

        // 1. Check App Bundle Resources (bundled inside Focus.app/Contents/Resources/)
        if let resPath = Bundle.main.resourcePath {
            candidates.append((resPath as NSString).appendingPathComponent("scenepack_generator.py"))
        }

        // 2. Relative to Focus.app bundle location (e.g. dist_mac/Focus.app -> project root)
        let bundleURL = Bundle.main.bundleURL
        let appDir = bundleURL.deletingLastPathComponent().path
        let projectDir = bundleURL.deletingLastPathComponent().deletingLastPathComponent().path
        candidates.append((appDir as NSString).appendingPathComponent("scenepack_generator.py"))
        candidates.append((projectDir as NSString).appendingPathComponent("scenepack_generator.py"))
        candidates.append((bundleURL.path as NSString).appendingPathComponent("Contents/Resources/scenepack_generator.py"))

        // 3. User home and standard locations
        let homeDir = ("~" as NSString).expandingTildeInPath
        candidates.append((homeDir as NSString).appendingPathComponent("Focus/scenepack_generator.py"))

        // 4. Current working directory (if executed from terminal, ignoring root "/")
        let currentDir = FileManager.default.currentDirectoryPath
        if currentDir != "/" && !currentDir.isEmpty {
            candidates.append((currentDir as NSString).appendingPathComponent("scenepack_generator.py"))
            candidates.append((currentDir as NSString).appendingPathComponent("../scenepack_generator.py"))
            candidates.append((currentDir as NSString).appendingPathComponent("Focus/scenepack_generator.py"))
        }

        for path in candidates {
            if FileManager.default.fileExists(atPath: path) {
                return (path as NSString).standardizingPath
            }
        }
        return "scenepack_generator.py"
    }

    public static func resolvePythonExecutable(forScript scriptPath: String = "") -> String {
        var candidates: [String] = []

        // 1. Embedded portable Python inside App Bundle (Standalone distribution)
        if let resPath = Bundle.main.resourcePath {
            candidates.append((resPath as NSString).appendingPathComponent("python/bin/python3"))
            candidates.append((resPath as NSString).appendingPathComponent("python/bin/python"))
            candidates.append((resPath as NSString).appendingPathComponent("Frameworks/Python.framework/Versions/Current/bin/python3"))
        }

        // 2. Application Support runtime (auto-bootstrapped user environment)
        if let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?.appendingPathComponent("Focus").path {
            candidates.append((appSupport as NSString).appendingPathComponent("runtime/bin/python3"))
            candidates.append((appSupport as NSString).appendingPathComponent("runtime/bin/python"))
            candidates.append((appSupport as NSString).appendingPathComponent("venv/bin/python3"))
            candidates.append((appSupport as NSString).appendingPathComponent("venv/bin/python"))
        }

        // 3. Check venv adjacent to resolved script
        if !scriptPath.isEmpty && scriptPath != "scenepack_generator.py" {
            let scriptDir = (scriptPath as NSString).deletingLastPathComponent
            if !scriptDir.isEmpty && scriptDir != "/" {
                candidates.append((scriptDir as NSString).appendingPathComponent("venv/bin/python3"))
                candidates.append((scriptDir as NSString).appendingPathComponent("venv/bin/python"))
            }
        }

        // 4. Relative to Focus.app bundle location
        let bundleURL = Bundle.main.bundleURL
        let projectDir = bundleURL.deletingLastPathComponent().deletingLastPathComponent().path
        candidates.append((projectDir as NSString).appendingPathComponent("venv/bin/python3"))
        candidates.append((projectDir as NSString).appendingPathComponent("venv/bin/python"))

        // 5. Standard user environment paths
        let home = ("~" as NSString).expandingTildeInPath
        candidates.append((home as NSString).appendingPathComponent("Focus/venv/bin/python3"))
        candidates.append((home as NSString).appendingPathComponent(".focus/venv/bin/python3"))
        candidates.append((home as NSString).appendingPathComponent("venv/bin/python3"))

        // 6. Current working directory venv (if not root "/")
        let currentDir = FileManager.default.currentDirectoryPath
        if currentDir != "/" && !currentDir.isEmpty {
            candidates.append((currentDir as NSString).appendingPathComponent("venv/bin/python3"))
            candidates.append((currentDir as NSString).appendingPathComponent("venv/bin/python"))
            candidates.append((currentDir as NSString).appendingPathComponent("../venv/bin/python3"))
        }

        // 7. System Python
        candidates.append("/opt/homebrew/bin/python3")
        candidates.append("/usr/local/bin/python3")
        candidates.append("/usr/bin/python3")

        for p in candidates {
            if FileManager.default.isExecutableFile(atPath: p) {
                return (p as NSString).standardizingPath
            }
        }
        return "python3"
    }

    public static func resolveFFmpegExecutable() -> String? {
        var candidates: [String] = []

        // 1. Embedded inside App Bundle
        if let resPath = Bundle.main.resourcePath {
            candidates.append((resPath as NSString).appendingPathComponent("bin/ffmpeg"))
        }

        // 2. Application Support
        if let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?.appendingPathComponent("Focus").path {
            candidates.append((appSupport as NSString).appendingPathComponent("bin/ffmpeg"))
        }

        // 3. System paths
        candidates.append("/opt/homebrew/bin/ffmpeg")
        candidates.append("/usr/local/bin/ffmpeg")
        candidates.append("/usr/bin/ffmpeg")

        for p in candidates {
            if FileManager.default.isExecutableFile(atPath: p) {
                return p
            }
        }
        return nil
    }

    public static func resolveFFprobeExecutable() -> String? {
        var candidates: [String] = []

        // 1. Embedded inside App Bundle
        if let resPath = Bundle.main.resourcePath {
            candidates.append((resPath as NSString).appendingPathComponent("bin/ffprobe"))
        }

        // 2. Application Support
        if let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?.appendingPathComponent("Focus").path {
            candidates.append((appSupport as NSString).appendingPathComponent("bin/ffprobe"))
        }

        // 3. System paths
        candidates.append("/opt/homebrew/bin/ffprobe")
        candidates.append("/usr/local/bin/ffprobe")
        candidates.append("/usr/bin/ffprobe")

        for p in candidates {
            if FileManager.default.isExecutableFile(atPath: p) {
                return p
            }
        }
        return nil
    }

    public static func resolveEngineExecutable() -> String? {
        var candidates: [String] = []

        // 1. Embedded inside App Bundle (Standalone distribution)
        if let resPath = Bundle.main.resourcePath {
            candidates.append((resPath as NSString).appendingPathComponent("engine/focus-engine"))
            candidates.append((resPath as NSString).appendingPathComponent("bin/focus-engine"))
            candidates.append((resPath as NSString).appendingPathComponent("focus-engine/focus-engine"))
        }

        // 2. Application Support runtime
        if let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?.appendingPathComponent("Focus").path {
            candidates.append((appSupport as NSString).appendingPathComponent("engine/focus-engine"))
            candidates.append((appSupport as NSString).appendingPathComponent("bin/focus-engine"))
        }

        // 3. Current working directory / dist
        let currentDir = FileManager.default.currentDirectoryPath
        if currentDir != "/" && !currentDir.isEmpty {
            candidates.append((currentDir as NSString).appendingPathComponent("dist_engine/focus-engine/focus-engine"))
        }

        for p in candidates {
            if FileManager.default.isExecutableFile(atPath: p) {
                return (p as NSString).standardizingPath
            }
        }
        return nil
    }

    public struct EngineDiagnostics: Sendable {
        public let engineType: String
        public let pythonPath: String
        public let ffmpegPath: String?
        public let ffprobePath: String?
        public let isReady: Bool
        public let statusDescription: String

        public init(
            engineType: String = "Python Runtime",
            pythonPath: String,
            ffmpegPath: String?,
            ffprobePath: String?,
            isReady: Bool,
            statusDescription: String
        ) {
            self.engineType = engineType
            self.pythonPath = pythonPath
            self.ffmpegPath = ffmpegPath
            self.ffprobePath = ffprobePath
            self.isReady = isReady
            self.statusDescription = statusDescription
        }
    }

    public static func checkEngineDiagnostics() -> EngineDiagnostics {
        let engine = resolveEngineExecutable()
        let script = resolveScriptPath()
        let python = resolvePythonExecutable(forScript: script)
        let ffmpeg = resolveFFmpegExecutable()
        let ffprobe = resolveFFprobeExecutable()

        let hasEngine = (engine != nil)
        let hasPython = FileManager.default.isExecutableFile(atPath: python)
        let hasFFmpeg = (ffmpeg != nil)
        let isReady = (hasEngine || hasPython) && hasFFmpeg

        let engineType = hasEngine ? "Standalone (Zero-Config)" : "Python Environment"
        let activeRuntimePath = engine ?? python

        let desc: String
        if isReady {
            if hasEngine {
                desc = "Standalone Engine Ready (Embedded, FFmpeg: \(ffmpeg != nil ? "Ready" : "Missing"))"
            } else {
                desc = "Engine Ready (Python: \((python as NSString).lastPathComponent), FFmpeg: \(ffmpeg != nil ? "Ready" : "Missing"))"
            }
        } else if !hasEngine && !hasPython {
            desc = "AI Engine runtime not found"
        } else {
            desc = "FFmpeg binary missing"
        }

        return EngineDiagnostics(
            engineType: engineType,
            pythonPath: activeRuntimePath,
            ffmpegPath: ffmpeg,
            ffprobePath: ffprobe,
            isReady: isReady,
            statusDescription: desc
        )
    }

    public func cancel() {
        if let proc = currentProcess, proc.isRunning {
            proc.terminate()
        }
        currentProcess = nil
    }

    private func clearProcess() {
        currentProcess = nil
    }

    public static func makeProcessEnvironment() -> [String: String] {
        var env = ProcessInfo.processInfo.environment
        var customBins: [String] = []

        // 1. Bundle resources bin
        if let resPath = Bundle.main.resourcePath {
            customBins.append((resPath as NSString).appendingPathComponent("bin"))
            customBins.append((resPath as NSString).appendingPathComponent("python/bin"))
        }

        // 2. Application Support Focus bin
        if let appSupport = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first?.appendingPathComponent("Focus").path {
            customBins.append((appSupport as NSString).appendingPathComponent("bin"))
            customBins.append((appSupport as NSString).appendingPathComponent("runtime/bin"))
        }

        // 3. Standard system paths
        customBins.append(contentsOf: ["/opt/homebrew/bin", "/usr/local/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"])

        let extraPaths = customBins.joined(separator: ":")
        if let existing = env["PATH"] {
            env["PATH"] = extraPaths + ":" + existing
        } else {
            env["PATH"] = extraPaths
        }
        env["PYTHONUNBUFFERED"] = "1"
        return env
    }

    public func queryAudioTracks(for videoPath: String) async -> [AudioTrackItem] {
        // Method 1: Direct fast probe via local ffprobe if available
        if let ffprobe = Self.resolveFFprobeExecutable() {
            let proc = Process()
            proc.executableURL = URL(fileURLWithPath: ffprobe)
            proc.arguments = [
                "-v", "error",
                "-show_entries", "stream=index,codec_name:stream_tags=language,title",
                "-select_streams", "a",
                "-of", "json",
                videoPath
            ]
            let pipe = Pipe()
            proc.standardOutput = pipe
            proc.standardError = Pipe()
            do {
                try proc.run()
                let data = pipe.fileHandleForReading.readDataToEndOfFile()
                proc.waitUntilExit()

                if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let streams = json["streams"] as? [[String: Any]] {
                    var items: [AudioTrackItem] = []
                    for s in streams {
                        guard let idx = s["index"] as? Int else { continue }
                        let tags = s["tags"] as? [String: Any]
                        let lang = tags?["language"] as? String
                        let title = tags?["title"] as? String
                        let codec = s["codec_name"] as? String ?? "audio"

                        var labelParts: [String] = ["Track \(idx + 1)"]
                        if let lang = lang, !lang.isEmpty { labelParts.append("[\(lang.uppercased())]") }
                        if let title = title, !title.isEmpty { labelParts.append("(\(title))") }
                        labelParts.append("(\(codec))")
                        items.append(AudioTrackItem(index: idx, label: labelParts.joined(separator: " ")))
                    }
                    if !items.isEmpty {
                        return items
                    }
                }
            } catch {
                print("ffprobe direct probe error: \(error)")
            }
        }

        // Method 2: Standalone Engine or Python backend bridge
        let proc = Process()
        if let engine = Self.resolveEngineExecutable() {
            proc.executableURL = URL(fileURLWithPath: engine)
            proc.arguments = ["-v", videoPath, "--get-audio-tracks"]
        } else {
            let script = Self.resolveScriptPath()
            let python = Self.resolvePythonExecutable(forScript: script)
            let scriptURL = URL(fileURLWithPath: script)
            let scriptDirURL = scriptURL.deletingLastPathComponent()

            proc.executableURL = URL(fileURLWithPath: python)
            if FileManager.default.fileExists(atPath: scriptDirURL.path) {
                proc.currentDirectoryURL = scriptDirURL
            }
            proc.arguments = [script, "-v", videoPath, "--get-audio-tracks"]
        }
        proc.environment = Self.makeProcessEnvironment()

        let stdoutPipe = Pipe()
        proc.standardOutput = stdoutPipe
        proc.standardError = Pipe()

        do {
            try proc.run()
            let data = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
            proc.waitUntilExit()

            if let str = String(data: data, encoding: .utf8) {
                for line in str.components(separatedBy: .newlines) {
                    let trimmed = line.trimmingCharacters(in: .whitespacesAndNewlines)
                    guard let lineData = trimmed.data(using: .utf8),
                          let json = try? JSONSerialization.jsonObject(with: lineData) as? [String: Any],
                          let type = json["type"] as? String, type == "audio_tracks",
                          let tracksData = json["tracks"] as? [[String: Any]] else { continue }

                    let items = tracksData.compactMap { dict -> AudioTrackItem? in
                        guard let idx = dict["index"] as? Int,
                              let lbl = dict["label"] as? String else { return nil }
                        return AudioTrackItem(index: idx, label: lbl)
                    }
                    if !items.isEmpty {
                        return items
                    }
                }
            }
        } catch {
            print("Audio track probe error: \(error)")
        }

        return []
    }

    public func run(
        arguments: [String],
        onEvent: @escaping @Sendable (BridgeEvent) -> Void
    ) async throws {
        cancel()

        let proc = Process()
        if let engine = Self.resolveEngineExecutable() {
            proc.executableURL = URL(fileURLWithPath: engine)
            proc.arguments = arguments + ["--json-stream"]
        } else {
            let script = Self.resolveScriptPath()
            let python = Self.resolvePythonExecutable(forScript: script)
            let scriptURL = URL(fileURLWithPath: script)
            let scriptDirURL = scriptURL.deletingLastPathComponent()

            proc.executableURL = URL(fileURLWithPath: python)
            if FileManager.default.fileExists(atPath: scriptDirURL.path) {
                proc.currentDirectoryURL = scriptDirURL
            }
            proc.arguments = [script] + arguments + ["--json-stream"]
        }
        proc.environment = Self.makeProcessEnvironment()

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        proc.standardOutput = stdoutPipe
        proc.standardError = stderrPipe

        currentProcess = proc

        let stdoutHandle = stdoutPipe.fileHandleForReading
        let stderrHandle = stderrPipe.fileHandleForReading

        let errBufferStore = ThreadSafeLogBuffer()
        let resumeController = ThreadSafeResumeFlag()

        return try await withCheckedThrowingContinuation { continuation in
            // 1. Concurrent stdout line reader (JSON protocol + stdout logs)
            DispatchQueue.global(qos: .userInitiated).async {
                var buffer = Data()
                while true {
                    let chunk = stdoutHandle.availableData
                    if chunk.isEmpty { break }
                    buffer.append(chunk)

                    while let range = buffer.range(of: Data([0x0A])) { // newline \n
                        let lineData = buffer.subdata(in: buffer.startIndex..<range.lowerBound)
                        buffer.removeSubrange(buffer.startIndex...range.lowerBound)

                        if let line = String(data: lineData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
                           !line.isEmpty {
                            Self.parseLine(line, onEvent: onEvent)
                        }
                    }
                }
            }

            // 2. Concurrent stderr line reader (Python INFO, WARNING, ERROR logs)
            DispatchQueue.global(qos: .userInitiated).async {
                var errBuffer = Data()
                while true {
                    let chunk = stderrHandle.availableData
                    if chunk.isEmpty { break }
                    errBuffer.append(chunk)

                    while let range = errBuffer.range(of: Data([0x0A])) {
                        let lineData = errBuffer.subdata(in: errBuffer.startIndex..<range.lowerBound)
                        errBuffer.removeSubrange(errBuffer.startIndex...range.lowerBound)

                        if let line = String(data: lineData, encoding: .utf8)?.trimmingCharacters(in: .whitespacesAndNewlines),
                           !line.isEmpty {
                            onEvent(.log(line))
                            errBufferStore.append(line)
                        }
                    }
                }
            }

            proc.terminationHandler = { process in
                Task { [weak self] in
                    await self?.clearProcess()
                }

                if process.terminationStatus == 0 || process.terminationReason == .uncaughtSignal {
                    resumeController.resumeOnce {
                        continuation.resume()
                    }
                } else {
                    let collectedErr = errBufferStore.suffixJoined(15)
                    let finalErr = collectedErr.isEmpty ? "Process exited with status \(process.terminationStatus)" : collectedErr
                    resumeController.resumeOnce {
                        continuation.resume(throwing: NSError(domain: "FocusBridge", code: Int(process.terminationStatus), userInfo: [NSLocalizedDescriptionKey: finalErr]))
                    }
                }
            }

            do {
                try proc.run()
            } catch {
                currentProcess = nil
                resumeController.resumeOnce {
                    continuation.resume(throwing: error)
                }
            }
        }
    }

    private static func parseLine(_ line: String, onEvent: @escaping (BridgeEvent) -> Void) {
        guard let data = line.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let type = json["type"] as? String else {
            onEvent(.log(line))
            return
        }

        switch type {
        case "log":
            if let msg = json["message"] as? String {
                onEvent(.log(msg))
            }
        case "progress":
            let val = (json["val"] as? Double) ?? 0.0
            let status = (json["status"] as? String) ?? ""
            onEvent(.progress(value: val, status: status))
        case "episode_progress":
            let cur = (json["cur"] as? Int) ?? 1
            let tot = (json["tot"] as? Int) ?? 1
            let name = (json["name"] as? String) ?? ""
            let epProg = (json["ep_prog"] as? Double) ?? 0.0
            let totProg = (json["tot_prog"] as? Double) ?? 0.0
            let epEta = json["ep_eta"] as? String
            let batchEta = json["batch_eta"] as? String
            onEvent(.episodeProgress(current: cur, total: tot, name: name, epProgress: epProg, totalProgress: totProg, epEta: epEta, batchEta: batchEta))
        case "gallery_progress":
            let val = (json["val"] as? Double) ?? 0.0
            let status = (json["status"] as? String) ?? ""
            onEvent(.galleryProgress(value: val, status: status))
        case "gallery_status":
            if let status = json["status"] as? String {
                onEvent(.galleryStatus(status))
                onEvent(.log("[GALLERY] \(status)"))
            }
        case "gallery_results":
            if let clustersData = json["clusters"] {
                if let rawData = try? JSONSerialization.data(withJSONObject: clustersData),
                   let profiles = try? JSONDecoder().decode([CharacterProfile].self, from: rawData) {
                    onEvent(.galleryResults(profiles))
                    onEvent(.log("[GALLERY] Discovered \(profiles.count) unique character face clusters."))
                }
            }
        case "review_ready":
            if let clipsData = json["clips"] {
                if let rawData = try? JSONSerialization.data(withJSONObject: clipsData),
                   let clips = try? JSONDecoder().decode([ClipInterval].self, from: rawData) {
                    onEvent(.reviewReady(clips))
                    onEvent(.log("[INFO] Succeeded! Detected \(clips.count) scene clips ready for review."))
                }
            }
        case "render_complete":
            if let out = json["output"] as? String {
                onEvent(.renderComplete(out))
                onEvent(.log("[SUCCESS] Master render completed: \(out)"))
            }
        case "error":
            if let msg = json["message"] as? String {
                onEvent(.error(msg))
                onEvent(.log("[ERROR] \(msg)"))
            }
        case "audio_tracks":
            if let tracksData = json["tracks"] as? [[String: Any]] {
                let items = tracksData.compactMap { dict -> AudioTrackItem? in
                    guard let idx = dict["index"] as? Int,
                          let lbl = dict["label"] as? String else { return nil }
                    return AudioTrackItem(index: idx, label: lbl)
                }
                onEvent(.audioTracks(items))
            }
        case "master_concat_complete":
            if let out = json["output"] as? String {
                onEvent(.masterConcatComplete(out))
                onEvent(.log("[SUCCESS] Master concatenation finished: \(out)"))
            }
        default:
            onEvent(.log(line))
            break
        }
    }
}
