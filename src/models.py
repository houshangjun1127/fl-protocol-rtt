"""Small CPU-friendly models and parameter-block partitioning."""
import torch
import torch.nn as nn
import torch.nn.functional as F


class SmallCNN(nn.Module):
    """Compact CNN: enough capacity to show non-IID effects, cheap on CPU."""

    def __init__(self, in_ch, img_size, n_classes, width=16):
        super().__init__()
        c, h, w = in_ch, img_size[0], img_size[1]
        self.features = nn.Sequential(
            nn.Conv2d(c, width, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
            nn.Conv2d(width, width * 2, 3, padding=1), nn.ReLU(), nn.MaxPool2d(2),
        )
        flat = width * 2 * (h // 4) * (w // 4)
        self.classifier = nn.Sequential(
            nn.Flatten(), nn.Linear(flat, 64), nn.ReLU(), nn.Linear(64, n_classes)
        )

    def forward(self, x):
        return self.classifier(self.features(x))


class TinyMLP(nn.Module):
    def __init__(self, in_ch, img_size, n_classes, hidden=128):
        super().__init__()
        d = in_ch * img_size[0] * img_size[1]
        self.net = nn.Sequential(
            nn.Flatten(), nn.Linear(d, hidden), nn.ReLU(), nn.Linear(hidden, n_classes)
        )

    def forward(self, x):
        return self.net(x)


def build_model(arch, in_ch, img_size, n_classes):
    if arch == "mlp":
        return TinyMLP(in_ch, img_size, n_classes)
    return SmallCNN(in_ch, img_size, n_classes)


def param_blocks(model):
    """Group parameters into semantically meaningful blocks.

    'conv'  - early feature extractor (low drift under label skew)
    'head'  - classifier (high drift)
    Each conv/linear layer is also exposed individually via 'layer:<name>'.
    """
    blocks = {}
    for name, p in model.named_parameters():
        if not p.requires_grad:
            continue
        if name.startswith("features"):
            blocks.setdefault("conv", []).append(name)
        else:
            blocks.setdefault("head", []).append(name)
    return blocks


def get_flat_grad(model):
    return torch.cat([p.detach().reshape(-1) for p in model.parameters() if p.requires_grad])


def flat_to_state(flat, ref_state):
    """Scatter a flat vector back into a state_dict-shaped mapping."""
    out, i = {}, 0
    for k, v in ref_state.items():
        n = v.numel()
        out[k] = flat[i:i + n].view_as(v)
        i += n
    return out