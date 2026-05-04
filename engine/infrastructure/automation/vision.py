from __future__ import annotations

import contextlib
import os
from collections.abc import Callable

import cv2
import numpy as np

from engine.domain.models import TemplateMatch


class VisionEngine:
    """OpenCV-based template matching with multi-scale search and learning."""

    SCALE_MIN = 0.3
    SCALE_MAX = 3.0
    COARSE_STEP = 0.08
    FINE_OFFSETS = [0, -0.03, 0.03, -0.06, 0.06, -0.10, 0.10, -0.15, 0.15, -0.20, 0.20]
    EARLY_EXIT_SCORE = 0.88
    DEFAULT_THRESHOLD = 0.65

    def __init__(
        self,
        dpi: int,
        template_source_dpi: int = 144,
        log_callback: Callable[[str], None] | None = None,
    ) -> None:
        self._dpi = dpi
        self._template_source_dpi = template_source_dpi
        self._log_callback = log_callback
        self._learned_scales: dict[str, dict[str, object]] = {}

    def set_dpi(self, dpi: int) -> None:
        self._dpi = dpi

    def set_template_source_dpi(self, dpi: int) -> None:
        self._template_source_dpi = dpi

    def set_learned_scales(self, scales: dict[str, dict[str, object]]) -> None:
        self._learned_scales = scales

    def get_learned_scales(self) -> dict[str, dict[str, object]]:
        return self._learned_scales

    def clear_learned_scales(self) -> None:
        self._learned_scales.clear()

    def _log(self, msg: str) -> None:
        if self._log_callback:
            with contextlib.suppress(Exception):
                self._log_callback(msg)

    def _calc_dpi_ratio(self) -> float:
        src = self._template_source_dpi
        return self._dpi / (src if src > 0 else 144)

    def _scale_key(self, tpath: str) -> str:
        return os.path.basename(tpath)

    def _get_preferred_scale(self, tpath: str) -> float | None:
        rec = self._learned_scales.get(self._scale_key(tpath))
        if rec is None:
            return None
        sd = rec.get("dpi", self._dpi)
        ss = rec.get("scale", 1.0)
        if isinstance(sd, (int, float)) and isinstance(ss, (int, float)):
            if sd != self._dpi and float(sd) > 0:
                return float(ss) * (self._dpi / float(sd))
            return float(ss)
        return None

    def _save_preferred_scale(self, tpath: str, scale: float) -> None:
        from datetime import datetime

        self._learned_scales[self._scale_key(tpath)] = {
            "scale": round(scale, 4),
            "dpi": self._dpi,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }

    def match_template(
        self, screen: np.ndarray, tpath: str, threshold: float | None = None
    ) -> TemplateMatch | None:
        if not tpath or not os.path.exists(tpath):
            return None
        if threshold is None:
            threshold = self.DEFAULT_THRESHOLD
        tpl_bgr = self._imread_safe(tpath)
        if tpl_bgr is None:
            self._log(f"[Match] failed to read: {tpath}")
            return None

        sg = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        tg = cv2.cvtColor(tpl_bgr, cv2.COLOR_BGR2GRAY)
        sh, sw = sg.shape[:2]
        dr = self._calc_dpi_ratio()
        tn = os.path.basename(tpath)
        pref = self._get_preferred_scale(tpath)

        if pref is not None and self.SCALE_MIN <= pref <= self.SCALE_MAX:
            r = self._try_match(sg, tg, pref, threshold, sw, sh)
            if r is not None:
                self._log(f"[Match] fast [{tn}] s={pref:.3f} sc={r.confidence:.3f}")
                return r
            for o in self.FINE_OFFSETS:
                if o == 0:
                    continue
                s = pref + o
                if not (self.SCALE_MIN <= s <= self.SCALE_MAX):
                    continue
                r = self._try_match(sg, tg, s, threshold, sw, sh)
                if r is not None:
                    self._save_preferred_scale(tpath, r.scale)
                    return r

        sl = self._build_scale_list(dr, pref)
        best: TemplateMatch | None = None
        tested = 0
        for s in sl:
            tested += 1
            r = self._try_match(sg, tg, s, threshold, sw, sh)
            if r is not None and (best is None or r.confidence > best.confidence):
                best = r
                if best.confidence >= self.EARLY_EXIT_SCORE:
                    break

        if best is not None:
            self._log(
                f"[Match] OK [{tn}] s={best.scale:.3f} sc={best.confidence:.3f} t={tested}"
            )
            self._save_preferred_scale(tpath, best.scale)
            return best

        self._log(f"[Match] FAIL [{tn}] t={tested}")
        return None

    def _try_match(
        self, sg: np.ndarray, tg: np.ndarray, scale: float, thr: float, sw: int, sh: int
    ) -> TemplateMatch | None:
        if abs(scale - 1.0) < 0.005:
            scaled = tg
        else:
            scaled = cv2.resize(
                tg,
                None,
                fx=scale,
                fy=scale,
                interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR,
            )
        rh, rw = scaled.shape[:2]
        if rw > sw or rh > sh or rw < 6 or rh < 6:
            return None
        try:
            res = cv2.matchTemplate(sg, scaled, cv2.TM_CCOEFF_NORMED)
            _, mv, _, ml = cv2.minMaxLoc(res)
        except cv2.error:
            return None
        if mv >= thr:
            return TemplateMatch(
                found=True,
                x=ml[0],
                y=ml[1],
                width=rw,
                height=rh,
                confidence=round(float(mv), 4),
                scale=round(scale, 4),
            )
        return None

    def _build_scale_list(self, dr: float, pref: float | None = None) -> list[float]:
        c: list[float] = []
        for o in self.FINE_OFFSETS:
            s = dr + o
            if self.SCALE_MIN <= s <= self.SCALE_MAX:
                c.append(round(s, 4))
        if abs(dr - 1.0) > 0.15:
            for o in self.FINE_OFFSETS:
                s = 1.0 + o
                if self.SCALE_MIN <= s <= self.SCALE_MAX:
                    c.append(round(s, 4))
        if pref is not None:
            for o in self.FINE_OFFSETS:
                s = pref + o
                if self.SCALE_MIN <= s <= self.SCALE_MAX:
                    c.append(round(s, 4))
        s = dr
        while s <= self.SCALE_MAX:
            c.append(round(s, 4))
            s += self.COARSE_STEP
        s = dr - self.COARSE_STEP
        while s >= self.SCALE_MIN:
            c.append(round(s, 4))
            s -= self.COARSE_STEP
        seen: set[float] = set()
        r: list[float] = []
        for s in c:
            k = round(s, 3)
            if k not in seen:
                seen.add(k)
                r.append(s)
        return r

    @staticmethod
    def _imread_safe(filepath: str) -> np.ndarray | None:
        if not filepath or not os.path.exists(filepath):
            return None
        try:
            img = cv2.imread(filepath)
            if img is not None:
                return img
        except Exception:
            pass
        try:
            with open(filepath, "rb") as f:
                data = np.frombuffer(f.read(), dtype=np.uint8)
            return cv2.imdecode(data, cv2.IMREAD_COLOR)
        except Exception:
            return None
