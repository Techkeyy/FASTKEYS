import sys
import types
import unittest

# These tests exercise deterministic selection and timestamp helpers without
# starting TensorFlow. The real Basic Pitch path is covered by the fixture and
# browser timing runs.
_basic_pitch = types.ModuleType('basic_pitch')
_basic_pitch_inference = types.ModuleType('basic_pitch.inference')
_basic_pitch_inference.predict = lambda *args, **kwargs: (None, None, [])
_basic_pitch.inference = _basic_pitch_inference
sys.modules.setdefault('basic_pitch', _basic_pitch)
sys.modules.setdefault('basic_pitch.inference', _basic_pitch_inference)

from engine import analysis_chunk_ranges, select_melody_events


class TimingGateTests(unittest.TestCase):
    def test_chunk_ranges_remain_absolute_and_cover_the_song(self):
        self.assertEqual(list(analysis_chunk_ranges(65.0)), [(0.0, 30.0), (27.0, 57.0), (54.0, 65.0)])

    def test_selection_preserves_real_onsets_offsets_and_rests(self):
        raw = [
            {'start': 0.012, 'end': 0.952, 'midi': 52, 'amplitude': 0.638},
            {'start': 0.244, 'end': 0.789, 'midi': 60, 'amplitude': 0.802},
            {'start': 1.242, 'end': 1.800, 'midi': 65, 'amplitude': 0.795},
            {'start': 2.254, 'end': 2.788, 'midi': 67, 'amplitude': 0.765},
            {'start': 3.252, 'end': 3.798, 'midi': 64, 'amplitude': 0.755},
        ]
        selected = select_melody_events(raw, 0, 4.2)
        self.assertEqual([event['midi'] for event in selected], [60, 65, 67, 64])
        self.assertEqual([event['start'] for event in selected], [0.244, 1.242, 2.254, 3.252])
        self.assertEqual([event['end'] for event in selected], [0.789, 1.8, 2.788, 3.798])
        self.assertLess(selected[0]['end'], selected[1]['start'])

    def test_selector_keeps_one_note_per_overlap_and_drops_short_harmonic(self):
        raw = [
            {'start': 0.0, 'end': 0.5, 'midi': 60, 'amplitude': 0.70},
            {'start': 0.0, 'end': 0.2, 'midi': 72, 'amplitude': 0.31},
            {'start': 0.48, 'end': 1.0, 'midi': 62, 'amplitude': 0.66},
            {'start': 0.98, 'end': 1.15, 'midi': 77, 'amplitude': 0.31},
        ]
        selected = select_melody_events(raw, 0, 1.2)
        self.assertEqual([event['midi'] for event in selected], [60, 62])
        self.assertTrue(all(left['end'] <= right['start'] for left, right in zip(selected, selected[1:])))


if __name__ == '__main__':
    unittest.main()
