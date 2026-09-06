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

public actor ProcessBridge {
    public static let shared = ProcessBridge()
    private var currentProcess: Process?

    private init() {}

    public static func resolvePythonExecutable() -> String {
        let currentDir = FileManager.default.currentDirectoryPath
        let possibleVenvs = [
            (currentDir as NSString).appendingPathComponent("venv/bin/python3"),
            (currentDir as NSString).appendingPathComponent("../venv/bin/python3"),
            "/opt/homebrew/bin/python3",
            "/usr/local/bin/python3",
            "/usr/bin/python3"
        ]
        for p in possibleVenvs {
            if FileManager.default.isExecutableFile(atPath: p) {
                return p
            }
        }
        return "python3"
    }

    public static func resolveScriptPath() -> String {
        let currentDir = FileManager.default.currentDirectoryPath
        let possibleScripts = [
            (currentDir as NSString).appendingPathComponent("scenepack_generator.py"),
            (currentDir as NSString).appendingPathComponent("../scenepack_generator.py")
        ]
        for p in possibleScripts {
            if FileManager.default.fileExists(atPath: p) {
                return p
            }
        }
        return "scenepack_generator.py"
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

    public func run(
        arguments: [String],
        onEvent: @escaping @Sendable (BridgeEvent) -> Void
    ) async throws {
        cancel()

        let python = Self.resolvePythonExecutable()
        let script = Self.resolveScriptPath()

        let proc = Process()
        proc.executableURL = URL(fileURLWithPath: python)
        proc.arguments = [script] + arguments + ["--json-stream"]

        let stdoutPipe = Pipe()
        let stderrPipe = Pipe()
        proc.standardOutput = stdoutPipe
        proc.standardError = stderrPipe

        currentProcess = proc

        let stdoutHandle = stdoutPipe.fileHandleForReading

        return try await withCheckedThrowingContinuation { continuation in
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

            proc.terminationHandler = { process in
                Task { [weak self] in
                    await self?.clearProcess()
                }

                if process.terminationStatus == 0 {
                    continuation.resume()
                } else if process.terminationReason == .uncaughtSignal {
                    continuation.resume()
                } else {
                    let errData = stderrPipe.fileHandleForReading.readDataToEndOfFile()
                    let errMsg = String(data: errData, encoding: .utf8) ?? "Process exited with status \(process.terminationStatus)"
                    continuation.resume(throwing: NSError(domain: "FocusBridge", code: Int(process.terminationStatus), userInfo: [NSLocalizedDescriptionKey: errMsg]))
                }
            }

            do {
                try proc.run()
            } catch {
                currentProcess = nil
                continuation.resume(throwing: error)
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
            }
        case "gallery_results":
            if let clustersData = json["clusters"] {
                if let rawData = try? JSONSerialization.data(withJSONObject: clustersData),
                   let profiles = try? JSONDecoder().decode([CharacterProfile].self, from: rawData) {
                    onEvent(.galleryResults(profiles))
                }
            }
        case "review_ready":
            if let clipsData = json["clips"] {
                if let rawData = try? JSONSerialization.data(withJSONObject: clipsData),
                   let clips = try? JSONDecoder().decode([ClipInterval].self, from: rawData) {
                    onEvent(.reviewReady(clips))
                }
            }
        case "render_complete":
            if let out = json["output"] as? String {
                onEvent(.renderComplete(out))
            }
        case "error":
            if let msg = json["message"] as? String {
                onEvent(.error(msg))
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
            }
        default:
            break
        }
    }
}
