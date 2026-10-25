"""One-device live mode: play the chirp from the speaker and record from the microphone."""
from dataclasses import replace

import numpy as np

from .chirp import lfm_chirp


class AudioUnavailable(RuntimeError):
    """Raised when no usable audio device / PortAudio library exists (UI falls back to simulation)."""


def _sd():
    """Import sounddevice lazily; a missing PortAudio library raises OSError on import."""
    try:
        import sounddevice as sd
        return sd
    except (ImportError, OSError) as exc:
        raise AudioUnavailable(f"sounddevice / PortAudio is not available: {exc}") from exc


def audio_status():
    """(ok, message): is there at least one input and one output device?"""
    try:
        sd = _sd()
        devs = sd.query_devices()
        n_in = sum(d["max_input_channels"] > 0 for d in devs)
        n_out = sum(d["max_output_channels"] > 0 for d in devs)
    except AudioUnavailable as exc:
        return False, str(exc)
    except Exception as exc:                                  # PortAudioError etc.
        return False, f"audio query failed: {exc}"
    if n_in == 0 or n_out == 0:
        return False, f"need a speaker and a microphone (found {n_out} output, {n_in} input devices)"
    return True, f"{n_out} output and {n_in} input devices found"


def live_config(cfg, total_s=0.5):
    """Live records must be long enough to hold the (unknown) audio latency plus the echoes."""
    return replace(cfg, record_s=total_s)


def record_with_playback(cfg, amplitude=0.5):
    """Play one chirp at t=0 and record cfg.record_s seconds, simultaneously (full duplex).

    The recording contains the direct speaker->microphone sound (after the unknown audio
    latency) followed by room echoes; process(..., use_direct=True) measures echoes relative
    to that direct peak, which cancels the latency.  Returns the mono float recording.
    """
    sd = _sd()
    tx = np.zeros(cfg.n_samples, dtype=np.float32)
    chirp = lfm_chirp(cfg.f0, cfg.bandwidth, cfg.duration, cfg.fs, amplitude)
    tx[:len(chirp)] = chirp
    try:
        rec = sd.playrec(tx[:, None], samplerate=cfg.fs, channels=1, dtype="float32")
        sd.wait()
    except Exception as exc:
        raise AudioUnavailable(f"could not play/record at {cfg.fs:.0f} Hz: {exc}") from exc
    return np.asarray(rec)[:, 0].astype(float)
