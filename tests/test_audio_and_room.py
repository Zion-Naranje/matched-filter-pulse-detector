"""Audio fallback tests (mocked) and the optional room-size stage."""
import numpy as np
import pytest

from src import audio_io
from src.chirp import C_AIR
from src.pipeline import RadarConfig
from src.room import (estimate_room, image_sources, measure_room, room_config, room_scene,
                      simulate_room_record)


def test_missing_portaudio_gives_clear_error(monkeypatch):
    def boom():
        raise audio_io.AudioUnavailable("no PortAudio")
    monkeypatch.setattr(audio_io, "_sd", boom)
    ok, msg = audio_io.audio_status()
    assert not ok and "PortAudio" in msg
    with pytest.raises(audio_io.AudioUnavailable):
        audio_io.record_with_playback(RadarConfig())


def test_no_devices_reported(monkeypatch):
    class FakeSD:
        @staticmethod
        def query_devices():
            return []
    monkeypatch.setattr(audio_io, "_sd", lambda: FakeSD)
    ok, msg = audio_io.audio_status()
    assert not ok and "0 output" in msg


def test_live_chain_with_fake_loopback_cancels_latency(monkeypatch):
    """Fake full-duplex device: 37 ms unknown latency + an echo from 1.2 m + noise."""
    cfg = audio_io.live_config(RadarConfig(), 0.3)
    from src.simulation import clean_signal
    from src.pipeline import process

    class FakeSD:
        @staticmethod
        def playrec(tx, samplerate, channels, dtype):
            lat = 0.037
            rec = clean_signal(cfg, [lat, lat + 2 * 1.2 / C_AIR], [1.0, 0.3])
            rec += 0.01 * np.random.default_rng(0).standard_normal(len(rec))
            return rec[:, None].astype("float32")

        @staticmethod
        def wait():
            pass
    monkeypatch.setattr(audio_io, "_sd", lambda: FakeSD)
    rx = audio_io.record_with_playback(cfg)
    res = process(rx, cfg)
    assert res.direct_ok and len(res.det_range) == 1
    assert abs(res.det_range[0] - 1.2) < 0.005          # latency has cancelled


def test_image_source_first_order_distances():
    room, c = (6.0, 4.0, 3.0), (2.0, 1.5, 1.0)
    path, amp = room_scene(room, c, 0.2, (0.8,) * 6, max_order=1)
    r = np.sort(path / 2)
    # walls at 2.0 / 4.0 (x), 1.5 / 2.5 (y), 1.0 / 2.0 (z); first-order paths are 2*d
    for d in (2.0, 4.0, 1.5, 2.5, 1.0, 2.0):
        assert np.min(np.abs(r - d)) < 0.01
    assert amp.max() == pytest.approx(1.0)               # direct sound normalised to 1


def test_image_sources_match_pyroomacoustics():
    pra = pytest.importorskip("pyroomacoustics")
    room, src, mic = (6.0, 4.0, 3.0), (2.0, 1.6, 1.0), (2.0, 1.4, 1.0)
    room_obj = pra.ShoeBox(room, fs=48000, materials=pra.Material(0.2), max_order=2)
    room_obj.add_source(src)
    room_obj.add_microphone(mic)
    room_obj.image_source_model()
    pra_d = np.sort(np.linalg.norm(room_obj.sources[0].images.T - np.array(mic)[None], axis=1))
    ours, _ = image_sources(room, src, mic, (np.sqrt(1 - 0.2),) * 6, max_order=2)
    ours = np.sort(ours)
    # same first arrivals (ours keeps only images with |n-q|+|n| <= 2; compare the nearest ones)
    assert np.allclose(ours[:12], pra_d[:12], atol=1e-6)


@pytest.mark.parametrize("room,pos", [((6.0, 4.0, 2.7), (2.2, 1.7, 1.0)),
                                      ((8.0, 5.5, 3.0), (3.1, 2.0, 1.1)),
                                      ((5.2, 4.1, 2.6), (1.7, 1.3, 0.9))])
def test_room_estimate_within_tolerance(room, pos):
    cfg = room_config()
    beta = (0.8, 0.8, 0.8, 0.8, 0.3, 0.4)
    rx = simulate_room_record(cfg, room, pos, 0.2, beta, 50, np.random.default_rng(4))
    est = measure_room(rx, cfg, 0.2)
    assert est["ok"]
    assert est["length"] == pytest.approx(max(room[:2]), abs=0.05)
    assert est["breadth"] == pytest.approx(min(room[:2]), abs=0.05)


def test_room_estimator_reports_failure_without_echoes():
    assert not estimate_room([], [])["ok"]
