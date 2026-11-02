"""Small xformers attention API adapter backed by PyTorch SDPA.

The archived generator passes [batch*heads, tokens, dim]. Its auxiliary
self-attention block may pass [batch, tokens, heads, dim]. Both layouts are
mapped to attention over tokens.
"""
import torch.nn.functional as F


class LowerTriangularMask:
    pass


def memory_efficient_attention(query, key, value, attn_bias=None, p=0.0, scale=None):
    mask = True if isinstance(attn_bias, LowerTriangularMask) else attn_bias
    if query.ndim == 3:
        return F.scaled_dot_product_attention(
            query, key, value, attn_mask=None if mask is True else mask,
            dropout_p=p, is_causal=mask is True, scale=scale,
        )
    if query.ndim == 4:
        output = F.scaled_dot_product_attention(
            query.transpose(1, 2), key.transpose(1, 2), value.transpose(1, 2),
            attn_mask=None if mask is True else mask, dropout_p=p,
            is_causal=mask is True, scale=scale,
        )
        return output.transpose(1, 2)
    raise ValueError(f"Unsupported attention rank: {query.ndim}")
