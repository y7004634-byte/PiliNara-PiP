import AVFoundation
import Flutter
import Foundation

final class PiliNaraNativeBridge: NSObject, FlutterPlugin, FlutterStreamHandler {
  private var thermalEventSink: FlutterEventSink?

  static func register(with registrar: FlutterPluginRegistrar) {
    let instance = PiliNaraNativeBridge()
    let method = FlutterMethodChannel(
      name: "com.pilinara.tw/native",
      binaryMessenger: registrar.messenger()
    )
    let thermal = FlutterEventChannel(
      name: "com.pilinara.tw/thermal",
      binaryMessenger: registrar.messenger()
    )
    registrar.addMethodCallDelegate(instance, channel: method)
    thermal.setStreamHandler(instance)
    NotificationCenter.default.addObserver(
      instance,
      selector: #selector(instance.thermalStateDidChange),
      name: ProcessInfo.thermalStateDidChangeNotification,
      object: nil
    )
  }

  deinit {
    NotificationCenter.default.removeObserver(self)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "remux":
      guard
        let args = call.arguments as? [String: Any],
        let outputPath = args["outputPath"] as? String
      else {
        result(
          FlutterError(
            code: "BAD_ARGS",
            message: "outputPath is required",
            details: nil
          )
        )
        return
      }

      let videoPath = args["videoPath"] as? String
      let audioPath = args["audioPath"] as? String
      let audioOnly = (args["audioOnly"] as? Bool) ?? false

      DispatchQueue.global(qos: .userInitiated).async {
        do {
          try Self.remux(
            videoPath: videoPath,
            audioPath: audioPath,
            outputPath: outputPath,
            audioOnly: audioOnly,
            completion: { value in
              DispatchQueue.main.async {
                switch value {
                case .success(let path):
                  result(path)
                case .failure(let error):
                  result(
                    FlutterError(
                      code: "REMUX_FAILED",
                      message: error.localizedDescription,
                      details: nil
                    )
                  )
                }
              }
            }
          )
        } catch {
          DispatchQueue.main.async {
            result(
              FlutterError(
                code: "REMUX_FAILED",
                message: error.localizedDescription,
                details: nil
              )
            )
          }
        }
      }

    default:
      result(FlutterMethodNotImplemented)
    }
  }

  private enum BridgeError: LocalizedError {
    case missingVideoTrack
    case missingAudioTrack
    case cannotCreateTrack
    case cannotCreateExporter
    case exportFailed(String)

    var errorDescription: String? {
      switch self {
      case .missingVideoTrack:
        return "找不到影片轨"
      case .missingAudioTrack:
        return "找不到音讯轨"
      case .cannotCreateTrack:
        return "无法建立封装轨道"
      case .cannotCreateExporter:
        return "无法建立快速封装器"
      case .exportFailed(let reason):
        return "快速封装失败：\(reason)"
      }
    }
  }

  private static func remux(
    videoPath: String?,
    audioPath: String?,
    outputPath: String,
    audioOnly: Bool,
    completion: @escaping (Result<String, Error>) -> Void
  ) throws {
    let composition = AVMutableComposition()
    var targetDuration = CMTime.zero

    if !audioOnly {
      guard let videoPath else {
        throw BridgeError.missingVideoTrack
      }
      let videoAsset = AVURLAsset(url: URL(fileURLWithPath: videoPath))
      guard let sourceVideo = videoAsset.tracks(withMediaType: .video).first else {
        throw BridgeError.missingVideoTrack
      }
      guard
        let targetVideo = composition.addMutableTrack(
          withMediaType: .video,
          preferredTrackID: kCMPersistentTrackID_Invalid
        )
      else {
        throw BridgeError.cannotCreateTrack
      }
      let duration = videoAsset.duration
      try targetVideo.insertTimeRange(
        CMTimeRange(start: .zero, duration: duration),
        of: sourceVideo,
        at: .zero
      )
      targetVideo.preferredTransform = sourceVideo.preferredTransform
      targetDuration = duration
    }

    if let audioPath {
      let audioAsset = AVURLAsset(url: URL(fileURLWithPath: audioPath))
      guard let sourceAudio = audioAsset.tracks(withMediaType: .audio).first else {
        if audioOnly {
          throw BridgeError.missingAudioTrack
        }
        throw BridgeError.missingAudioTrack
      }
      guard
        let targetAudio = composition.addMutableTrack(
          withMediaType: .audio,
          preferredTrackID: kCMPersistentTrackID_Invalid
        )
      else {
        throw BridgeError.cannotCreateTrack
      }

      let audioDuration = audioAsset.duration
      let insertDuration: CMTime
      if audioOnly || targetDuration == .zero {
        insertDuration = audioDuration
        targetDuration = audioDuration
      } else {
        insertDuration = CMTimeMinimum(audioDuration, targetDuration)
      }
      try targetAudio.insertTimeRange(
        CMTimeRange(start: .zero, duration: insertDuration),
        of: sourceAudio,
        at: .zero
      )
    } else if audioOnly {
      throw BridgeError.missingAudioTrack
    }

    let outputURL = URL(fileURLWithPath: outputPath)
    try? FileManager.default.removeItem(at: outputURL)

    guard
      let exporter = AVAssetExportSession(
        asset: composition,
        presetName: AVAssetExportPresetPassthrough
      )
    else {
      throw BridgeError.cannotCreateExporter
    }

    exporter.outputURL = outputURL
    exporter.outputFileType = audioOnly ? .m4a : .mp4
    exporter.shouldOptimizeForNetworkUse = true
    exporter.exportAsynchronously {
      switch exporter.status {
      case .completed:
        completion(.success(outputPath))
      case .failed:
        completion(
          .failure(
            BridgeError.exportFailed(
              exporter.error?.localizedDescription ?? "unknown error"
            )
          )
        )
      case .cancelled:
        completion(.failure(BridgeError.exportFailed("cancelled")))
      default:
        completion(
          .failure(
            BridgeError.exportFailed(
              exporter.error?.localizedDescription ?? "unexpected state"
            )
          )
        )
      }
    }
  }

  func onListen(
    withArguments arguments: Any?,
    eventSink events: @escaping FlutterEventSink
  ) -> FlutterError? {
    thermalEventSink = events
    events(ProcessInfo.processInfo.thermalState.rawValue)
    return nil
  }

  func onCancel(withArguments arguments: Any?) -> FlutterError? {
    thermalEventSink = nil
    return nil
  }

  @objc private func thermalStateDidChange() {
    thermalEventSink?(ProcessInfo.processInfo.thermalState.rawValue)
  }
}
