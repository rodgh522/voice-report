"""Voice Report - Convert voice recordings into structured meeting reports."""

__version__ = "0.1.0"

import torch
import functools

# Monkeypatch torch.load to default weights_only=False
# This is required because pyannote/whisperx checkpoints contain globals (ListConfig, ContainerMetadata, etc.)
# that are not in the default safe allowlist of PyTorch 2.6+.
# Monkeypatch torch.load to default weights_only=False
_original_load = torch.load

def _strict_load(*args, **kwargs):
    if kwargs.get("weights_only") is None:
        kwargs["weights_only"] = False
    return _original_load(*args, **kwargs)

torch.load = _strict_load
