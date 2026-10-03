"""
Production Deployment Smoke Test Suite for FASTKEYS.
Designed according to Director Priority 2 specifications:
Audits production deployment endpoints, verifies /api/health, upload analysis,
expected payload schema, and temporary-file cleanup without changing FASTKEYS product behavior.
"""
import os
import sys
import glob
import tempfile
import unittest
import requests

SERVER_URL = os.environ.get("FASTKEYS_SERVER_URL", "http://127.0.0.1:8000")

class FastkeysProductionSmokeTest(unittest.TestCase):
    
    def test_01_health_endpoint(self):
        """Verifies that the /api/health endpoint is online and reports open-source AI and DSP cores."""
        url = f"{SERVER_URL}/api/health"
        resp = requests.get(url, timeout=10)
        self.assertEqual(resp.status_code, 200, f"Expected 200 from health endpoint, got {resp.status_code}")
        
        data = resp.json()
        self.assertEqual(data.get("status"), "ok")
        self.assertIn("Spotify Basic Pitch", data.get("ai_core", ""))
        self.assertIn("Krumhansl-Schmuckler", data.get("dsp_core", ""))
        print("\n[SMOKE PASS] /api/health is online and reporting AI + DSP core components.")

    def test_02_upload_analysis_and_schema(self):
        """Uploads a supported audio fixture, verifies HTTP 200, validates play map schema."""
        test_audio = "fixture_pop_C.wav"
        if not os.path.exists(test_audio):
            self.skipTest(f"Audio fixture {test_audio} not found locally.")
            
        url = f"{SERVER_URL}/api/analyze"
        with open(test_audio, "rb") as f:
            files = {"file": ("fixture_pop_C.wav", f, "audio/wav")}
            resp = requests.post(url, files=files, timeout=60)
            
        self.assertEqual(resp.status_code, 200, f"Analysis failed with {resp.status_code}: {resp.text}")
        payload = resp.json()
        
        # Verify required response schema
        required_keys = [
            "filename", "duration", "key", "key_confidence",
            "chord_progression", "degree_sequence", "melody_notes",
            "solfa_sequence", "raw_note_count"
        ]
        for key in required_keys:
            self.assertIn(key, payload, f"Missing required response field: {key}")
            
        self.assertIsInstance(payload["chord_progression"], list)
        self.assertIsInstance(payload["melody_notes"], list)
        self.assertGreater(payload["raw_note_count"], 0)
        print(f"\n[SMOKE PASS] Upload analysis succeeded. Key: {payload['key']}, Degrees: {payload['degree_sequence']}")

    def test_03_temp_file_cleanup(self):
        """Verifies that upload analysis cleans up temporary audio files in the OS temp directory."""
        temp_dir = tempfile.gettempdir()
        initial_temp_files = set(glob.glob(os.path.join(temp_dir, "tmp*")))
        
        test_audio = "fixture_lead_D.wav"
        if not os.path.exists(test_audio):
            self.skipTest(f"Audio fixture {test_audio} not found locally.")
            
        url = f"{SERVER_URL}/api/analyze"
        with open(test_audio, "rb") as f:
            files = {"file": ("fixture_lead_D.wav", f, "audio/wav")}
            resp = requests.post(url, files=files, timeout=60)
            
        self.assertEqual(resp.status_code, 200)
        
        post_temp_files = set(glob.glob(os.path.join(temp_dir, "tmp*")))
        leaked_files = [f for f in (post_temp_files - initial_temp_files) if "_converted.wav" in f]
        self.assertEqual(len(leaked_files), 0, f"Temporary audio files leaked in {temp_dir}: {leaked_files}")
        print("\n[SMOKE PASS] Temporary audio files cleanly unlinked and deleted in post-request finally block.")

if __name__ == "__main__":
    unittest.main()
