"""
BrainLM - Brain Language Model for Connectivity Matrix Analysis

A Transformer-based model for learning latent representations
from brain connectivity matrices using masked autoencoding.
"""

from .model import BrainLM, BrainLMConfig
from .dataset import BrainLMDataset, create_dataloaders
from .train import BrainLMTrainer

__all__ = [
    'BrainLM',
    'BrainLMConfig',
    'BrainLMDataset',
    'create_dataloaders',
    'BrainLMTrainer',
]
