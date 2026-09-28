"""
trufor_detector.py
Complete TruFor detector with full implementation

WHAT THIS FILE DOES:
- Loads the TruFor model
- Preprocesses images for TruFor
- Runs inference to detect manipulation
- Returns manipulation score + heatmap
"""

import torch
import numpy as np
from PIL import Image
import cv2
import logging
import os
from typing import Tuple, Optional, Dict
import io

from app.config import BASE_DIR

logger = logging.getLogger(__name__)

class TruForDetector:
    """
    Complete TruFor Detector
    
    PURPOSE:
    Detect if an image has been digitally manipulated using deep learning
    
    HOW IT WORKS:
    1. Load pre-trained TruFor model (trained on 2M images)
    2. Preprocess input image (resize, normalize)
    3. Run through neural network
    4. Get manipulation probability + heatmap
    
    USAGE:
    detector = TruForDetector()
    result = detector.detect(image_bytes)
    # Returns: {'is_manipulated': True/False, 'confidence': 0.85, ...}
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize TruFor detector
        
        WHAT HAPPENS HERE:
        1. Set device (CPU or GPU)
        2. Model will be loaded lazily (only when first used)
        
        Args:
            model_path: Path to pre-trained model weights
        
        WHY LAZY LOADING:
        - Faster startup (don't load 500MB model if not needed)
        - Only load when actually detecting manipulation
        """
        model_path = model_path or os.getenv(
            "TRUFOR_MODEL_PATH",
            os.path.join(BASE_DIR, "models", "trufor", "trufor_model.pth.tar"),
        )
        # Fail early (caller falls back to ELA only) instead of failing on every request
        if not os.path.isfile(model_path):
            raise FileNotFoundError(f"TruFor weights not found at {model_path}")

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.model = None
        self.model_path = model_path
        
        logger.info(f"TruFor will use device: {self.device}")
        if self.device.type == 'cuda':
            logger.info("✓ GPU available - TruFor will run faster")
        else:
            logger.info("ℹ Using CPU - TruFor will be slower (3-5s per image)")
    
    def _load_model(self):
        """
        Load the TruFor model (called automatically on first use)
        
        WHAT HAPPENS:
        1. Import model architecture
        2. Load pre-trained weights from disk
        3. Move model to GPU/CPU
        4. Set to evaluation mode
        
        WHY WE DO THIS:
        - Model is 500MB - only load once, reuse for all images
        - Evaluation mode disables training-specific layers
        """
        if self.model is not None:
            return  # Already loaded
        
        try:
            logger.info("Loading TruFor model... (this may take 10-20 seconds)")
            
            # Import model architecture
            from app.agents.forensics.trufor_model import load_trufor_model
            
            # Load pre-trained model
            self.model = load_trufor_model(self.model_path, device=str(self.device))
            
            logger.info("✓ TruFor model loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load TruFor model: {e}")
            logger.error("TruFor will not be available. Falling back to ELA only.")
            raise
    
    def _preprocess_image(self, image_bytes: bytes) -> torch.Tensor:
        """
        Preprocess image for TruFor model
        
        WHAT HAPPENS:
        1. Load image from bytes
        2. Convert to RGB (in case it's grayscale or RGBA)
        3. Resize to 512x512 (TruFor's expected input size)
        4. Normalize pixel values (0-255 → 0-1 → standardized)
        5. Convert to PyTorch tensor
        6. Add batch dimension
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            Preprocessed tensor ready for model
            Shape: (1, 3, 384, 384)
                1 = batch size
                3 = RGB channels
                384x384 = image size
        
        WHY THESE STEPS:
        - RGB: Model expects 3 channels
        - 384x384: Model was trained on this size
        - Normalization: Makes training/inference stable
        - Tensor: PyTorch format
        """
        # Step 1: Load image
        image = Image.open(io.BytesIO(image_bytes))
        
        # Step 2: Convert to RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
        
        # Step 3: Resize to 384x384 (TruFor's expected input size)
        # LANCZOS = high-quality resampling
        image = image.resize((384, 384), Image.LANCZOS)
        
        # Step 4: Convert to numpy array and normalize
        img_array = np.array(image).astype(np.float32)
        img_array = img_array / 255.0  # Scale to 0-1
        
        # Step 5: Standardize using ImageNet mean/std
        # These are standard values used in most vision models
        mean = np.array([0.485, 0.456, 0.406])  # ImageNet mean (R, G, B)
        std = np.array([0.229, 0.224, 0.225])   # ImageNet std (R, G, B)
        img_array = (img_array - mean) / std
        
        # Step 6: Convert to PyTorch tensor with explicit float32
        # Change from (H, W, C) to (C, H, W) - PyTorch format
        tensor = torch.from_numpy(img_array.astype(np.float32)).permute(2, 0, 1)
        
        # Step 7: Add batch dimension
        # (C, H, W) → (1, C, H, W)
        tensor = tensor.unsqueeze(0)
        
        # Step 8: Move to device (CPU/GPU) and ensure float32
        tensor = tensor.to(self.device, dtype=torch.float32)
        
        return tensor
    
    def detect(self, image_bytes: bytes) -> Dict:
        """
        Detect image manipulation using TruFor
        
        COMPLETE WORKFLOW:
        1. Load model (if not already loaded)
        2. Preprocess image
        3. Run through neural network
        4. Get manipulation mask + confidence score
        5. Calculate overall manipulation probability
        6. Return results
        
        Args:
            image_bytes: Raw image data
            
        Returns:
            dict with:
                - is_manipulated: bool (True if score > 0.5)
                - confidence: float (0-1, overall manipulation probability)
                - manipulation_score: float (same as confidence)
                - method: str ('trufor')
                - details: str (human-readable)
                - heatmap_available: bool (True if we have pixel-level data)
        
        WHAT THE MODEL DOES:
        - Analyzes every pixel
        - Looks for inconsistencies in:
            * Noise patterns (camera sensor noise)
            * JPEG compression (edited areas compress differently)
            * Edge patterns (fake text has different edges)
            * Color distribution (AI-generated has specific patterns)
        - Outputs probability per pixel + overall score
        """
        try:
            # Step 1: Load model if needed
            self._load_model()
            
            # Step 2: Preprocess image
            img_tensor = self._preprocess_image(image_bytes)
            
            # Step 3: Run inference
            # torch.no_grad() = don't compute gradients (we're not training)
            # This saves memory and speeds up inference
            with torch.no_grad():
                # Forward pass through model
                # Returns:
                #   - manipulation_mask: (1, 1, 384, 384) - probability per pixel
                #   - confidence_score: (1,) - overall probability
                manipulation_mask, confidence_score = self.model(img_tensor)
            
            # Step 4: Extract values
            # Convert from PyTorch tensor to Python float
            manipulation_score = confidence_score.item()  # Single number 0-1
            
            # Step 5: Determine verdict
            is_manipulated = manipulation_score > 0.5
            
            # Step 6: Log results
            logger.info(f"TruFor analysis complete: score={manipulation_score:.3f}, "
                       f"verdict={'MANIPULATED' if is_manipulated else 'AUTHENTIC'}")
            
            # Step 7: Return results
            return {
                'is_manipulated': is_manipulated,
                'confidence': manipulation_score,
                'manipulation_score': manipulation_score,
                'method': 'trufor',
                'details': f"TruFor deep learning analysis (confidence: {manipulation_score:.2%})",
                'heatmap_available': True,  # We have pixel-level data
            }
            
        except Exception as e:
            logger.error(f"TruFor detection failed: {e}", exc_info=True)
            
            # Do NOT report a score on failure: the caller must treat this as
            # "inconclusive" rather than as a clean pass.
            return {
                'method': 'trufor',
                'error': str(e),
                'heatmap_available': False
            }
    
    def get_heatmap(self, image_bytes: bytes) -> Optional[np.ndarray]:
        """
        Generate manipulation heatmap
        
        WHAT THIS DOES:
        - Shows WHERE in the image manipulation was detected
        - Returns a 2D array where each pixel has manipulation probability
        - Can be visualized as red (manipulated) to blue (original)
        
        Args:
            image_bytes: Raw image bytes
            
        Returns:
            numpy array (384, 384) with values 0-1
            0 = authentic pixel
            1 = manipulated pixel
        
        USAGE:
        heatmap = detector.get_heatmap(image_bytes)
        # Visualize:
        import matplotlib.pyplot as plt
        plt.imshow(heatmap, cmap='hot')
        plt.colorbar()
        plt.show()
        """
        try:
            self._load_model()
            img_tensor = self._preprocess_image(image_bytes)
            
            with torch.no_grad():
                manipulation_mask, _ = self.model(img_tensor)
            
            # Convert tensor to numpy
            # (1, 1, 384, 384) → (384, 384)
            heatmap = manipulation_mask.squeeze().cpu().numpy()
            
            return heatmap
            
        except Exception as e:
            logger.error(f"Failed to generate heatmap: {e}")
            return None
    
    def analyze_regions(self, image_bytes: bytes) -> Dict:
        """
        Detailed region-based analysis
        
        WHAT THIS DOES:
        - Divides image into regions (e.g., 4x4 grid = 16 regions)
        - Calculates manipulation probability per region
        - Useful for identifying WHICH PARTS were edited
        
        Returns:
            dict with:
                - overall_score: float
                - region_scores: list of floats (one per region)
                - suspicious_regions: list of (x, y) coordinates
        
        EXAMPLE OUTPUT:
        {
            'overall_score': 0.73,
            'region_scores': [[0.1, 0.2], [0.9, 0.85]],  # Top-left low, bottom-right high
            'suspicious_regions': [(1, 0), (1, 1)]  # Bottom-right regions
        }
        
        USE CASE:
        "The name and date were changed, but the logo is original"
        Region analysis can show exactly where edits were made
        """
        try:
            heatmap = self.get_heatmap(image_bytes)
            
            if heatmap is None:
                return {'error': 'Could not generate heatmap'}
            
            # Divide into 4x4 grid
            h, w = heatmap.shape
            grid_size = 4
            cell_h, cell_w = h // grid_size, w // grid_size
            
            region_scores = []
            suspicious_regions = []
            
            for i in range(grid_size):
                row_scores = []
                for j in range(grid_size):
                    # Extract region
                    region = heatmap[
                        i*cell_h:(i+1)*cell_h,
                        j*cell_w:(j+1)*cell_w
                    ]
                    
                    # Calculate average score for this region
                    region_score = region.mean()
                    row_scores.append(float(region_score))
                    
                    # Mark as suspicious if score > 0.6
                    if region_score > 0.6:
                        suspicious_regions.append((i, j))
                
                region_scores.append(row_scores)
            
            overall_score = heatmap.mean()
            
            return {
                'overall_score': float(overall_score),
                'region_scores': region_scores,
                'suspicious_regions': suspicious_regions,
                'grid_size': grid_size
            }
            
        except Exception as e:
            logger.error(f"Region analysis failed: {e}")
            return {'error': str(e)}