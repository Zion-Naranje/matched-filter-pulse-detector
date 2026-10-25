"""ESC-50 access: read clips from a local zip, a local folder, or (fallback) GitHub; preprocess to 16 kHz."""
import csv
import io
import os
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor
from math import gcd
from pathlib import Path

import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly

SR = 16000
CLASSES = ["dog", "rooster", "rain", "siren", "door_wood_knock"]   # names as spelled in meta/esc50.csv
RAW_URL = "https://raw.githubusercontent.com/karolpiczak/ESC-50/master/"
ROOT = Path(__file__).resolve().parents[1]


def preprocess(x, sr_in, sr_out=SR, silence_rel=1e-3):
    """int/float samples -> mono float, resampled to sr_out, peak-normalised, silent padding trimmed.

    ESC-50 pads short events with digital silence up to 5 s; we trim it so the template and the
    inserted clips contain only the sound itself.
    """
    x = np.asarray(x)
    if x.dtype.kind == "i":
        x = x / float(np.iinfo(x.dtype).max)
    x = x.astype(float)
    if x.ndim == 2:
        x = x.mean(axis=1)
    if sr_in != sr_out:
        g = gcd(int(sr_in), int(sr_out))
        x = resample_poly(x, sr_out // g, int(sr_in) // g)
    peak = np.max(np.abs(x)) if len(x) else 0.0
    if peak == 0:
        return x
    x = x / peak
    loud = np.flatnonzero(np.abs(x) > silence_rel)
    return x[loud[0]:loud[-1] + 1]


class Esc50:
    """Where the audio comes from, in order: explicit `path` (zip or folder), $ESC50_PATH,
    ./data/ (a zip or an extracted ESC-50-master folder), else download single files from GitHub
    into ./data/cache (only the clips actually used)."""

    def __init__(self, path=None, cache_dir=None):
        self.cache = Path(cache_dir or ROOT / "data" / "cache")
        self._zip = None
        self._members = {}
        self._folder = None
        self._clips = {}
        src = path or os.environ.get("ESC50_PATH") or self._find_default()
        self.source = "GitHub download (cached)"
        if src:
            src = Path(src).expanduser()
            if src.is_file() and src.suffix.lower() == ".zip":
                self._zip = zipfile.ZipFile(src)
                for n in self._zip.namelist():
                    if n.lower().endswith(".wav"):
                        self._members[Path(n).name] = n
                    elif n.endswith("meta/esc50.csv"):
                        self._members["esc50.csv"] = n
                self.source = f"zip file {src}"
            elif src.is_dir():
                folder = self._locate_folder(src)
                if folder is None:
                    raise FileNotFoundError(f"No meta/esc50.csv found under {src}")
                self._folder = folder
                self.source = f"folder {folder}"
            else:
                raise FileNotFoundError(f"ESC-50 path not found: {src}")

    @staticmethod
    def _locate_folder(base):
        for cand in (base, base / "ESC-50-master", base / "ESC-50"):
            if (cand / "meta" / "esc50.csv").exists():
                return cand
        return None

    @staticmethod
    def _find_default():
        data = ROOT / "data"
        for z in sorted(data.glob("*.zip")):
            return z
        return data if Esc50._locate_folder(data) else None

    # ---------------------------------------------------------------- raw access
    def _read(self, rel):
        """Bytes of 'meta/esc50.csv' or 'audio/<file>.wav' from the active source."""
        name = Path(rel).name
        if self._zip is not None:
            return self._zip.read(self._members[name if name != "esc50.csv" else "esc50.csv"])
        if self._folder is not None:
            return (self._folder / rel).read_bytes()
        local = self.cache / rel
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            try:
                with urllib.request.urlopen(RAW_URL + rel, timeout=60) as r:
                    local.write_bytes(r.read())
            except Exception as exc:
                raise RuntimeError(
                    f"Could not download {rel} from GitHub ({exc}). Point the app to your ESC-50 zip or folder.") from exc
        return local.read_bytes()

    def meta(self):
        """List of csv rows (dicts): filename, fold, target, category, ..."""
        if not hasattr(self, "_meta"):
            self._meta = list(csv.DictReader(io.StringIO(self._read("meta/esc50.csv").decode("utf-8"))))
        return self._meta

    def categories(self):
        return sorted({r["category"] for r in self.meta()})

    def clips_of(self, category, folds=None):
        return sorted(r["filename"] for r in self.meta()
                      if r["category"] == category and (folds is None or int(r["fold"]) in folds))

    def load(self, filename):
        """Preprocessed 16 kHz mono clip (cached in memory)."""
        if filename not in self._clips:
            sr, x = wavfile.read(io.BytesIO(self._read(f"audio/{filename}")))
            self._clips[filename] = preprocess(x, sr)
        return self._clips[filename]

    def prefetch(self, categories, workers=8):
        """Load every clip of the given classes in parallel (downloads them if needed)."""
        names = [f for c in categories for f in self.clips_of(c)]
        with ThreadPoolExecutor(workers) as ex:
            list(ex.map(self.load, names))
        return len(names)
