import Foundation

public enum BridgeEvent: Sendable {
    case log(String)
    case progress(value: Double, status: String)
    case episodeProgress(current: Int, total: Int, name: String, epProgress: Double, totalProgress: Double)
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

        // 3. Known repository directories
        candidates.append("/Volumes/DyskNvmeE6XPG/Antigravity/Kwiatson cliping software copy 2/scenepack_generator.py")
        candidates.append("/Volumes/DyskNvmeE6XPG/Antigravity/Kwiatson cliping software/scenepack_generator.py")
        candidates.append("/Users/bartosz5500/Antigravity/Kwiatson cliping software copy 2/scenepack_generator.py")

        // 4. Current working directory (if executed from terminal, ignoring root "/")
        let currentDir = FileManager.default.currentDirectoryPath
        if currentDir != "/" && !currentDir.isEmpty {
            candidates.append((currentDir as NSString).appendingPathComponent("scenepack_generator.py"))
            candidates.append((currentDir as NSString).appendingPathComponent("../scenepack_generator.py"))
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

        // 1. Check venv adjacent to resolved script
        if !scriptPath.isEmpty && scriptPath != "scenepack_generator.py" {
            let scriptDir = (scriptPath as NSString).deletingLastPathComponent
            if !scriptDir.isEmpty && scriptDir != "/" {
                candidates.append((scriptDir as NSString).appendingPathComponent("venv/bin/python3"))
                candidates.append((scriptDir as NSString).appendingPathComponent("venv/bin/python"))
            }
        }

        // 2. Relative to Focus.app bundle location
        let bundleURL = Bundle.main.bundleURL
        let projectDir = bundleURL.deletingLastPathComponent().deletingLastPathComponent().path
        candidates.append((projectDir as NSString).appendingPathComponent("venv/bin/python3"))
        candidates.append((projectDir as NSString).appendingPathComponent("venv/bin/python"))

        // 3. Known configured project venvs with cv2 and full AI dependencies
        candidates.append("/Volumes/DyskNvmeE6XPG/Antigravity/Kwiatson cliping software copy 2/venv/bin/python3")
        candidates.append("/Volumes/DyskNvmeE6XPG/Antigravity/Kwiatson cliping software copy 2/venv/bin/python")
        candidates.append("/Users/bartosz5500/Antigravity/Kwiatson cliping software copy 2/venv/bin/python3")
        candidates.append("/Volumes/DyskNvmeE6XPG/Antigravity/Kwiatson cliping software/venv/bin/python3")
        candidates.append("/Users/bartosz5500/venv/bin/python3")

        // 4. Current working directory venv (if not root "/")
        let currentDir = FileManager.default.currentDirectoryPath
        if currentDir != "/" && !currentDir.isEmpty {
            candidates.append((currentDir as NSString).appendingPathComponent("venv/bin/python3"))
            candidates.append((currentDir as NSString).appendingPathComponent("venv/bin/python"))
            candidates.append((currentDir as NSString).appendingPathComponent("../venv/bin/python3"))
        }

        // 5. System Python
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

    public static func resolveFFprobeExecutable() -> String? {
        let candidates = [
            "/opt/homebrew/bin/ffprobe",
            "/usr/local/bin/ffprobe",
            "/usr/bin/ffprobe"
        ]
        for p in candidates {
            if FileManager.default.isExecutableFile(atPath: p) {
                return p
            }
        }
        return nil
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

    public func queryAudioTracks(for videoPath: String) async -> [AudioTrackItem] {
        // Method 1: Fast direct ffprobe in ~15ms
        if let ffprobe = Self.resolveFFprobeExecutable() {
            let proc = Process()
            proc.executableURL = URL(fileURLWithPath: ffprobe)
            proc.arguments = [
                "-v", "error",
                "-select_streams", "a",
                "-show_entries", "stream=index,codec_name:stream_tags=language,title",
                "-of", "json",
                videoPath
            ]
            let stdoutPipe = Pipe()
            proc.standardOutput = stdoutPipe
            proc.standardError = Pipe()

            do {
                try proc.run()
                let data = stdoutPipe.fileHandleForReading.readDataToEndOfFile()
                proc.waitUntilExit()

                if proc.terminationStatus == 0,
                   let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                   let streams = json["streams"] as? [[String: Any]], !streams.isEmpty {
                    var items: [AudioTrackItem] = []
                    for (idx, stream) in streams.enumerated() {
                        let tags = stream["tags"] as? [String: Any] ?? [:]
                        let lang = (tags["language"] as? String) ?? "und"
                        let title = (tags["title"] as? String) ?? ""
                        let codec = (stream["codec_name"] as? String) ?? "audio"

                        var labelParts = ["Track \(idx + 1)"]
                        if lang != "und" && !lang.isEmpty {
                            labelParts.append("[\(lang.uppercased())]")
                        }
                        if !title.isEmpty {
                            labelParts.append("- \(title)")
                        }
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

        // Method 2: Fallback to Python backend bridge
        let script = Self.resolveScriptPath()
        let python = Self.resolvePythonExecutable(forScript: script)
        let scriptURL = URL(fileURLWithPath: script)
        let scriptDirURL = scriptURL.deletingLastPathComponent()

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: python)
        if FileManager.default.fileExists(atPath: scriptDirURL.path) {
            proc.currentDirectoryURL = scriptDirURL
        }
        proc.arguments = [script, "-v", videoPath, "--get-audio-tracks"]

        var env = ProcessInfo.processInfo.environment
        let extraPaths = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        if let existing = env["PATH"] {
            env["PATH"] = extraPaths + ":" + existing
        } else {
            env["PATH"] = extraPaths
        }
        env["PYTHONUNBUFFERED"] = "1"
        proc.environment = env

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
            print("ProcessBridge queryAudioTracks fallback error: \(error)")
        }

        return []
    }

    public func run(
        arguments: [String],
        onEvent: @escaping @Sendable (BridgeEvent) -> Void
    ) async throws {
        cancel()

        let script = Self.resolveScriptPath()
        let python = Self.resolvePythonExecutable(forScript: script)
        let scriptURL = URL(fileURLWithPath: script)
        let scriptDirURL = scriptURL.deletingLastPathComponent()

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: python)
        if FileManager.default.fileExists(atPath: scriptDirURL.path) {
            proc.currentDirectoryURL = scriptDirURL
        }
        proc.arguments = [script] + arguments + ["--json-stream"]

        var env = ProcessInfo.processInfo.environment
        let extraPaths = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
        if let existing = env["PATH"] {
            env["PATH"] = extraPaths + ":" + existing
        } else {
            env["PATH"] = extraPaths
        }
        env["PYTHONUNBUFFERED"] = "1"
        proc.environment = env

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
            onEvent(.episodeProgress(current: cur, total: tot, name: name, epProgress: epProg, totalProgress: totProg))
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
