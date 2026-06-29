"""
CM Tokenizer Module

This module tokenizes connectivity matrices for input to BrainLM.
Converts sequences of CMs into fixed-length tokens.
"""

import numpy as np
from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
import torch

from .connectivity import ConnectivityMatrix
from .clustering import ClusteringResult, flatten_cm, unflatten_cm


@dataclass
class TokenizedSequence:
    """Represents a tokenized CM sequence"""
    tokens: np.ndarray
    cluster_ids: List[int]
    subject_ids: List[str]
    segment_ids: List[int]
    attention_mask: np.ndarray
    
    def to_tensor(self) -> Dict[str, torch.Tensor]:
        """Convert to PyTorch tensors"""
        return {
            'input_ids': torch.from_numpy(self.tokens).float(),
            'attention_mask': torch.from_numpy(self.attention_mask).float(),
            'cluster_ids': torch.tensor(self.cluster_ids, dtype=torch.long)
        }


class CMTokenizer:
    """
    Tokenizer for connectivity matrices.
    
    Converts CM sequences into fixed-length tokens for BrainLM input.
    """
    
    def __init__(
        self,
        n_features: int = 100,
        token_size: int = 100,
        max_seq_len: int = 512,
        use_upper_triangle: bool = True,
        pad_value: float = 0.0
    ):
        """
        Initialize tokenizer.
        
        Args:
            n_features: Number of brain regions
            token_size: Size of each token (rows of CM to include)
            max_seq_len: Maximum sequence length
            use_upper_triangle: Whether to use only upper triangle
            pad_value: Value for padding
        """
        self.n_features = n_features
        self.token_size = token_size
        self.max_seq_len = max_seq_len
        self.use_upper_triangle = use_upper_triangle
        self.pad_value = pad_value
        
        if use_upper_triangle:
            self.feature_dim = n_features * (n_features - 1) // 2
        else:
            self.feature_dim = n_features * n_features
    
    def tokenize_single_cm(self, cm: np.ndarray) -> np.ndarray:
        """
        Tokenize a single connectivity matrix.
        
        Args:
            cm: Connectivity matrix of shape (n_features, n_features)
            
        Returns:
            Token representation
        """
        if self.use_upper_triangle:
            return flatten_cm(cm)
        else:
            return cm.flatten()
    
    def tokenize_cm_sequence(
        self,
        cms: List[ConnectivityMatrix],
        cluster_labels: Optional[np.ndarray] = None
    ) -> TokenizedSequence:
        """
        Tokenize a sequence of connectivity matrices.
        
        Args:
            cms: List of ConnectivityMatrix objects
            cluster_labels: Optional cluster assignments
            
        Returns:
            TokenizedSequence object
        """
        tokens = []
        cluster_ids = []
        subject_ids = []
        segment_ids = []
        
        for i, cm in enumerate(cms):
            token = self.tokenize_single_cm(cm.matrix)
            tokens.append(token)
            subject_ids.append(cm.subject_id)
            segment_ids.append(cm.segment_id)
            
            if cluster_labels is not None and i < len(cluster_labels):
                cluster_ids.append(int(cluster_labels[i]))
            else:
                cluster_ids.append(-1)
        
        tokens = np.array(tokens, dtype=np.float32)
        
        seq_len = len(tokens)
        if seq_len > self.max_seq_len:
            tokens = tokens[:self.max_seq_len]
            cluster_ids = cluster_ids[:self.max_seq_len]
            subject_ids = subject_ids[:self.max_seq_len]
            segment_ids = segment_ids[:self.max_seq_len]
            attention_mask = np.ones(self.max_seq_len, dtype=np.float32)
        else:
            pad_len = self.max_seq_len - seq_len
            padding = np.full((pad_len, self.feature_dim), self.pad_value, dtype=np.float32)
            tokens = np.concatenate([tokens, padding], axis=0)
            attention_mask = np.concatenate([
                np.ones(seq_len, dtype=np.float32),
                np.zeros(pad_len, dtype=np.float32)
            ])
            cluster_ids.extend([-1] * pad_len)
            subject_ids.extend(['[PAD]'] * pad_len)
            segment_ids.extend([-1] * pad_len)
        
        return TokenizedSequence(
            tokens=tokens,
            cluster_ids=cluster_ids,
            subject_ids=subject_ids,
            segment_ids=segment_ids,
            attention_mask=attention_mask
        )
    
    def tokenize_by_cluster(
        self,
        all_cms: Dict[str, List[ConnectivityMatrix]],
        clustering_result: ClusteringResult
    ) -> Dict[int, TokenizedSequence]:
        """
        Tokenize CMs grouped by cluster.
        
        Args:
            all_cms: Dictionary of CMs by subject
            clustering_result: Clustering result
            
        Returns:
            Dictionary mapping cluster_id to TokenizedSequence
        """
        cm_list = []
        for subject_id, cms in all_cms.items():
            cm_list.extend(cms)
        
        cluster_cms = {i: [] for i in range(clustering_result.n_clusters)}
        
        for i, (subject_id, segment_id) in enumerate(clustering_result.cm_labels):
            cluster_id = clustering_result.labels[i]
            for cms in all_cms.get(subject_id, []):
                for cm in [cms] if isinstance(cms, ConnectivityMatrix) else cms:
                    if cm.segment_id == segment_id:
                        cluster_cms[cluster_id].append(cm)
                        break
        
        tokenized = {}
        for cluster_id, cms in cluster_cms.items():
            if cms:
                cluster_labels = np.full(len(cms), cluster_id)
                tokenized[cluster_id] = self.tokenize_cm_sequence(cms, cluster_labels)
        
        return tokenized
    
    def create_sliding_window_tokens(
        self,
        cms: List[ConnectivityMatrix],
        window_size: int = 10,
        stride: int = 5
    ) -> List[TokenizedSequence]:
        """
        Create tokens using sliding window over CM sequence.
        
        Args:
            cms: List of CMs
            window_size: Window size
            stride: Stride between windows
            
        Returns:
            List of TokenizedSequence objects
        """
        sequences = []
        n_cms = len(cms)
        
        for start in range(0, n_cms - window_size + 1, stride):
            end = start + window_size
            window_cms = cms[start:end]
            seq = self.tokenize_cm_sequence(window_cms)
            sequences.append(seq)
        
        return sequences
    
    def concatenate_cluster_cms(
        self,
        cluster_tokenized: Dict[int, TokenizedSequence]
    ) -> np.ndarray:
        """
        Concatenate CMs from all clusters into one sequence.
        
        Args:
            cluster_tokenized: Dictionary of tokenized sequences by cluster
            
        Returns:
            Concatenated token array
        """
        all_tokens = []
        
        for cluster_id in sorted(cluster_tokenized.keys()):
            seq = cluster_tokenized[cluster_id]
            valid_len = int(seq.attention_mask.sum())
            all_tokens.append(seq.tokens[:valid_len])
        
        if all_tokens:
            return np.concatenate(all_tokens, axis=0)
        return np.array([], dtype=np.float32)


class BrainLMTokenizer(CMTokenizer):
    """
    Extended tokenizer for BrainLM with special tokens.
    """
    
    def __init__(
        self,
        n_features: int = 100,
        max_seq_len: int = 512,
        mask_ratio: float = 0.15,
        **kwargs
    ):
        super().__init__(n_features=n_features, max_seq_len=max_seq_len, **kwargs)
        self.mask_ratio = mask_ratio
        
        self.cls_token = np.zeros(self.feature_dim, dtype=np.float32)
        self.sep_token = np.ones(self.feature_dim, dtype=np.float32) * 0.5
        self.mask_token = np.ones(self.feature_dim, dtype=np.float32) * -1.0
    
    def add_special_tokens(
        self,
        tokens: np.ndarray,
        attention_mask: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray]:
        """
        Add CLS and SEP tokens.
        
        Args:
            tokens: Token array
            attention_mask: Attention mask
            
        Returns:
            Tuple of (tokens_with_special, attention_mask)
        """
        valid_len = int(attention_mask.sum())
        
        new_tokens = np.zeros((self.max_seq_len, self.feature_dim), dtype=np.float32)
        new_mask = np.zeros(self.max_seq_len, dtype=np.float32)
        
        new_tokens[0] = self.cls_token
        new_mask[0] = 1.0
        
        copy_len = min(valid_len, self.max_seq_len - 2)
        new_tokens[1:1+copy_len] = tokens[:copy_len]
        new_mask[1:1+copy_len] = 1.0
        
        if copy_len + 1 < self.max_seq_len:
            new_tokens[1+copy_len] = self.sep_token
            new_mask[1+copy_len] = 1.0
        
        return new_tokens, new_mask
    
    def apply_masking(
        self,
        tokens: np.ndarray,
        attention_mask: np.ndarray
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Apply random masking for masked language modeling.
        
        Args:
            tokens: Token array
            attention_mask: Attention mask
            
        Returns:
            Tuple of (masked_tokens, mask_labels, original_tokens)
        """
        valid_indices = np.where(attention_mask == 1.0)[0]
        
        if len(valid_indices) <= 2:
            return tokens.copy(), np.zeros(len(tokens)), tokens.copy()
        
        maskable_indices = valid_indices[1:-1]
        
        n_mask = max(1, int(len(maskable_indices) * self.mask_ratio))
        mask_indices = np.random.choice(maskable_indices, n_mask, replace=False)
        
        masked_tokens = tokens.copy()
        mask_labels = np.zeros(len(tokens), dtype=np.float32)
        
        for idx in mask_indices:
            masked_tokens[idx] = self.mask_token
            mask_labels[idx] = 1.0
        
        return masked_tokens, mask_labels, tokens.copy()
    
    def prepare_for_training(
        self,
        cms: List[ConnectivityMatrix],
        cluster_labels: Optional[np.ndarray] = None
    ) -> Dict[str, torch.Tensor]:
        """
        Prepare CM sequence for BrainLM training.
        
        Args:
            cms: List of CMs
            cluster_labels: Optional cluster assignments
            
        Returns:
            Dictionary of tensors for training
        """
        seq = self.tokenize_cm_sequence(cms, cluster_labels)
        
        tokens, attention_mask = self.add_special_tokens(seq.tokens, seq.attention_mask)
        
        masked_tokens, mask_labels, original_tokens = self.apply_masking(tokens, attention_mask)
        
        return {
            'input_ids': torch.from_numpy(masked_tokens).float(),
            'attention_mask': torch.from_numpy(attention_mask).float(),
            'labels': torch.from_numpy(original_tokens).float(),
            'mask_labels': torch.from_numpy(mask_labels).float(),
            'cluster_ids': torch.tensor(seq.cluster_ids[:len(attention_mask)], dtype=torch.long)
        }


if __name__ == "__main__":
    np.random.seed(42)
    n_features = 100
    
    cms = []
    for i in range(20):
        cm_matrix = np.random.randn(n_features, n_features).astype(np.float32)
        cm_matrix = (cm_matrix + cm_matrix.T) / 2
        np.fill_diagonal(cm_matrix, 1.0)
        
        cm = ConnectivityMatrix(
            subject_id=f"subj_{i//5}",
            segment_id=i % 5,
            matrix=cm_matrix,
            n_features=n_features,
            segment_length=100
        )
        cms.append(cm)
    
    tokenizer = BrainLMTokenizer(n_features=n_features, max_seq_len=32)
    
    seq = tokenizer.tokenize_cm_sequence(cms)
    print(f"Tokenized shape: {seq.tokens.shape}")
    print(f"Attention mask sum: {seq.attention_mask.sum()}")
    
    training_data = tokenizer.prepare_for_training(cms)
    print(f"\nTraining data keys: {training_data.keys()}")
    print(f"Input shape: {training_data['input_ids'].shape}")
    print(f"Mask labels sum: {training_data['mask_labels'].sum().item()}")
