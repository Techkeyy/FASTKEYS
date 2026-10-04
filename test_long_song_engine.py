import sys
import types
import unittest

# These tests cover the deterministic timestamp helpers only. Keep the test
# process independent of TensorFlow/Basic Pitch startup and leave neural
# inference coverage to the real browser/API long-song gate.
_basic_pitch = types.ModuleType('basic_pitch')
_basic_pitch_inference = types.ModuleType('basic_pitch.inference')
_basic_pitch_inference.predict = lambda *args, **kwargs: (None, None, [])
_basic_pitch.inference = _basic_pitch_inference
sys.modules.setdefault('basic_pitch', _basic_pitch)
sys.modules.setdefault('basic_pitch.inference', _basic_pitch_inference)

from engine import analysis_chunk_ranges, merge_overlapping_notes


class LongSongEngineTests(unittest.TestCase):
    def test_chunk_ranges_cover_full_duration_with_absolute_starts(self):
        ranges = list(analysis_chunk_ranges(65.0))
        self.assertEqual(ranges, [(0.0, 30.0), (27.0, 57.0), (54.0, 65.0)])
        self.assertEqual(ranges[0][0], 0.0)
        self.assertEqual(ranges[-1][1], 65.0)

    def test_overlap_deduplicates_same_note_without_rewriting_absolute_time(self):
        events = [
            {'start': 29.94, 'end': 30.34, 'midi': 64, 'amplitude': 0.7, 'chunk': 0},
            {'start': 30.02, 'end': 30.41, 'midi': 64, 'amplitude': 0.8, 'chunk': 1},
            {'start': 30.50, 'end': 30.90, 'midi': 64, 'amplitude': 0.7, 'chunk': 1},
        ]
        merged = merge_overlapping_notes(events)
        self.assertEqual(len(merged), 2)
        self.assertAlmostEqual(merged[0]['start'], 29.94)
        self.assertAlmostEqual(merged[0]['end'], 30.41)
        self.assertAlmostEqual(merged[1]['start'], 30.50)

    def test_different_pitches_at_boundary_are_preserved(self):
        events = [
            {'start': 29.98, 'end': 30.31, 'midi': 64, 'amplitude': 0.7, 'chunk': 0},
            {'start': 30.02, 'end': 30.35, 'midi': 65, 'amplitude': 0.7, 'chunk': 1},
        ]
        self.assertEqual(len(merge_overlapping_notes(events)), 2)


if __name__ == '__main__':
    unittest.main()
