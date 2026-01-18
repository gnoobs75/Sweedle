"""
TqdmCapture - Utility to capture tqdm progress output and send WebSocket updates.

Intercepts stderr to parse tqdm progress bars like:
  Diffusion Sampling::  12%|███████▌        | 3/25 [00:01<00:08, 2.60it/s]
  Volume Decoding:      38%|████████████    | 338/899 [00:00<00:01, 319.98it/s]

Extracts stage name, percentage, current/total, and sends via callback.
"""

import sys
import re
import io
import threading
from typing import Callable, Optional
from contextlib import contextmanager


class TqdmCapture:
    """Captures stderr and parses tqdm progress bars."""

    # Pattern to match tqdm output lines
    # Examples:
    #   Diffusion Sampling::   4%|██▎   | 1/25 [00:00<00:10, 2.28it/s]
    #   Volume Decoding:  38%|███▎   | 338/899 [00:00<00:01, 319.98it/s]
    TQDM_PATTERN = re.compile(
        r'^(.+?):\s*(\d+)%\|[█▏▎▍▌▋▊▉\s]*\|\s*(\d+)/(\d+)'
    )

    def __init__(
        self,
        callback: Callable[[str, float, int, int], None],
        min_update_interval: float = 0.1,
    ):
        """
        Initialize tqdm capture.

        Args:
            callback: Function called with (stage_name, percent, current, total)
            min_update_interval: Minimum seconds between callback calls
        """
        self.callback = callback
        self.min_update_interval = min_update_interval
        self._last_update_time = 0
        self._original_stderr = None
        self._capture_buffer = io.StringIO()
        self._lock = threading.Lock()

    def _parse_and_callback(self, line: str):
        """Parse a line and call callback if it's tqdm output."""
        # Remove carriage returns and clean the line
        line = line.replace('\r', '').strip()
        if not line:
            return

        match = self.TQDM_PATTERN.search(line)
        if match:
            stage = match.group(1).strip()
            percent = int(match.group(2))
            current = int(match.group(3))
            total = int(match.group(4))

            # Throttle updates
            import time
            current_time = time.time()
            if current_time - self._last_update_time >= self.min_update_interval:
                self._last_update_time = current_time
                try:
                    self.callback(stage, percent / 100.0, current, total)
                except Exception:
                    pass  # Don't let callback errors break capture


class TqdmCaptureWriter:
    """A file-like object that captures writes and forwards to both original and parser."""

    def __init__(self, original_stderr, capture: TqdmCapture):
        self.original = original_stderr
        self.capture = capture
        self.buffer = ""

    def write(self, text):
        # Write to original stderr so it still shows in console
        if self.original:
            self.original.write(text)
            self.original.flush()

        # Buffer and process lines
        self.buffer += text
        while '\r' in self.buffer or '\n' in self.buffer:
            # Find the earliest line ending
            r_pos = self.buffer.find('\r')
            n_pos = self.buffer.find('\n')

            if r_pos == -1:
                pos = n_pos
            elif n_pos == -1:
                pos = r_pos
            else:
                pos = min(r_pos, n_pos)

            line = self.buffer[:pos]
            self.buffer = self.buffer[pos + 1:]

            if line.strip():
                self.capture._parse_and_callback(line)

    def flush(self):
        if self.original:
            self.original.flush()

    def fileno(self):
        if self.original:
            return self.original.fileno()
        return 2  # stderr default

    def isatty(self):
        if self.original:
            return self.original.isatty()
        return False


@contextmanager
def capture_tqdm_progress(
    callback: Callable[[str, float, int, int], None],
    min_update_interval: float = 0.1,
):
    """
    Context manager to capture tqdm progress and call callback.

    Usage:
        def on_progress(stage, percent, current, total):
            print(f"{stage}: {percent*100:.0f}% ({current}/{total})")

        with capture_tqdm_progress(on_progress):
            # Code that uses tqdm will have progress captured
            run_inference()

    Args:
        callback: Function called with (stage_name, percent, current, total)
        min_update_interval: Minimum seconds between callback calls
    """
    capture = TqdmCapture(callback, min_update_interval)
    original_stderr = sys.stderr

    try:
        # Replace stderr with our capturing writer
        sys.stderr = TqdmCaptureWriter(original_stderr, capture)
        yield capture
    finally:
        # Restore original stderr
        sys.stderr = original_stderr
