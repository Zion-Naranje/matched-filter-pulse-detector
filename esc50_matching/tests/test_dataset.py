import io
import zipfile

import numpy as np
from scipy.io import wavfile

from src.dataset import SR, Esc50, preprocess


def _wav_bytes(x, sr=44100):
    b = io.BytesIO()
    wavfile.write(b, sr, (x * 32767).astype(np.int16))
    return b.getvalue()


def test_preprocess_resamples_normalises_and_trims_silence():
    sr = 44100
    t = np.arange(sr) / sr
    x = np.concatenate([np.zeros(sr), 0.2 * np.sin(2 * np.pi * 440 * t), np.zeros(sr)])   # 3 s, sound in the middle
    y = preprocess((x * 32767).astype(np.int16), sr)
    assert abs(len(y) - SR) < 400                      # ~1 s left at 16 kHz
    assert np.max(np.abs(y)) == 1.0


def test_loads_from_zip_and_folder(tmp_path):
    meta = "filename,fold,target,category,esc10,src_file,take\n1-1-A-0.wav,1,0,dog,True,1,A\n2-1-A-0.wav,2,0,dog,True,1,A\n"
    tone = 0.5 * np.sin(2 * np.pi * 300 * np.arange(22050) / 44100)
    z = tmp_path / "ESC-50-master.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.writestr("ESC-50-master/meta/esc50.csv", meta)
        for f in ("1-1-A-0.wav", "2-1-A-0.wav"):
            zf.writestr(f"ESC-50-master/audio/{f}", _wav_bytes(tone))
    ds = Esc50(z)
    assert ds.categories() == ["dog"] and ds.clips_of("dog", folds={2}) == ["2-1-A-0.wav"]
    assert abs(len(ds.load("1-1-A-0.wav")) - 8000) < 100
    with zipfile.ZipFile(z) as zf:
        zf.extractall(tmp_path / "x")
    ds2 = Esc50(tmp_path / "x")                          # extracted folder (ESC-50-master inside)
    assert np.allclose(ds2.load("2-1-A-0.wav"), ds.load("2-1-A-0.wav"))
