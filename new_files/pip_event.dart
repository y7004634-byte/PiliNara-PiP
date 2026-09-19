abstract class PipEvent {
  const PipEvent();
}
class PipWillStart extends PipEvent { const PipWillStart(); }
class PipDidStart extends PipEvent { const PipDidStart(); }
class PipWillStop extends PipEvent { const PipWillStop(); }
class PipDidStop extends PipEvent { const PipDidStop(); }
class PipRestore extends PipEvent { const PipRestore(); }
class PipClosed extends PipEvent { const PipClosed(); }
class PipFailed extends PipEvent {
  const PipFailed(this.reason);
  final String reason;
}
class PipSetPlaying extends PipEvent {
  const PipSetPlaying({required this.playing});
  final bool playing;
}
