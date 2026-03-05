"""
BrainLM Training Module

Training and evaluation utilities for BrainLM model.
"""

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR, OneCycleLR
from typing import Dict, List, Optional, Tuple
from pathlib import Path
from tqdm import tqdm
import json
from datetime import datetime

from .model import BrainLM, BrainLMConfig


class BrainLMTrainer:
    """
    Trainer for BrainLM model.
    
    Handles training loop, validation, checkpointing, and logging.
    """
    
    def __init__(
        self,
        model: BrainLM,
        train_loader: DataLoader,
        val_loader: Optional[DataLoader] = None,
        lr: float = 1e-4,
        weight_decay: float = 0.01,
        warmup_steps: int = 100,
        max_epochs: int = 100,
        patience: int = 10,
        checkpoint_dir: Optional[Path] = None,
        device: Optional[torch.device] = None
    ):
        """
        Initialize trainer.
        
        Args:
            model: BrainLM model
            train_loader: Training data loader
            val_loader: Validation data loader
            lr: Learning rate
            weight_decay: Weight decay for AdamW
            warmup_steps: Number of warmup steps
            max_epochs: Maximum number of epochs
            patience: Early stopping patience
            checkpoint_dir: Directory for saving checkpoints
            device: Device to use for training
        """
        self.model = model
        self.train_loader = train_loader
        self.val_loader = val_loader
        self.lr = lr
        self.weight_decay = weight_decay
        self.warmup_steps = warmup_steps
        self.max_epochs = max_epochs
        self.patience = patience
        
        if device is None:
            if torch.cuda.is_available():
                self.device = torch.device('cuda')
            elif torch.backends.mps.is_available():
                self.device = torch.device('mps')
            else:
                self.device = torch.device('cpu')
        else:
            self.device = device
        
        self.model = self.model.to(self.device)
        
        self.optimizer = AdamW(
            model.parameters(),
            lr=lr,
            weight_decay=weight_decay
        )
        
        total_steps = max_epochs * len(train_loader)
        self.scheduler = OneCycleLR(
            self.optimizer,
            max_lr=lr,
            total_steps=total_steps,
            pct_start=0.1
        )
        
        self.checkpoint_dir = checkpoint_dir
        if checkpoint_dir:
            checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        self.history = {
            'train_loss': [],
            'val_loss': [],
            'lr': []
        }
        
        self.best_val_loss = float('inf')
        self.patience_counter = 0
        self.current_epoch = 0
    
    def train_epoch(self) -> float:
        """
        Train for one epoch.
        
        Returns:
            Average training loss
        """
        self.model.train()
        total_loss = 0.0
        n_batches = 0
        
        pbar = tqdm(self.train_loader, desc=f'Epoch {self.current_epoch + 1}')
        
        for batch in pbar:
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)
            mask_labels = batch['mask_labels'].to(self.device)
            
            self.optimizer.zero_grad()
            
            loss_output = self.model.compute_loss(
                input_ids, labels, attention_mask, mask_labels
            )
            loss = loss_output['loss']
            
            loss.backward()
            torch.nn.utils.clip_grad_norm_(self.model.parameters(), max_norm=1.0)
            self.optimizer.step()
            self.scheduler.step()
            
            total_loss += loss.item()
            n_batches += 1
            
            pbar.set_postfix({'loss': f'{loss.item():.4f}'})
        
        return total_loss / n_batches
    
    @torch.no_grad()
    def validate(self) -> float:
        """
        Validate model.
        
        Returns:
            Average validation loss
        """
        if self.val_loader is None:
            return 0.0
        
        self.model.eval()
        total_loss = 0.0
        n_batches = 0
        
        for batch in self.val_loader:
            input_ids = batch['input_ids'].to(self.device)
            attention_mask = batch['attention_mask'].to(self.device)
            labels = batch['labels'].to(self.device)
            mask_labels = batch['mask_labels'].to(self.device)
            
            loss_output = self.model.compute_loss(
                input_ids, labels, attention_mask, mask_labels
            )
            
            total_loss += loss_output['loss'].item()
            n_batches += 1
        
        return total_loss / n_batches if n_batches > 0 else 0.0
    
    def train(self) -> Dict[str, List[float]]:
        """
        Full training loop.
        
        Returns:
            Training history dictionary
        """
        print(f"Training on {self.device}")
        print(f"Total epochs: {self.max_epochs}")
        print(f"Training samples: {len(self.train_loader.dataset)}")
        if self.val_loader:
            print(f"Validation samples: {len(self.val_loader.dataset)}")
        
        for epoch in range(self.max_epochs):
            self.current_epoch = epoch
            
            train_loss = self.train_epoch()
            val_loss = self.validate() if self.val_loader else train_loss
            
            current_lr = self.scheduler.get_last_lr()[0]
            
            self.history['train_loss'].append(train_loss)
            self.history['val_loss'].append(val_loss)
            self.history['lr'].append(current_lr)
            
            print(f'Epoch {epoch + 1}/{self.max_epochs} - '
                  f'Train Loss: {train_loss:.4f} - '
                  f'Val Loss: {val_loss:.4f} - '
                  f'LR: {current_lr:.6f}')
            
            if val_loss < self.best_val_loss:
                self.best_val_loss = val_loss
                self.patience_counter = 0
                
                if self.checkpoint_dir:
                    self.save_checkpoint('best_model.pt')
            else:
                self.patience_counter += 1
            
            if self.patience_counter >= self.patience:
                print(f'Early stopping at epoch {epoch + 1}')
                break
            
            if self.checkpoint_dir and (epoch + 1) % 10 == 0:
                self.save_checkpoint(f'checkpoint_epoch_{epoch + 1}.pt')
        
        if self.checkpoint_dir:
            self.save_checkpoint('final_model.pt')
            self.save_history()
        
        return self.history
    
    def save_checkpoint(self, filename: str):
        """Save model checkpoint"""
        if self.checkpoint_dir is None:
            return
        
        checkpoint = {
            'epoch': self.current_epoch,
            'model_state_dict': self.model.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'scheduler_state_dict': self.scheduler.state_dict(),
            'best_val_loss': self.best_val_loss,
            'history': self.history,
            'config': self.model.config.__dict__
        }
        
        torch.save(checkpoint, self.checkpoint_dir / filename)
    
    def load_checkpoint(self, filepath: Path):
        """Load model checkpoint"""
        checkpoint = torch.load(filepath, map_location=self.device)
        
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.scheduler.load_state_dict(checkpoint['scheduler_state_dict'])
        self.best_val_loss = checkpoint['best_val_loss']
        self.history = checkpoint['history']
        self.current_epoch = checkpoint['epoch']
    
    def save_history(self):
        """Save training history to JSON"""
        if self.checkpoint_dir is None:
            return
        
        history_path = self.checkpoint_dir / 'training_history.json'
        with open(history_path, 'w') as f:
            json.dump(self.history, f, indent=2)


@torch.no_grad()
def extract_latents(
    model: BrainLM,
    dataloader: DataLoader,
    device: torch.device
) -> Tuple[np.ndarray, np.ndarray]:
    """
    Extract latent representations for all samples.
    
    Args:
        model: Trained BrainLM model
        dataloader: DataLoader with samples
        device: Device to use
        
    Returns:
        Tuple of (latents, cluster_ids)
    """
    model.eval()
    model = model.to(device)
    
    all_latents = []
    all_cluster_ids = []
    
    for batch in tqdm(dataloader, desc='Extracting latents'):
        input_ids = batch['input_ids'].to(device)
        attention_mask = batch['attention_mask'].to(device)
        
        cls_rep = model.get_cls_representation(input_ids, attention_mask)
        
        all_latents.append(cls_rep.cpu().numpy())
        
        if 'cluster_id' in batch:
            all_cluster_ids.append(batch['cluster_id'].numpy())
        elif 'cluster_ids' in batch:
            all_cluster_ids.append(batch['cluster_ids'][:, 0].numpy())
    
    latents = np.concatenate(all_latents, axis=0)
    
    if all_cluster_ids:
        cluster_ids = np.concatenate(all_cluster_ids, axis=0)
    else:
        cluster_ids = np.full(len(latents), -1)
    
    return latents, cluster_ids


def train_brainlm(
    train_loader: DataLoader,
    val_loader: Optional[DataLoader] = None,
    config: Optional[BrainLMConfig] = None,
    max_epochs: int = 100,
    lr: float = 1e-4,
    patience: int = 10,
    checkpoint_dir: Optional[Path] = None,
    device: Optional[torch.device] = None
) -> Tuple[BrainLM, Dict[str, List[float]]]:
    """
    Train BrainLM model.
    
    Args:
        train_loader: Training data loader
        val_loader: Validation data loader
        config: Model configuration
        max_epochs: Maximum epochs
        lr: Learning rate
        patience: Early stopping patience
        checkpoint_dir: Checkpoint directory
        device: Device to use
        
    Returns:
        Tuple of (trained_model, history)
    """
    if config is None:
        config = BrainLMConfig()
    
    model = BrainLM(config)
    
    trainer = BrainLMTrainer(
        model=model,
        train_loader=train_loader,
        val_loader=val_loader,
        lr=lr,
        max_epochs=max_epochs,
        patience=patience,
        checkpoint_dir=checkpoint_dir,
        device=device
    )
    
    history = trainer.train()
    
    if checkpoint_dir and (checkpoint_dir / 'best_model.pt').exists():
        trainer.load_checkpoint(checkpoint_dir / 'best_model.pt')
    
    return model, history


if __name__ == "__main__":
    import sys
    sys.path.append(str(Path(__file__).parent.parent))
    
    from brainlm.dataset import BrainLMDataset, create_dataloaders
    from pipeline.connectivity import ConnectivityMatrix
    
    np.random.seed(42)
    torch.manual_seed(42)
    
    n_features = 100
    cms = []
    for i in range(200):
        cm_matrix = np.random.randn(n_features, n_features).astype(np.float32)
        cm_matrix = (cm_matrix + cm_matrix.T) / 2
        np.fill_diagonal(cm_matrix, 1.0)
        
        cm = ConnectivityMatrix(
            subject_id=f"subj_{i//20}",
            segment_id=i % 20,
            matrix=cm_matrix,
            n_features=n_features,
            segment_length=100
        )
        cms.append(cm)
    
    cluster_labels = np.random.randint(0, 5, size=len(cms))
    
    train_loader, val_loader, test_loader = create_dataloaders(
        cms, cluster_labels, batch_size=32
    )
    
    config = BrainLMConfig(
        n_features=100,
        d_model=128,
        nhead=4,
        num_encoder_layers=2,
        num_decoder_layers=1,
        max_seq_len=64
    )
    
    checkpoint_dir = Path("checkpoint/brainlm_test")
    
    model, history = train_brainlm(
        train_loader=train_loader,
        val_loader=val_loader,
        config=config,
        max_epochs=5,
        lr=1e-3,
        patience=3,
        checkpoint_dir=checkpoint_dir
    )
    
    print(f"\nFinal train loss: {history['train_loss'][-1]:.4f}")
    print(f"Final val loss: {history['val_loss'][-1]:.4f}")
    
    if torch.cuda.is_available():
        device = torch.device('cuda')
    elif torch.backends.mps.is_available():
        device = torch.device('mps')
    else:
        device = torch.device('cpu')
    
    latents, cluster_ids = extract_latents(model, test_loader, device)
    print(f"\nExtracted latents shape: {latents.shape}")
    print(f"Unique clusters: {np.unique(cluster_ids)}")
