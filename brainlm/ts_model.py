"""
Time-series BrainLM (masked autoencoder over time steps).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, Optional

import torch
import torch.nn as nn
import torch.nn.functional as F


@dataclass
class BrainLMTimeSeriesConfig:
    n_features: int
    d_model: int = 256
    nhead: int = 8
    num_encoder_layers: int = 4
    num_decoder_layers: int = 2
    dim_feedforward: int = 1024
    dropout: float = 0.1
    max_time_steps: int = 2048
    mask_ratio: float = 0.15


class PositionalEncoding(nn.Module):
    def __init__(self, d_model: int, max_len: int, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-math.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))  # (1, max_len, d_model)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.pe[:, : x.size(1)]
        return self.dropout(x)


class BrainLMTimeSeries(nn.Module):
    """
    Masked autoencoder on time series:
      input: (B, T, F)
      mask_labels: (B, T) where 1 indicates masked steps
      attention_mask: (B, T) where 1 indicates valid (non-padding) steps
    """

    def __init__(self, config: BrainLMTimeSeriesConfig):
        super().__init__()
        self.config = config

        self.input_proj = nn.Linear(config.n_features, config.d_model)
        self.output_proj = nn.Linear(config.d_model, config.n_features)

        self.cls_token = nn.Parameter(torch.randn(1, 1, config.d_model) * 0.02)
        self.mask_token = nn.Parameter(torch.randn(1, 1, config.d_model) * 0.02)

        self.pos = PositionalEncoding(config.d_model, max_len=config.max_time_steps + 1, dropout=config.dropout)

        enc_layer = nn.TransformerEncoderLayer(
            d_model=config.d_model,
            nhead=config.nhead,
            dim_feedforward=config.dim_feedforward,
            dropout=config.dropout,
            batch_first=True,
            norm_first=True,
        )
        self.encoder = nn.TransformerEncoder(enc_layer, num_layers=config.num_encoder_layers)

        dec_layer = nn.TransformerDecoderLayer(
            d_model=config.d_model,
            nhead=config.nhead,
            dim_feedforward=config.dim_feedforward,
            dropout=config.dropout,
            batch_first=True,
            norm_first=True,
        )
        self.decoder = nn.TransformerDecoder(dec_layer, num_layers=config.num_decoder_layers)

        self.ln = nn.LayerNorm(config.d_model)
        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(
        self,
        input_x: torch.Tensor,  # (B, T, F)
        attention_mask: Optional[torch.Tensor] = None,  # (B, T)
        mask_labels: Optional[torch.Tensor] = None,  # (B, T)
        return_latent: bool = False,
    ) -> Dict[str, torch.Tensor]:
        B, T, F = input_x.shape
        x = self.input_proj(input_x)  # (B, T, D)

        if mask_labels is not None:
            m = mask_labels.unsqueeze(-1).expand_as(x)  # (B, T, D)
            x = torch.where(m > 0.5, self.mask_token.expand_as(x), x)

        cls = self.cls_token.expand(B, 1, -1)
        x = torch.cat([cls, x], dim=1)  # (B, T+1, D)
        x = self.pos(x)

        if attention_mask is not None:
            cls_mask = torch.ones(B, 1, device=attention_mask.device, dtype=attention_mask.dtype)
            full = torch.cat([cls_mask, attention_mask], dim=1)  # (B, T+1)
            key_padding = (full < 0.5)  # True => pad
        else:
            key_padding = None

        enc = self.encoder(x, src_key_padding_mask=key_padding)  # (B, T+1, D)
        cls_latent = enc[:, 0]  # (B, D)

        dec = self.decoder(
            enc,
            enc,
            tgt_key_padding_mask=key_padding,
            memory_key_padding_mask=key_padding,
        )
        dec = self.ln(dec)
        recon = self.output_proj(dec[:, 1:])  # (B, T, F)

        out: Dict[str, torch.Tensor] = {
            "reconstruction": recon,
            "cls_representation": cls_latent,
        }
        if return_latent:
            out["latent_tokens"] = enc[:, 1:]
        return out

    def compute_loss(
        self,
        input_x: torch.Tensor,
        labels: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        mask_labels: Optional[torch.Tensor] = None,
    ) -> Dict[str, torch.Tensor]:
        out = self.forward(input_x, attention_mask=attention_mask, mask_labels=mask_labels)
        recon = out["reconstruction"]

        if attention_mask is None:
            attn = torch.ones(recon.shape[:2], device=recon.device, dtype=recon.dtype)
        else:
            attn = attention_mask

        if mask_labels is not None:
            m = (mask_labels > 0.5).to(recon.dtype)
            w = (m * attn).unsqueeze(-1)  # (B, T, 1)
        else:
            w = attn.unsqueeze(-1)

        denom = w.sum().clamp_min(1.0)
        loss = F.mse_loss(recon * w, labels * w, reduction="sum") / denom
        return {"loss": loss, "reconstruction": recon, "cls_representation": out["cls_representation"]}

