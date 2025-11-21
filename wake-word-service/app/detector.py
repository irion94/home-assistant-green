"""
OpenWakeWord Detector Wrapper
"""

import os
import logging
import numpy as np
from openwakeword.model import Model

logger = logging.getLogger(__name__)


class WakeWordDetector:
    """Wrapper for OpenWakeWord detection"""

    def __init__(self, model_name: str = "hey_jarvis_v0.1", threshold: float = 0.5):
        """
        Initialize wake-word detector

        Args:
            model_name: Name of the wake-word model
            threshold: Detection threshold (0.0 to 1.0)
        """
        self.model_name = model_name
        self.threshold = threshold
        self.model = None

        self._load_model()

    def _load_model(self):
        """Load OpenWakeWord model"""
        logger.info(f"Loading wake-word model: {self.model_name}")

        try:
            # Get inference framework
            inference_framework = os.getenv("INFERENCE_FRAMEWORK", "tflite")

            # Download models if needed (wake-word + melspectrogram)
            model_dir = self._download_models(self.model_name)

            # Initialize model with absolute path to wake-word model
            # OpenWakeWord will automatically find preprocessing models in the same directory
            if model_dir:
                # Determine file extension based on inference framework
                ext = ".onnx" if inference_framework == "onnx" else ".tflite"
                wakeword_model_path = os.path.join(model_dir, f"{self.model_name}_v0.1{ext}")

                logger.info(f"Loading model from: {wakeword_model_path}")

                self.model = Model(
                    wakeword_models=[wakeword_model_path],
                    inference_framework=inference_framework
                )
            else:
                # Use default package models
                self.model = Model(
                    wakeword_models=[f"{self.model_name}_v0.1"],
                    inference_framework=inference_framework
                )

            logger.info(f"Model loaded successfully: {self.model_name}")
            logger.info(f"Inference framework: {inference_framework}")

        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise

    def _download_models(self, model_name: str) -> str:
        """
        Download wake-word and preprocessing models

        Args:
            model_name: Name of the wake-word model to download

        Returns:
            Path to models directory or empty string to use package models
        """
        from openwakeword.utils import download_models

        model_dir = "/app/models"
        inference_framework = os.getenv("INFERENCE_FRAMEWORK", "tflite")
        ext = ".onnx" if inference_framework == "onnx" else ".tflite"
        model_filename = f"{model_name}_v0.1{ext}"
        model_path = os.path.join(model_dir, model_filename)
        melspec_path = os.path.join(model_dir, f"melspectrogram{ext}")

        # Check if both models already exist
        if os.path.exists(model_path) and os.path.exists(melspec_path):
            logger.info(f"Models already exist: {model_name}, melspectrogram")
            return model_dir

        # Download pre-trained models using OpenWakeWord's utility
        try:
            logger.info(f"Downloading OpenWakeWord models ({model_name} + melspectrogram)...")
            os.makedirs(model_dir, exist_ok=True)

            # Download both the wake-word model and melspectrogram (required for audio preprocessing)
            # download_models expects a list of model names and target directory
            download_models([model_name, "melspectrogram"], model_dir)

            # Verify both models were downloaded
            if os.path.exists(model_path) and os.path.exists(melspec_path):
                logger.info(f"Models downloaded successfully to {model_dir}")
                return model_dir
            else:
                logger.warning(f"Some models missing after download. Available models:")
                for f in os.listdir(model_dir):
                    if f.endswith('.tflite'):
                        logger.info(f"  - {f}")

                # Return empty string to use package default models
                return ""

        except Exception as e:
            logger.error(f"Failed to download models: {e}")
            logger.info("Will try to use package default models")
            return ""

    def predict(self, audio_chunk: np.ndarray) -> float:
        """
        Run wake-word prediction on audio chunk

        Args:
            audio_chunk: Audio data as numpy array (mono, 16kHz)

        Returns:
            Confidence score (0.0 to 1.0)
        """
        if self.model is None:
            logger.error("Model not loaded")
            return 0.0

        try:
            # Ensure audio is correct format (mono, int16)
            if audio_chunk.dtype != np.int16:
                audio_chunk = audio_chunk.astype(np.int16)

            # Run prediction
            prediction = self.model.predict(audio_chunk)

            # Debug: Log prediction keys (only once)
            if not hasattr(self, '_logged_keys'):
                logger.info(f"Prediction keys: {list(prediction.keys())}")
                self._logged_keys = True

            # Get score for our wake word model
            # OpenWakeWord returns a dict with model names as keys
            # The key might be the full path or just the model name
            score = 0.0

            # Try different possible keys
            for key in prediction.keys():
                if self.model_name in str(key) or "hey_jarvis" in str(key).lower():
                    score = max(score, float(prediction[key]))
                    break

            # If no match found, try to get max score from all numeric values
            if score == 0.0:
                scores = [float(v) for v in prediction.values() if isinstance(v, (int, float))]
                score = max(scores) if scores else 0.0

            return float(score)

        except Exception as e:
            logger.error(f"Error during prediction: {e}")
            return 0.0

    def reset(self):
        """Reset model state"""
        if self.model:
            self.model.reset()
