"""
BrainLM Dataset Module

Dataset classes for training BrainLM on connectivity matrices.
"""

import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import pickle

import sys
sys.path.append(str(Path(__file__).parent.parent))
from pipeline.connectivity import ConnectivityMatrix
from pipeline.clustering import ClusteringResult, flatten_cm


class BrainLMDataset(Dataset):
    """
    Dataset for BrainLM training.
    
    Each sample is a sequence of connectivity matrices with optional masking.
    """
    
    def __init__(
        self,
        cms: List[ConnectivityMatrix],
        cluster_labels: Optional[np.ndarray] = None,
        max_seq_len: int = 512,
        mask_ratio: float = 0.15,
        use_upper_triangle: bool = True,
        augment: bool = True
    ):
        """
        Initialize dataset.
        
        Args:
            cms: List of ConnectivityMatrix objects
            cluster_labels: Optional cluster assignments for each CM
            max_seq_len: Maximum sequence length
            mask_ratio: Ratio of tokens to mask
            use_upper_triangle: Whether to use only upper triangle of CM
            augment: Whether to apply data augmentation
        """
        self.cms = cms
        self.cluster_labels = cluster_labels
        self.max_seq_len = max_seq_len
        self.mask_ratio = mask_ratio
        self.use_upper_triangle = use_upper_triangle
        self.augment = augment
        
        if cms:
            self.n_features = cms[0].n_features
            if use_upper_triangle:
                self.feature_dim = self.n_features * (self.n_features - 1) // 2
            else:
                self.feature_dim = self.n_features * self.n_features
        else:
            self.n_features = 100
            self.feature_dim = 4950
        
        self._prepare_data()
    
    def _prepare_data(self):
        """Prepare CM data as numpy arrays"""
        self.cm_arrays = []
        for cm in self.cms:
            if self.use_upper_triangle:
                flat = flatten_cm(cm.matrix)
            else:
                flat = cm.matrix.flatten()
            self.cm_arrays.append(flat.astype(np.float32))
        
        self.cm_arrays = np.array(self.cm_arrays)
    
    def __len__(self) -> int:
        return len(self.cms)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        """
        Get a single sample.
        
        Returns dictionary with:
        - input_ids: Potentially masked CM features
        - attention_mask: Valid position mask
        - labels: Original (unmasked) CM features
        - mask_labels: Binary mask for masked positions
        - cluster_id: Cluster assignment (if available)
        """
        cm_flat = self.cm_arrays[idx].copy()
        
        if self.augment:
            cm_flat = self._augment(cm_flat)
        
        input_ids = cm_flat.copy()
        labels = cm_flat.copy()
        
        mask_labels = np.zeros(1, dtype=np.float32)
        if self.mask_ratio > 0:
            n_mask = max(1, int(self.mask_ratio))
            if np.random.random() < self.mask_ratio:
                noise = np.random.randn(*cm_flat.shape) * 0.1
                input_ids = cm_flat + noise
                mask_labels = np.ones(1, dtype=np.float32)
        
        input_ids = input_ids.reshape(1, -1)
        labels = labels.reshape(1, -1)
        attention_mask = np.ones(1, dtype=np.float32)
        
        result = {
            'input_ids': torch.from_numpy(input_ids).float(),
            'attention_mask': torch.from_numpy(attention_mask).float(),
            'labels': torch.from_numpy(labels).float(),
            'mask_labels': torch.from_numpy(mask_labels).float(),
        }
        
        if self.cluster_labels is not None:
            result['cluster_id'] = torch.tensor(self.cluster_labels[idx], dtype=torch.long)
        else:
            result['cluster_id'] = torch.tensor(-1, dtype=torch.long)
        
        return result
    
    def _augment(self, cm_flat: np.ndarray) -> np.ndarray:
        """Apply data augmentation"""
        if np.random.random() < 0.3:
            noise = np.random.randn(*cm_flat.shape) * 0.05
            cm_flat = cm_flat + noise
        
        return cm_flat


class SequenceBrainLMDataset(Dataset):
    """
    Dataset for BrainLM with sequences of CMs.
    
    Groups CMs by subject/cluster and creates sequences.
    """
    
    def __init__(
        self,
        all_cms: Dict[str, List[ConnectivityMatrix]],
        cluster_labels: Optional[Dict[str, np.ndarray]] = None,
        seq_len: int = 16,
        stride: int = 8,
        mask_ratio: float = 0.15,
        use_upper_triangle: bool = True
    ):
        """
        Initialize sequence dataset.
        
        Args:
            all_cms: Dictionary mapping subject_id to list of CMs
            cluster_labels: Dictionary mapping subject_id to cluster assignments
            seq_len: Sequence length
            stride: Stride for sliding window
            mask_ratio: Ratio of tokens to mask
            use_upper_triangle: Whether to use only upper triangle
        """
        self.all_cms = all_cms
        self.cluster_labels = cluster_labels or {}
        self.seq_len = seq_len
        self.stride = stride
        self.mask_ratio = mask_ratio
        self.use_upper_triangle = use_upper_triangle
        
        self._build_sequences()
    
    def _build_sequences(self):
        """Build sequences from CMs"""
        self.sequences = []
        self.sequence_info = []
        
        for subject_id, cms in self.all_cms.items():
            if len(cms) < self.seq_len:
                continue
            
            n_features = cms[0].n_features
            if self.use_upper_triangle:
                feature_dim = n_features * (n_features - 1) // 2
            else:
                feature_dim = n_features * n_features
            
            cm_arrays = []
            for cm in cms:
                if self.use_upper_triangle:
                    flat = flatten_cm(cm.matrix)
                else:
                    flat = cm.matrix.flatten()
                cm_arrays.append(flat)
            
            cm_arrays = np.array(cm_arrays, dtype=np.float32)
            
            cluster_labels = self.cluster_labels.get(subject_id, 
                                                      np.full(len(cms), -1))
            
            for start in range(0, len(cms) - self.seq_len + 1, self.stride):
                end = start + self.seq_len
                seq = cm_arrays[start:end]
                labels = cluster_labels[start:end] if len(cluster_labels) >= end else np.full(self.seq_len, -1)
                
                self.sequences.append(seq)
                self.sequence_info.append({
                    'subject_id': subject_id,
                    'start_idx': start,
                    'end_idx': end,
                    'cluster_labels': labels
                })
    
    def __len__(self) -> int:
        return len(self.sequences)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        seq = self.sequences[idx].copy()
        info = self.sequence_info[idx]
        
        seq_len, feature_dim = seq.shape
        
        mask_labels = np.zeros(seq_len, dtype=np.float32)
        n_mask = max(1, int(seq_len * self.mask_ratio))
        mask_indices = np.random.choice(seq_len, n_mask, replace=False)
        mask_labels[mask_indices] = 1.0
        
        input_ids = seq.copy()
        for i in mask_indices:
            input_ids[i] = np.random.randn(feature_dim) * 0.1
        
        return {
            'input_ids': torch.from_numpy(input_ids).float(),
            'attention_mask': torch.ones(seq_len, dtype=torch.float),
            'labels': torch.from_numpy(seq).float(),
            'mask_labels': torch.from_numpy(mask_labels).float(),
            'cluster_ids': torch.from_numpy(info['cluster_labels'].astype(np.int64))
        }


def create_dataloaders(
    cms: List[ConnectivityMatrix],
    cluster_labels: Optional[np.ndarray] = None,
    batch_size: int = 32,
    val_split: float = 0.1,
    test_split: float = 0.1,
    num_workers: int = 0,
    **dataset_kwargs
) -> Tuple[DataLoader, DataLoader, DataLoader]:
    """
    Create train, validation, and test dataloaders.
    
    Args:
        cms: List of ConnectivityMatrix objects
        cluster_labels: Optional cluster assignments
        batch_size: Batch size
        val_split: Validation split ratio
        test_split: Test split ratio
        num_workers: Number of workers for DataLoader
        **dataset_kwargs: Additional arguments for dataset
        
    Returns:
        Tuple of (train_loader, val_loader, test_loader)
    """
    n_total = len(cms)
    n_test = int(n_total * test_split)
    n_val = int(n_total * val_split)
    n_train = n_total - n_test - n_val
    
    indices = np.random.permutation(n_total)
    train_indices = indices[:n_train]
    val_indices = indices[n_train:n_train + n_val]
    test_indices = indices[n_train + n_val:]
    
    train_cms = [cms[i] for i in train_indices]
    val_cms = [cms[i] for i in val_indices]
    test_cms = [cms[i] for i in test_indices]
    
    train_labels = cluster_labels[train_indices] if cluster_labels is not None else None
    val_labels = cluster_labels[val_indices] if cluster_labels is not None else None
    test_labels = cluster_labels[test_indices] if cluster_labels is not None else None
    
    train_dataset = BrainLMDataset(train_cms, train_labels, augment=True, **dataset_kwargs)
    val_dataset = BrainLMDataset(val_cms, val_labels, augment=False, **dataset_kwargs)
    test_dataset = BrainLMDataset(test_cms, test_labels, augment=False, **dataset_kwargs)
    
    train_loader = DataLoader(
        train_dataset, batch_size=batch_size, shuffle=True, num_workers=num_workers
    )
    val_loader = DataLoader(
        val_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    test_loader = DataLoader(
        test_dataset, batch_size=batch_size, shuffle=False, num_workers=num_workers
    )
    
    return train_loader, val_loader, test_loader


def save_dataset(
    cms: List[ConnectivityMatrix],
    cluster_labels: Optional[np.ndarray],
    filepath: Path
):
    """Save dataset to disk"""
    data = {
        'cms': cms,
        'cluster_labels': cluster_labels
    }
    with open(filepath, 'wb') as f:
        pickle.dump(data, f)


def load_dataset(filepath: Path) -> Tuple[List[ConnectivityMatrix], Optional[np.ndarray]]:
    """Load dataset from disk"""
    with open(filepath, 'rb') as f:
        data = pickle.load(f)
    return data['cms'], data['cluster_labels']


if __name__ == "__main__":
    np.random.seed(42)
    n_features = 100
    
    cms = []
    for i in range(100):
        cm_matrix = np.random.randn(n_features, n_features).astype(np.float32)
        cm_matrix = (cm_matrix + cm_matrix.T) / 2
        np.fill_diagonal(cm_matrix, 1.0)
        
        cm = ConnectivityMatrix(
            subject_id=f"subj_{i//10}",
            segment_id=i % 10,
            matrix=cm_matrix,
            n_features=n_features,
            segment_length=100
        )
        cms.append(cm)
    
    cluster_labels = np.random.randint(0, 5, size=len(cms))
    
    train_loader, val_loader, test_loader = create_dataloaders(
        cms, cluster_labels, batch_size=16
    )
    
    print(f"Train batches: {len(train_loader)}")
    print(f"Val batches: {len(val_loader)}")
    print(f"Test batches: {len(test_loader)}")
    
    batch = next(iter(train_loader))
    print(f"\nBatch keys: {batch.keys()}")
    print(f"Input shape: {batch['input_ids'].shape}")
    print(f"Labels shape: {batch['labels'].shape}")
