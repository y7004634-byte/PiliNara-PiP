#if canImport(Flutter)
import AVFoundation
import AVKit
import Flutter
import UIKit

final class MediaKitPictureInPicturePlugin: NSObject, FlutterStreamHandler {
  static let methodChannel = "com.alexmercerind/media_kit_video/pip"
  static let eventChannel = "com.alexmercerind/media_kit_video/pip/events"

  private let outputManager: VideoOutputManager
  private var controllerBox: AnyObject?
  private var eventSink: FlutterEventSink?
  private var audioSessionConfigured = false

  init(registrar: FlutterPluginRegistrar, outputManager: VideoOutputManager) {
    self.outputManager = outputManager
    super.init()
    let messenger = registrar.messenger()
    let method = FlutterMethodChannel(
      name: Self.methodChannel, binaryMessenger: messenger
    )
    let events = FlutterEventChannel(
      name: Self.eventChannel, binaryMessenger: messenger
    )
    method.setMethodCallHandler { [weak self] call, result in
      self?.handle(call, result: result)
    }
    events.setStreamHandler(self)
  }

  func handle(_ call: FlutterMethodCall, result: @escaping FlutterResult) {
    switch call.method {
    case "isSupported":
      if #available(iOS 15.0, *) {
        result(AVPictureInPictureController.isPictureInPictureSupported())
      } else {
        result(false)
      }
    case "isActive":
      if #available(iOS 15.0, *),
         let controller = controllerBox as? MediaKitPictureInPictureController {
        result(controller.isActive)
      } else {
        result(false)
      }
    case "start":
      handleStart(call.arguments, result: result)
    case "stop":
      if #available(iOS 15.0, *),
         let controller = controllerBox as? MediaKitPictureInPictureController {
        controller.stop()
      }
      controllerBox = nil
      result(nil)
    case "setAutoEnter":
      guard let args = call.arguments as? [String: Any],
            let enabled = args["enabled"] as? Bool else {
        result(FlutterError(code: "INVALID_ARGS", message: nil, details: nil))
        return
      }
      if #available(iOS 15.0, *),
         let controller = controllerBox as? MediaKitPictureInPictureController {
        controller.setAutoEnter(enabled)
      }
      result(nil)
    default:
      result(FlutterMethodNotImplemented)
    }
  }

  private func handleStart(_ arguments: Any?, result: @escaping FlutterResult) {
    guard #available(iOS 15.0, *) else {
      result(FlutterError(
        code: "UNSUPPORTED",
        message: "Picture-in-Picture requires iOS 15+",
        details: nil
      ))
      return
    }
    guard let args = arguments as? [String: Any] else {
      result(FlutterError(
        code: "INVALID_ARGS", message: "arguments required", details: nil
      ))
      return
    }
    let handle: Int64?
    if let n = args["handle"] as? NSNumber {
      handle = n.int64Value
    } else if let s = args["handle"] as? String {
      handle = Int64(s)
    } else {
      handle = nil
    }
    guard let handle else {
      result(FlutterError(
        code: "INVALID_ARGS", message: "handle required", details: nil
      ))
      return
    }

    let width = (args["width"] as? NSNumber)?.doubleValue ?? 1280
    let height = (args["height"] as? NSNumber)?.doubleValue ?? 720
    let autoEnter = args["autoEnter"] as? Bool ?? true
    let startImmediately = args["startImmediately"] as? Bool ?? false

    guard let hostView = Self.resolveHostView() else {
      result(FlutterError(
        code: "NO_WINDOW", message: "No host window available", details: nil
      ))
      return
    }

    configureAudioSessionIfNeeded()
    (controllerBox as? MediaKitPictureInPictureController)?.stop()

    let pip = MediaKitPictureInPictureController(
      hostView: hostView,
      outputManager: outputManager,
      videoSize: CGSize(width: width, height: height)
    ) { [weak self] event in
      self?.eventSink?(event)
    }
    controllerBox = pip

    if pip.start(
      handle: handle,
      autoEnter: autoEnter,
      startImmediately: startImmediately
    ) {
      result(nil)
    } else {
      controllerBox = nil
      result(FlutterError(
        code: "START_FAILED",
        message: "Unable to attach Picture-in-Picture pipeline",
        details: nil
      ))
    }
  }

  private func configureAudioSessionIfNeeded() {
    guard !audioSessionConfigured else { return }
    let session = AVAudioSession.sharedInstance()
    do {
      try session.setCategory(
        .playback,
        mode: .moviePlayback,
        options: [.allowAirPlay, .allowBluetoothA2DP]
      )
      try session.setActive(true)
      audioSessionConfigured = true
    } catch {
      NSLog("PiP AVAudioSession setup failed: \(error)")
    }
  }

  private static func resolveHostView() -> UIView? {
    for scene in UIApplication.shared.connectedScenes {
      guard let windowScene = scene as? UIWindowScene,
        scene.activationState == .foregroundActive ||
        scene.activationState == .foregroundInactive
      else { continue }
      let window = windowScene.windows.first(where: { $0.isKeyWindow })
        ?? windowScene.windows.first
      if let window {
        return window.rootViewController?.view ?? window
      }
    }
    return nil
  }

  func onListen(
    withArguments arguments: Any?,
    eventSink events: @escaping FlutterEventSink
  ) -> FlutterError? {
    eventSink = events
    return nil
  }

  func onCancel(withArguments arguments: Any?) -> FlutterError? {
    eventSink = nil
    return nil
  }
}
#endif
