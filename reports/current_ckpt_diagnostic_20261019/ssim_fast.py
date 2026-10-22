"""Separable implementation of the archived valid Gaussian 3D SSIM formula."""
import torch
import torch.nn.functional as F


@torch.inference_mode()
def ssim(x, y, kernel_size):
    dist = torch.arange((1-kernel_size)/2, (1+kernel_size)/2, dtype=torch.float32)
    g = torch.exp(-torch.pow(dist / 1.5, 2) / 2)
    g = (g/g.sum()).to(x.device)
    moments = torch.cat([x, y, x*x, y*y, x*y], dim=0)
    for shape in [(kernel_size, 1, 1), (1, kernel_size, 1), (1, 1, kernel_size)]:
        moments = F.conv3d(moments, g.reshape(1, 1, *shape))
    mx, my, mxx, myy, mxy = moments.unbind(0)
    vx = mxx-mx*mx
    vy = myy-my*my
    cov = mxy-mx*my
    return float((((2*mx*my+.01**2)/(mx.square()+my.square()+.01**2))
                  *((2*cov+.03**2)/(vx+vy+.03**2))).mean())
