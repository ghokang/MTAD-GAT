"""
BrainLM Model - Transformer-based Masked Autoencoder for Brain Connectivity

Architecture inspired by BrainLM paper, adapted for 100-feature brain signals.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import math
from dataclasses import dataclass
from typing import Optional, Tuple, Dict


@dataclass
class BrainLMConfig:
    """Configuration for BrainLM model"""
    n_features: int = 100
    d_model: int = 256
    nhead: int = 8
    num_encoder_layers: int = 6
    num_decoder_layers: int = 2
    dim_feedforward: int = 1024
    dropout: float = 0.1
    max_seq_len: int = 512
    use_upper_triangle: bool = True
    mask_ratio: float = 0.15
    
    @property
    def input_dim(self) -> int:
        if self.use_upper_triangle:
            return self.n_features * (self.n_features - 1) // 2
        return self.n_features * self.n_features


class PositionalEncoding(nn.Module):
    """Sinusoidal positional encoding"""
    
    def __init__(self, d_model: int, max_len: int = 512, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0)
        
        self.register_buffer('pe', pe)
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, :x.size(1)]
        return self.dropout(x)


class BrainLM(nn.Module):
    """
    BrainLM: Transformer-based Masked Autoencoder for Brain Connectivity
    
    Architecture:
    - Input projection: Maps CM features to d_model
    - CLS token: Learnable token for sequence-level representation
    - Positional encoding: Sinusoidal position embeddings
    - Transformer Encoder: Self-attention layers
    - Transformer Decoder: For reconstruction (lighter than encoder)
    - Output projection: Reconstructs original CM features
    """
    
    def __init__(self, config: BrainLMConfig):
        super().__init__()
        self.config = config
        
        self.input_projection = nn.Linear(config.input_dim, config.d_model)
        
        self.cls_token = nn.Parameter(torch.randn(1, 1, config.d_model) * 0.02)
        
        self.mask_token = nn.Parameter(torch.randn(1, 1, config.d_model) * 0.02)
        
        self.pos_encoder = PositionalEncoding(
            config.d_model, 
            config.max_seq_len + 1,
            config.dropout
        )
        
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.nhead,
            dim_feedforward=config.dim_feedforward,
            dropout=config.dropout,
            batch_first=True,
            norm_first=True
        )
        self.encoder = nn.TransformerEncoder(
            encoder_layer,
            num_layers=config.num_encoder_layers
        )
        
        decoder_layer = nn.TransformerDecoderLayer(
            d_model=config.d_model,
            nhead=config.nhead,
            dim_feedforward=config.dim_feedforward,
            dropout=config.dropout,
            batch_first=True,
            norm_first=True
        )
        self.decoder = nn.TransformerDecoder(
            decoder_layer,
            num_layers=config.num_decoder_layers
        )
        
        self.output_projection = nn.Linear(config.d_model, config.input_dim)
        
        self.layer_norm = nn.LayerNorm(config.d_model)
        
        self._init_weights()
    
    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)
    
    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        mask_labels: Optional[torch.Tensor] = None,
        return_latent: bool = False
    ) -> Dict[str, torch.Tensor]:
        """
        Forward pass.
        
        Args:
            input_ids: Input tensor of shape (batch, seq_len, input_dim)
            attention_mask: Mask of shape (batch, seq_len), 1 for valid, 0 for padding
            mask_labels: Binary mask indicating which positions are masked (batch, seq_len)
            return_latent: Whether to return latent representations
            
        Returns:
            Dictionary with 'reconstruction', 'cls_representation', and optionally 'latent'
        """
        batch_size, seq_len, _ = input_ids.shape
        
        x = self.input_projection(input_ids)
        
        if mask_labels is not None:
            mask_labels_expanded = mask_labels.unsqueeze(-1).expand_as(x)
            x = torch.where(mask_labels_expanded == 1, self.mask_token.expand_as(x), x)
        
        cls_tokens = self.cls_token.expand(batch_size, -1, -1)
        x = torch.cat([cls_tokens, x], dim=1)
        
        x = self.pos_encoder(x)
        
        if attention_mask is not None:
            cls_mask = torch.ones(batch_size, 1, device=attention_mask.device)
            full_mask = torch.cat([cls_mask, attention_mask], dim=1)
            src_key_padding_mask = (full_mask == 0)
        else:
            src_key_padding_mask = None
        
        encoded = self.encoder(x, src_key_padding_mask=src_key_padding_mask)
        
        cls_representation = encoded[:, 0]
        
        decoded = self.decoder(
            encoded,
            encoded,
            tgt_key_padding_mask=src_key_padding_mask,
            memory_key_padding_mask=src_key_padding_mask
        )
        
        decoded = self.layer_norm(decoded)
        
        reconstruction = self.output_projection(decoded[:, 1:])
        
        output = {
            'reconstruction': reconstruction,
            'cls_representation': cls_representation,
        }
        
        if return_latent:
            output['latent'] = encoded[:, 1:]
        
        return output
    
    def get_cls_representation(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None
    ) -> torch.Tensor:
        """
        Get CLS token representation (latent) for input sequence.
        
        Args:
            input_ids: Input tensor
            attention_mask: Attention mask
            
        Returns:
            CLS representation of shape (batch, d_model)
        """
        output = self.forward(input_ids, attention_mask, return_latent=False)
        return output['cls_representation']
    
    def compute_loss(
        self,
        input_ids: torch.Tensor,
        labels: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        mask_labels: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Compute reconstruction loss.
        
        Args:
            input_ids: Masked input tensor
            labels: Original (unmasked) tensor
            attention_mask: Attention mask
            mask_labels: Binary mask for masked positions
            
        Returns:
            Dictionary with 'loss' and 'reconstruction_loss'
        """
        output = self.forward(input_ids, attention_mask, mask_labels)
        reconstruction = output['reconstruction']
        
        if mask_labels is not None:
            mask = mask_labels.unsqueeze(-1).expand_as(reconstruction)
            masked_recon = reconstruction * mask
            masked_labels = labels * mask
            
            n_masked = mask.sum() + 1e-8
            loss = F.mse_loss(masked_recon, masked_labels, reduction='sum') / n_masked
        else:
            if attention_mask is not None:
                mask = attention_mask.unsqueeze(-1).expand_as(reconstruction)
                masked_recon = reconstruction * mask
                masked_labels = labels * mask
                n_valid = mask.sum() + 1e-8
                loss = F.mse_loss(masked_recon, masked_labels, reduction='sum') / n_valid
            else:
                loss = F.mse_loss(reconstruction, labels)
        
        return {
            'loss': loss,
            'reconstruction_loss': loss,
            'reconstruction': reconstruction
        }


class BrainLMForClassification(nn.Module):
    """BrainLM with classification head for downstream tasks"""
    
    def __init__(self, config: BrainLMConfig, num_classes: int):
        super().__init__()
        self.brainlm = BrainLM(config)
        self.classifier = nn.Sequential(
            nn.Linear(config.d_model, config.d_model // 2),
            nn.ReLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.d_model // 2, num_classes)
        )
    
    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None
    ) -> Dict[str, torch.Tensor]:
        cls_rep = self.brainlm.get_cls_representation(input_ids, attention_mask)
        logits = self.classifier(cls_rep)
        
        output = {'logits': logits, 'cls_representation': cls_rep}
        
        if labels is not None:
            loss = F.cross_entropy(logits, labels)
            output['loss'] = loss
        
        return output


if __name__ == "__main__":
    config = BrainLMConfig(
        n_features=100,
        d_model=256,
        nhead=8,
        num_encoder_layers=4,
        num_decoder_layers=2,
        max_seq_len=64
    )
    
    model = BrainLM(config)
    print(f"Model parameters: {sum(p.numel() for p in model.parameters()):,}")
    
    batch_size = 4
    seq_len = 32
    input_dim = config.input_dim
    
    x = torch.randn(batch_size, seq_len, input_dim)
    attention_mask = torch.ones(batch_size, seq_len)
    mask_labels = torch.zeros(batch_size, seq_len)
    mask_labels[:, 5:10] = 1
    
    output = model(x, attention_mask, mask_labels, return_latent=True)
    print(f"\nReconstruction shape: {output['reconstruction'].shape}")
    print(f"CLS representation shape: {output['cls_representation'].shape}")
    print(f"Latent shape: {output['latent'].shape}")
    
    loss_output = model.compute_loss(x, x, attention_mask, mask_labels)
    print(f"\nLoss: {loss_output['loss'].item():.4f}")
