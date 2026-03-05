import numpy as np
from torch.utils.data import Dataset


class MyDataset(Dataset):
    """
    Sliding-window dataset for MTAD-GAT.

    For each index i, returns:
        x : window  data[i : i+w]          shape (w, n_features)
        y : next step  data[i+w : i+w+1]   shape (1, n_features)
    """

    def __init__(self, data: np.ndarray, w: int = 64):
        """
        Args:
            data: time series of shape (T, n_features)
            w:    window length
        """
        self.data = data
        self.w = w

    def __len__(self) -> int:
        return max(0, len(self.data) - self.w)

    def __getitem__(self, index):
        x = self.data[index: index + self.w]
        y = self.data[index + self.w: index + self.w + 1]
        return x, y
