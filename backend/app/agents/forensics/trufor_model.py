"""
trufor_model.py
Complete TruFor model architecture for manipulation detection

Based on: https://github.com/grip-unina/TruFor
Paper: "TruFor: Leveraging all-round clues for trustworthy image forgery detection and localization"
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import timm
from typing import Tuple

class TruForModel(nn.Module):
    """
    TruFor: Trust in Forensics
    
    Architecture:
    1. Feature Extractor (Transformer backbone - Swin Transformer)
    2. Noiseprint++ extraction (detects camera noise patterns)
    3. Anomaly detection head (finds manipulated regions)
    4. Localization head (generates manipulation mask)
    
    Input: RGB image (B, 3, H, W)
    Output: 
        - manipulation_mask: (B, 1, H, W) - probability map of manipulation
        - confidence_score: (B,) - overall manipulation probability
    """
    
    def __init__(
        self, 
        backbone: str = 'swin_base_patch4_window12_384',
        pretrained: bool = True
    ):
        """
        Initialize TruFor model
        
        Args:
            backbone: Transformer backbone architecture
            pretrained: Use ImageNet pretrained weights for backbone
        
        How it works:
        1. Backbone extracts visual features (edges, textures, patterns)
        2. Noiseprint extracts camera sensor noise patterns
        3. Both are combined to detect inconsistencies
        4. Decoder generates pixel-level manipulation probability
        """
        super().__init__()
        
        # === BACKBONE: Feature Extractor ===
        # This extracts visual features from the image
        # Uses Swin Transformer (better than ResNet for this task)
        self.backbone = timm.create_model(
            backbone,
            pretrained=pretrained,
            features_only=True,  # We want intermediate features, not just final output
            out_indices=(1, 2, 3),  # Get features at different scales
        )
        
        # Get feature dimensions from backbone
        # These are the number of channels at each scale
        feature_info = self.backbone.feature_info
        self.feature_dims = [info['num_chs'] for info in feature_info]
        
        # === NOISEPRINT++ MODULE ===
        # Extracts camera sensor noise patterns
        # Manipulated regions have different noise than original camera noise
        self.noiseprint = NoiseprintExtractor()
        
        # === FUSION MODULE ===
        # Combines visual features + noise features
        self.fusion = FeatureFusion(self.feature_dims)
        
        # === DECODER ===
        # Converts fused features into manipulation probability map
        self.decoder = ManipulationDecoder(self.feature_dims)
        
        # === CLASSIFICATION HEAD ===
        # Overall image-level decision: manipulated or not
        self.classifier = nn.Sequential(
            nn.AdaptiveAvgPool2d(1),  # Global average pooling
            nn.Flatten(),
            nn.Linear(self.feature_dims[-1], 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 1),  # Single output: manipulation probability
            nn.Sigmoid()
        )
    
    def forward(self, x: torch.Tensor) -> Tuple[torch.Tensor, torch.Tensor]:
        """
        Forward pass
        
        Args:
            x: Input image (B, 3, H, W)
            
        Returns:
            manipulation_mask: (B, 1, H, W) - pixel-level probabilities
            confidence_score: (B,) - image-level probability
        
        Step-by-step:
        1. Extract visual features at multiple scales
        2. Extract noise features
        3. Fuse visual + noise features
        4. Decode to get pixel-level mask
        5. Pool to get image-level score
        """
        B, C, H, W = x.shape
        
        # Step 1: Extract multi-scale visual features
        # backbone returns features at 3 different resolutions
        # Small features = fine details (edges, text)
        # Large features = overall structure
        visual_features = self.backbone(x)  # List of 3 tensors
        
        # Step 2: Extract noise features
        # This detects camera sensor patterns
        # Manipulated areas have inconsistent noise
        noise_features = self.noiseprint(x)
        
        # Step 3: Fuse visual and noise features
        # Combines what the image LOOKS like with its NOISE pattern
        fused_features = self.fusion(visual_features, noise_features)
        
        # Step 4: Decode to manipulation mask
        # Upsamples features back to input resolution
        # Each pixel gets a probability: 0 (real) to 1 (fake)
        manipulation_mask = self.decoder(fused_features)
        
        # Step 5: Get overall confidence score
        # Average all pixel probabilities
        confidence_score = self.classifier(fused_features[-1])
        
        return manipulation_mask, confidence_score


class NoiseprintExtractor(nn.Module):
    """
    Noiseprint++ Module
    
    What it does:
    - Extracts camera sensor noise pattern
    - Real photos have consistent noise from the camera sensor
    - Edited areas have different noise (from Photoshop, etc.)
    
    How it works:
    - Uses high-pass filters to isolate noise
    - Learns what "normal" camera noise looks like
    - Flags areas with abnormal noise
    """
    
    def __init__(self):
        super().__init__()
        
        # High-pass filter to extract noise
        # Removes low-frequency content (main image)
        # Keeps high-frequency content (noise, edges)
        self.noise_extractor = nn.Sequential(
            nn.Conv2d(3, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 64, kernel_size=3, padding=1),
            nn.BatchNorm2d(64),
            nn.ReLU(),
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Extract noise features
        
        Args:
            x: RGB image (B, 3, H, W)
            
        Returns:
            noise_features: (B, 32, H, W)
        """
        # Apply high-pass filtering
        noise = self.noise_extractor(x)
        return noise


class FeatureFusion(nn.Module):
    """
    Feature Fusion Module
    
    What it does:
    - Combines visual features + noise features
    - Creates a unified representation
    
    Why it's needed:
    - Visual features show WHAT is in the image
    - Noise features show HOW the image was created
    - Together, they can detect manipulation
    """
    
    def __init__(self, feature_dims):
        super().__init__()
        
        # Fusion layers for each scale
        self.fusion_layers = nn.ModuleList([
            nn.Sequential(
                nn.Conv2d(dim + 32, dim, kernel_size=1),  # +32 from noise features
                nn.BatchNorm2d(dim),
                nn.ReLU()
            )
            for dim in feature_dims
        ])
    
    def forward(self, visual_features, noise_features):
        """
        Fuse visual and noise features
        
        Args:
            visual_features: List of 3 feature tensors at different scales
            noise_features: Noise tensor (B, 32, H, W)
            
        Returns:
            fused_features: List of 3 fused tensors
        """
        fused = []
        
        for i, visual_feat in enumerate(visual_features):
            # Resize noise to match visual feature size
            _, _, H, W = visual_feat.shape
            noise_resized = F.interpolate(
                noise_features, 
                size=(H, W), 
                mode='bilinear', 
                align_corners=False
            )
            
            # Concatenate and fuse
            concat = torch.cat([visual_feat, noise_resized], dim=1)
            fused_feat = self.fusion_layers[i](concat)
            fused.append(fused_feat)
        
        return fused


class ManipulationDecoder(nn.Module):
    """
    Manipulation Decoder
    
    What it does:
    - Takes fused features
    - Generates pixel-level manipulation probability map
    
    How it works:
    - Progressive upsampling (small → large)
    - Each layer refines the prediction
    - Final output: same size as input image
    """
    
    def __init__(self, feature_dims):
        super().__init__()
        
        # Decoder blocks - upsample from small to large
        self.decoder_blocks = nn.ModuleList([
            DecoderBlock(feature_dims[2], feature_dims[1]),  # Largest → Medium
            DecoderBlock(feature_dims[1], feature_dims[0]),  # Medium → Small
            DecoderBlock(feature_dims[0], 64),  # Small → Fine
        ])
        
        # Final convolution to get manipulation mask
        self.final_conv = nn.Sequential(
            nn.Conv2d(64, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.Conv2d(32, 1, kernel_size=1),  # 1 channel output
            nn.Sigmoid()  # Probability (0-1)
        )
    
    def forward(self, features):
        """
        Decode features to manipulation mask
        
        Args:
            features: List of 3 fused feature tensors
            
        Returns:
            mask: (B, 1, H, W) - manipulation probability per pixel
        """
        # Start from coarsest features
        x = features[-1]
        
        # Progressively upsample and refine
        for i, decoder_block in enumerate(self.decoder_blocks):
            # Skip connection from encoder (if not last)
            skip = features[-(i+2)] if i < len(features) - 1 else None
            x = decoder_block(x, skip)
        
        # Final upsampling to input resolution
        x = F.interpolate(x, scale_factor=4, mode='bilinear', align_corners=False)
        
        # Generate final mask
        mask = self.final_conv(x)
        
        return mask


class DecoderBlock(nn.Module):
    """
    Decoder Block for upsampling
    
    What it does:
    - Upsamples features 2x
    - Optionally adds skip connection
    - Refines the features
    """
    
    def __init__(self, in_channels, out_channels):
        super().__init__()
        
        self.upsample = nn.ConvTranspose2d(
            in_channels, 
            out_channels, 
            kernel_size=2, 
            stride=2
        )
        
        self.conv = nn.Sequential(
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU(),
            nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm2d(out_channels),
            nn.ReLU()
        )
    
    def forward(self, x, skip=None):
        """
        Args:
            x: Input features
            skip: Skip connection from encoder (optional)
        """
        # Upsample
        x = self.upsample(x)
        
        # Add skip connection if available
        if skip is not None:
            # Resize if dimensions don't match
            if x.shape[2:] != skip.shape[2:]:
                skip = F.interpolate(skip, size=x.shape[2:], mode='bilinear', align_corners=False)
            x = x + skip
        
        # Refine features
        x = self.conv(x)
        
        return x


def load_trufor_model(checkpoint_path: str, device: str = 'cpu') -> TruForModel:
    """
    Load pre-trained TruFor model
    
    Args:
        checkpoint_path: Path to model weights
        device: 'cpu' or 'cuda'
        
    Returns:
        Loaded model ready for inference
    
    What happens:
    1. Create model architecture
    2. Load pre-trained weights
    3. Set to evaluation mode
    4. Move to device (CPU/GPU)
    """
    # Create model
    model = TruForModel()
    
    # Load weights (weights_only=True: never unpickle arbitrary objects)
    checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=True)
    
    # Handle different checkpoint formats
    if 'model' in checkpoint:
        state_dict = checkpoint['model']
    elif 'state_dict' in checkpoint:
        state_dict = checkpoint['state_dict']
    else:
        state_dict = checkpoint
    
    # Strict loading: a checkpoint that does not match this architecture must
    # fail loudly instead of leaving randomly-initialised layers in place.
    model.load_state_dict(state_dict, strict=True)
    
    # Set to eval mode (disable dropout, batch norm in train mode)
    model.eval()
    
    # Move to device
    model.to(device)
    
    return model
