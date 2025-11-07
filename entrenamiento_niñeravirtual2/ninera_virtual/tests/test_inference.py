from django.test import TestCase

from deteccion.services.inference import run_inference


class InferenceServiceTests(TestCase):
    def test_run_inference_returns_metadata(self) -> None:
        payload = run_inference("media/uploads/example.jpg", {"primary": object()})

        self.assertEqual(payload["output_path"], "media/uploads/example.jpg")
        self.assertIn("primary", payload["models_used"])
