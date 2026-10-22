"""Numerical test of sequential tracer backpropagation, not a PET experiment."""
from pathlib import Path
import argparse
import numpy as np
import torch
import torch.nn.functional as F
from common import new_model,seed_all,write_json


def check(out):
    torch.set_num_threads(4);seed_all(42);model=new_model().cuda().train()
    x=torch.rand(1,1,16,16,16,device="cuda")
    targets=[torch.rand_like(x),torch.rand_like(x)]
    context=[torch.randn(1,2,512,device="cuda") for _ in range(2)]
    t=torch.tensor([317],device="cuda");fraction=.317
    opt=torch.optim.Adam(model.parameters(),lr=2.5e-5)
    for _ in range(2):
        opt.zero_grad();loss=sum(F.mse_loss(model(x=fraction*y+(1-fraction)*x,timesteps=t,context=c),y-x)
                                for y,c in zip(targets,context));loss.backward();opt.step()
    results=[]
    for amp in [False,True]:
        gradients=[]
        for sequential in [False,True]:
            model.zero_grad(set_to_none=True);losses=[]
            for y,c in zip(targets,context):
                with torch.autocast("cuda",enabled=amp,dtype=torch.float16):
                    p=model(x=fraction*y+(1-fraction)*x,timesteps=t,context=c)
                    loss=F.mse_loss(p.float(),(y-x).float())
                if sequential:(loss*65536).backward()
                else:losses.append(loss)
            if not sequential:(sum(losses)*65536).backward()
            gradients.append({k:p.grad.detach().float().cpu()/65536 for k,p in model.named_parameters() if p.grad is not None})
        maxdiff=max(float((gradients[0][k]-gradients[1][k]).abs().max()) for k in gradients[0])
        for k in gradients[0]:
            assert torch.isfinite(gradients[0][k]).all() and torch.isfinite(gradients[1][k]).all()
            torch.testing.assert_close(gradients[0][k],gradients[1][k],rtol=1e-3 if amp else 1e-5,atol=1e-5 if amp else 1e-6)
        results.append(dict(amp=amp,parameters_checked=len(gradients[0]),max_absolute_gradient_difference=maxdiff,pass_=True))
    write_json(out,dict(purpose="numerical fixture on random 16^3 inputs; not clinical or synthesis results",
        comparison="backward(L_FDG+L_AV45) versus two backward calls before one optimizer step",
        objective_unchanged=True,results=results))
    print(results,flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser();p.add_argument("--out",type=Path,required=True);a=p.parse_args();check(a.out)
