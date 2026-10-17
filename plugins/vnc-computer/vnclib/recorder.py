"""Fixed-rate framebuffer capture to numbered PNGs + frames.jsonl.

Never encodes video: frames are assembled into a video on another machine
(see README "Recording -> video assembly").
"""
import json
import os
import queue
import threading
import time

from .imaging import encode_png, scaled_size


class Recorder:
    def __init__(self, grab, out_dir, interval_ms=200, scale=1.0, log=None):
        """grab() -> (width, height, rgb) or raises."""
        self.grab = grab
        self.out_dir = os.path.abspath(out_dir)
        self.interval = max(20, int(interval_ms)) / 1000.0
        self.scale = float(scale)
        self.log = log or (lambda msg: None)
        self.frames = 0
        self.dropped = 0
        self.errors = 0
        self.size = None
        self.started_wall = None
        self.stopped_wall = None
        self._stop = threading.Event()
        self._queue = queue.Queue(maxsize=16)
        self._capture = threading.Thread(target=self._capture_loop, name='rec-capture', daemon=True)
        self._writer = threading.Thread(target=self._write_loop, name='rec-writer', daemon=True)

    def start(self):
        os.makedirs(self.out_dir, exist_ok=True)
        if os.path.exists(os.path.join(self.out_dir, 'frames.jsonl')):
            raise FileExistsError('%s already holds a recording (frames.jsonl)' % self.out_dir)
        self._index = open(os.path.join(self.out_dir, 'frames.jsonl'), 'a', encoding='utf-8')
        self.started_wall = time.time()
        self._t0 = time.monotonic()
        self._writer.start()
        self._capture.start()
        return self

    def _capture_loop(self):
        seq = 0
        next_t = time.monotonic()
        while not self._stop.is_set():
            try:
                w, h, rgb = self.grab()
                item = (seq, time.time(), time.monotonic() - self._t0, w, h, rgb)
                seq += 1
                try:
                    self._queue.put_nowait(item)
                except queue.Full:
                    self.dropped += 1
            except Exception as exc:
                self.errors += 1
                if self.errors in (1, 10, 100):
                    self.log('record: capture error #%d: %s' % (self.errors, exc))
            next_t += self.interval
            now = time.monotonic()
            if next_t < now:  # fell behind: skip missed slots, keep the grid
                missed = int((now - next_t) / self.interval) + 1
                next_t += missed * self.interval
            self._stop.wait(max(0.0, next_t - time.monotonic()))
        self._queue.put(None)

    def _write_loop(self):
        while True:
            item = self._queue.get()
            if item is None:
                break
            seq, wall, rel, w, h, rgb = item
            out = scaled_size(w, h, self.scale) if self.scale != 1.0 else (w, h)
            name = 'frame_%06d.png' % seq
            path = os.path.join(self.out_dir, name)
            with open(path, 'wb') as fh:
                fh.write(encode_png(rgb, w, h, out_size=out, level=1))
            self.size = out
            self._index.write(json.dumps({'frame': seq, 't': round(wall, 4), 't_rel': round(rel, 4),
                                          'file': name, 'path': path,
                                          'width': out[0], 'height': out[1]}) + '\n')
            self._index.flush()
            self.frames += 1

    def stop(self):
        self._stop.set()
        self._capture.join(timeout=10)
        self._writer.join(timeout=120)
        self._index.close()
        self.stopped_wall = time.time()
        summary = self.summary()
        with open(os.path.join(self.out_dir, 'recording.json'), 'w', encoding='utf-8') as fh:
            json.dump(summary, fh, indent=2)
            fh.write('\n')
        return summary

    def summary(self):
        end = self.stopped_wall or time.time()
        return {'out_dir': self.out_dir, 'frames': self.frames, 'dropped': self.dropped,
                'capture_errors': self.errors, 'interval_ms': int(self.interval * 1000),
                'frame_size': list(self.size) if self.size else None,
                'started': self.started_wall, 'stopped': self.stopped_wall,
                'duration_s': round(end - self.started_wall, 3) if self.started_wall else 0,
                'index': os.path.join(self.out_dir, 'frames.jsonl')}
