#if canImport(Flutter)
import AVFoundation
import AVKit
import CoreMedia
import Flutter
import UIKit

@available(iOS 15.0, *)
final class MediaKitPictureInPictureController: NSObject {
  typealias EventCallback = ([String: Any]) -> Void

  private let hostView: UIView
  private let outputManager: VideoOutputManager
  private let eventCallback: EventCallback
  private let displayLayer = AVSampleBufferDisplayLayer()
  private var pipController: AVPictureInPictureController?
  private let enqueueQueue = DispatchQueue(
    label: "com.alexmercerind.media_kit_video.pip.enqueue",
    qos: .userInteractive
  )
  private var handle: Int64?
  private var isPlayingState = true
  private var startRequested = false
  private var firstFrameEnqueued = false
  private var startAttempts = 0
  private var didRestoreInterface = false

  init(
    hostView: UIView,
    outputManager: VideoOutputManager,
    videoSize: CGSize,
    eventCallback: @escaping EventCallback
  ) {
    self.hostView = hostView
    self.outputManager = outputManager
    self.eventCallback = eventCallback
    super.init()

    displayLayer.videoGravity = .resizeAspect
    displayLayer.frame = CGRect(x: 0, y: 0, width: 2, height: 2)
    displayLayer.isOpaque = false
    displayLayer.backgroundColor = UIColor.clear.cgColor
    hostView.layer.insertSublayer(displayLayer, at: 0)

    NotificationCenter.default.addObserver(
      self,
      selector: #selector(appDidBecomeActive),
      name: UIApplication.didBecomeActiveNotification,
      object: nil
    )
  }

  deinit {
    NotificationCenter.default.removeObserver(self)
    teardown()
  }

  @objc private func appDidBecomeActive() {
    guard let controller = pipController,
          controller.isPictureInPictureActive else { return }
    DispatchQueue.main.async { controller.stopPictureInPicture() }
  }

  var isActive: Bool {
    pipController?.isPictureInPictureActive ?? false
  }

  @discardableResult
  func start(handle: Int64, autoEnter: Bool, startImmediately: Bool) -> Bool {
    self.handle = handle
    let contentSource = AVPictureInPictureController.ContentSource(
      sampleBufferDisplayLayer: displayLayer,
      playbackDelegate: self
    )
    let controller = AVPictureInPictureController(contentSource: contentSource)
    controller.delegate = self
    controller.canStartPictureInPictureAutomaticallyFromInline = autoEnter
    pipController = controller

    outputManager.setOnFrameRendered(handle: handle) { [weak self] pixelBuffer in
      self?.enqueue(pixelBuffer: pixelBuffer)
    }

    startRequested = startImmediately
    firstFrameEnqueued = false
    startAttempts = 0
    return true
  }

  private func attemptStart() {
    guard let controller = pipController else { return }
    if controller.isPictureInPictureActive { return }
    if controller.isPictureInPicturePossible {
      controller.startPictureInPicture()
      return
    }
    startAttempts += 1
    if startAttempts >= 20 {
      eventCallback(["event": "failed", "reason": "pip_not_possible"])
      return
    }
    DispatchQueue.main.asyncAfter(deadline: .now() + 0.1) { [weak self] in
      self?.attemptStart()
    }
  }

  func stop() {
    if let controller = pipController, controller.isPictureInPictureActive {
      DispatchQueue.main.async { controller.stopPictureInPicture() }
    }
    teardown()
  }

  func setAutoEnter(_ enabled: Bool) {
    pipController?.canStartPictureInPictureAutomaticallyFromInline = enabled
  }

  private func teardown() {
    if let handle = handle {
      outputManager.setOnFrameRendered(handle: handle, nil)
      self.handle = nil
    }
    pipController = nil
    displayLayer.flushAndRemoveImage()
    displayLayer.removeFromSuperlayer()
  }

  private func enqueue(pixelBuffer: CVPixelBuffer) {
    enqueueQueue.async { [weak self] in
      guard let self else { return }
      guard displayLayer.isReadyForMoreMediaData else { return }
      guard let sample = makeSampleBuffer(from: pixelBuffer) else { return }
      displayLayer.enqueue(sample)
      if !firstFrameEnqueued {
        firstFrameEnqueued = true
        if startRequested {
          DispatchQueue.main.async { [weak self] in self?.attemptStart() }
        }
      }
    }
  }

  private func makeSampleBuffer(from pixelBuffer: CVPixelBuffer) -> CMSampleBuffer? {
    var formatDescription: CMVideoFormatDescription?
    guard CMVideoFormatDescriptionCreateForImageBuffer(
      allocator: kCFAllocatorDefault,
      imageBuffer: pixelBuffer,
      formatDescriptionOut: &formatDescription
    ) == noErr, let description = formatDescription else { return nil }

    var timingInfo = CMSampleTimingInfo(
      duration: .invalid,
      presentationTimeStamp: CMClockGetTime(CMClockGetHostTimeClock()),
      decodeTimeStamp: .invalid
    )
    var sampleBuffer: CMSampleBuffer?
    guard CMSampleBufferCreateReadyWithImageBuffer(
      allocator: kCFAllocatorDefault,
      imageBuffer: pixelBuffer,
      formatDescription: description,
      sampleTiming: &timingInfo,
      sampleBufferOut: &sampleBuffer
    ) == noErr, let buffer = sampleBuffer else { return nil }

    if let attachments = CMSampleBufferGetSampleAttachmentsArray(
      buffer, createIfNecessary: true
    ) as? [NSMutableDictionary], let first = attachments.first {
      first[kCMSampleAttachmentKey_DisplayImmediately as NSString] = kCFBooleanTrue
    }
    return buffer
  }
}

@available(iOS 15.0, *)
extension MediaKitPictureInPictureController: AVPictureInPictureControllerDelegate {
  func pictureInPictureControllerWillStartPictureInPicture(
    _ controller: AVPictureInPictureController
  ) { eventCallback(["event": "willStart"]) }

  func pictureInPictureControllerDidStartPictureInPicture(
    _ controller: AVPictureInPictureController
  ) { eventCallback(["event": "didStart"]) }

  func pictureInPictureController(
    _ controller: AVPictureInPictureController,
    failedToStartPictureInPictureWithError error: Error
  ) {
    eventCallback(["event": "failed", "reason": error.localizedDescription])
  }

  func pictureInPictureControllerWillStopPictureInPicture(
    _ controller: AVPictureInPictureController
  ) {
    didRestoreInterface = false
    eventCallback(["event": "willStop"])
  }

  func pictureInPictureControllerDidStopPictureInPicture(
    _ controller: AVPictureInPictureController
  ) {
    eventCallback(["event": didRestoreInterface ? "didStop" : "closed"])
    didRestoreInterface = false
  }

  func pictureInPictureController(
    _ controller: AVPictureInPictureController,
    restoreUserInterfaceForPictureInPictureStopWithCompletionHandler
      completionHandler: @escaping (Bool) -> Void
  ) {
    didRestoreInterface = true
    eventCallback(["event": "restore"])
    completionHandler(true)
  }
}

@available(iOS 15.0, *)
extension MediaKitPictureInPictureController:
  AVPictureInPictureSampleBufferPlaybackDelegate
{
  func pictureInPictureController(
    _ pipController: AVPictureInPictureController,
    setPlaying playing: Bool
  ) {
    isPlayingState = playing
    eventCallback(["event": "setPlaying", "playing": playing])
  }

  func pictureInPictureControllerTimeRangeForPlayback(
    _ pipController: AVPictureInPictureController
  ) -> CMTimeRange {
    CMTimeRange(start: .negativeInfinity, duration: .positiveInfinity)
  }

  func pictureInPictureControllerIsPlaybackPaused(
    _ pipController: AVPictureInPictureController
  ) -> Bool { !isPlayingState }

  func pictureInPictureController(
    _ pipController: AVPictureInPictureController,
    didTransitionToRenderSize newRenderSize: CMVideoDimensions
  ) {}

  func pictureInPictureController(
    _ pipController: AVPictureInPictureController,
    skipByInterval skipInterval: CMTime,
    completion completionHandler: @escaping () -> Void
  ) { completionHandler() }
}
#endif
