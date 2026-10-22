"""Bounded CUDA regression fixture for the native batch_step (no PET results)."""
import copy
import io
import json
import sys
from contextlib import redirect_stdout
from pathlib import Path

import torch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'experiments/e1_clinical_conditioning'))
from run import batch_step
from common import write_json


class Fixture(torch.nn.Module):
    def __init__(self):
        super().__init__()
        self.dropout=torch.nn.Dropout(.25)
        self.linear=torch.nn.Linear(4,4)
        torch.nn.init.constant_(self.linear.weight,.1)
        torch.nn.init.constant_(self.linear.bias,.2)

    def forward(self,x,timesteps,context):
        return self.linear(self.dropout(x))


def main():
    torch.manual_seed(43);torch.cuda.manual_seed_all(43)
    data={key:torch.full((1,4),value,device='cuda') for key,value in [('mri',.75),('fdg',.25),('av45',.1)]}
    patient=torch.zeros(512,device='cuda');adapter=torch.zeros(2,512,device='cuda')
    row=dict(ptid='synthetic_fixture',has_fdg=True,has_av45=True)
    model=Fixture().cuda();initial=copy.deepcopy(model.state_dict())
    initial_rng=torch.cuda.get_rng_state()
    calls=[]
    def optimizer():
        opt=torch.optim.Adam(model.parameters(),lr=2.5e-5)
        opt.register_step_post_hook(lambda *args:calls.append(1))
        return opt
    opt=optimizer();baseline_scaler=torch.amp.GradScaler('cuda',init_scale=1.)
    baseline_loss=batch_step(model,opt,baseline_scaler,data,row,patient,adapter,395)
    baseline=copy.deepcopy(model.state_dict());baseline_rng=torch.cuda.get_rng_state()
    baseline_opt=copy.deepcopy(opt.state_dict())
    assert len(calls)==1

    model.load_state_dict(initial);torch.cuda.set_rng_state(initial_rng);calls.clear();opt=optimizer()
    scaler=torch.amp.GradScaler('cuda',init_scale=2.**20)
    output=io.StringIO()
    with redirect_stdout(output):loss=batch_step(model,opt,scaler,data,row,patient,adapter,395)
    events=[json.loads(line) for line in output.getvalue().splitlines()]
    assert events and len(calls)==1 and all(e['scale_after']==e['scale_before']/2 for e in events)
    assert loss==baseline_loss and torch.equal(torch.cuda.get_rng_state(),baseline_rng)
    for key,value in model.state_dict().items():torch.testing.assert_close(value,baseline[key],rtol=1e-3,atol=1e-6)
    for key,value in opt.state_dict()['state'].items():
        for name,tensor in value.items():torch.testing.assert_close(tensor,baseline_opt['state'][key][name],rtol=1e-3,atol=1e-6)
    assert all(int(state['step'])==1 for state in opt.state.values())
    recovered_scale=scaler.get_scale()

    # A forward NaN remains fatal, before any optimizer update.
    calls.clear();opt=optimizer();bad=dict(data,fdg=torch.full_like(data['fdg'],float('nan')))
    try:batch_step(model,opt,torch.amp.GradScaler('cuda'),bad,row,patient,adapter,395)
    except AssertionError as exc:assert 'Nonfinite pilot/training loss' in str(exc)
    else:raise AssertionError('NaN loss was accepted')
    assert not calls

    # Persistently invalid backward must exhaust the bounded retry and leave
    # model/optimizer intact, rather than count or apply an invalid update.
    saved=copy.deepcopy(model.state_dict());opt=optimizer();output=io.StringIO()
    hook=model.linear.weight.register_hook(lambda grad:torch.full_like(grad,float('inf')))
    try:
        with redirect_stdout(output):
            batch_step(model,opt,torch.amp.GradScaler('cuda',init_scale=1.),data,row,patient,adapter,395)
    except RuntimeError as exc:assert 'persisted after 8 AMP attempts' in str(exc)
    else:raise AssertionError('Persistent invalid gradient was accepted')
    finally:hook.remove()
    assert not calls and not opt.state
    for key,value in model.state_dict().items():assert torch.equal(value,saved[key])
    assert len(output.getvalue().splitlines())==8
    result=dict(torch=torch.__version__,gpu=torch.cuda.get_device_name(0),
        finite_loss_overflow_reproduced=True,retries=len(events),recovered_scale=recovered_scale,
        actual_optimizer_updates=1,parameters_and_adam_state_match_reference=True,
        cuda_rng_matches_single_forward=True,nan_loss_fails=True,persistent_gradient_fails_without_update=True,
        fixture='synthetic Linear/Dropout; calls native batch_step; not generator/PET results')
    write_json(Path(sys.argv[1]),result);print(json.dumps(result),flush=True)


if __name__=='__main__':main()
