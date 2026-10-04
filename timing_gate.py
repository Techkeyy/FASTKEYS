"""Measure the final timing and melody gate without changing inference data."""
import json
import os
import sys
from pathlib import Path

import engine


ROOT = Path(__file__).resolve().parent
GROUND_TRUTH = {
    'timing_fixture_C.wav': {
        'melody': [
            {'midi': 60, 'start': 0.25, 'end': 0.75},
            {'midi': 65, 'start': 1.25, 'end': 1.75},
            {'midi': 67, 'start': 2.25, 'end': 2.75},
            {'midi': 64, 'start': 3.25, 'end': 3.75},
        ],
        'chord_boundaries': [1.0, 2.0, 3.0],
    }
}


def nearest_events(expected, actual):
    remaining = list(actual)
    matched = []
    for reference in expected:
        options = [
            event for event in remaining
            if int(event.get('midi', -1)) == reference['midi']
        ]
        if not options:
            matched.append({'expected': reference, 'actual': None})
            continue
        event = min(options, key=lambda candidate: abs(candidate['start'] - reference['start']))
        remaining.remove(event)
        matched.append({'expected': reference, 'actual': event})
    return matched


def timing_errors(matches):
    onset = [abs(item['actual']['start'] - item['expected']['start']) for item in matches if item['actual']]
    offset = [abs(item['actual']['end'] - item['expected']['end']) for item in matches if item['actual']]
    return {
        'matched': len(onset),
        'missing': sum(item['actual'] is None for item in matches),
        'mean_onset_error_seconds': sum(onset) / len(onset) if onset else None,
        'max_onset_error_seconds': max(onset) if onset else None,
        'mean_offset_error_seconds': sum(offset) / len(offset) if offset else None,
        'max_offset_error_seconds': max(offset) if offset else None,
        'matches': matches,
    }


def analyze(path, expected=None):
    os.environ['FASTKEYS_TIMING_TRACE'] = '1'
    result = engine.analyze_audio_file(str(ROOT / path))
    raw = result.pop('raw_note_events', [])
    report = {
        'file': path,
        'duration': result['duration'],
        'key': result['key'],
        'chords': result['chord_progression'],
        'selected_melody': result['melody_notes'],
        'raw_note_events': raw,
        'raw_note_count': len(raw),
        'analysis_seconds': result['analysis_seconds'],
    }
    if expected:
        raw_matches = nearest_events(expected['melody'], raw)
        selected_matches = nearest_events(expected['melody'], result['melody_notes'])
        actual_boundaries = [event['start'] for event in result['chord_progression'][1:]]
        boundary_errors = [
            abs(actual - target)
            for actual, target in zip(actual_boundaries, expected['chord_boundaries'])
        ]
        report['ground_truth'] = expected
        report['raw_timing'] = timing_errors(raw_matches)
        report['selected_timing'] = timing_errors(selected_matches)
        report['chord_boundary_timing'] = {
            'expected': expected['chord_boundaries'],
            'actual': actual_boundaries,
            'mean_error_seconds': sum(boundary_errors) / len(boundary_errors) if boundary_errors else None,
            'max_error_seconds': max(boundary_errors) if boundary_errors else None,
        }
    return report


def representative_moments(report, moments):
    rows = []
    for timestamp in moments:
        chord = next((event for event in report['chords'] if event['start'] <= timestamp < event['end']), None)
        melody = next((event for event in report['selected_melody'] if event['start'] <= timestamp < event['end']), None)
        rows.append({'time': timestamp, 'audible_check': 'manual listening checkpoint', 'backend_chord': chord, 'backend_melody': melody})
    return rows


if __name__ == '__main__':
    reports = {
        'deterministic': analyze('timing_fixture_C.wav', GROUND_TRUTH['timing_fixture_C.wav']),
        'hymn': analyze('when_i_survey_20s.wav'),
        'non_hymn': analyze('st_louis_blues_20s.wav'),
    }
    reports['hymn']['representative_moments'] = representative_moments(reports['hymn'], [2.0, 6.0, 10.0, 14.0])
    reports['non_hymn']['representative_moments'] = representative_moments(reports['non_hymn'], [2.0, 6.0, 10.0, 14.0])
    destination = ROOT / 'evidence' / 'timing-gate-engine-proof.json'
    destination.write_text(json.dumps(reports, indent=2), encoding='utf-8')
    print(json.dumps(reports, indent=2))
