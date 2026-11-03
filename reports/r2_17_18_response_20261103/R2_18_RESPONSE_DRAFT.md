# Response to Reviewer 2, Comment 18

Thank you for requesting direct computational measurements. We agree that a training-cost estimate alone does not substantiate inference-efficiency claims. The available measurements support the following specific description of the generator's inference cost.

The benchmark uses the documented DIReCT++ revision model at fold 1, epoch 165, on an NVIDIA RTX 4090 with 24 GB of memory, using PyTorch 2.5.1+cu121 and FP32 inference. The input is one real MRI tensor of shape \(1\times1\times160\times192\times160\), with its clinical and tracer embeddings already cached on the GPU. Each tracer is measured separately after 10 warm-up calls, followed by 50 timed repetitions. CUDA synchronization is performed before and after each timed call. The timed operation includes the generator forward pass, addition of the predicted velocity to MRI, and output clamping to [0,1]. It excludes text encoding, image preprocessing, disk I/O, host-to-device transfers, and NIfTI export.

| Measurement | FDG | AV45 |
|---|---:|---:|
| Timed repetitions | 50 | 50 |
| Mean inference latency, ms | 251.015 | 251.411 |
| Sample SD of repeated-call latency, ms | 0.187 | 0.256 |
| Median latency, ms | 251.022 | 251.549 |
| 5th–95th percentiles of repeated-call latency, ms | 250.758–251.377 | 250.971–251.628 |
| Peak PyTorch allocated memory, GiB | 8.290 | 8.290 |
| Peak PyTorch reserved memory, GiB | 13.268 | 13.268 |

The generator contains **9,925,921 parameters**. This count excludes the frozen BiomedCLIP encoders and other components not executed in the measured generator forward pass. The memory values are peaks recorded by the PyTorch allocator under the stated protocol; they are not total GPU occupancy or training-memory requirements. The latency variation and percentiles describe repeated calls on one fixed input, rather than variability across a patient cohort or confidence intervals for population-level runtime.

An important implementation clarification is that a forward call produces **one tracer-specific PET volume**. The shared generator must be called with each tracer's context to produce both PET volumes. Thus, approximately 251 ms is a per-tracer, cached-input network latency and must not be described as the end-to-end time for simultaneous dual-PET generation. Likewise, the update \(\widehat x_m=\operatorname{clip}_{[0,1]}[x_{\mathrm{MRI}}+v_\theta(x_{\mathrm{MRI}},0,c_m)]\) is a learned one-step approximation, not a claim of exact numerical integration of the continuous ODE.

Two requested elements remain unavailable from the current profiling records. First, we do not have a validated FLOP total covering the full 3D network and its attention operators. We therefore report FLOPs as unavailable rather than inferring them from parameter count or presenting a partial operator count as a complete total. Second, there is no verified diffusion/flow-baseline latency series obtained with the same hardware, precision, resident inputs, warm-up procedure, synchronization, and timing boundaries. We consequently do not report a measured speedup factor or an efficiency ranking against those baselines. A lower number of sampling steps alone is not a direct runtime comparison.

The approximately **138 GPU-hours** stated in the original manuscript also cannot be independently verified from the recovered timing records. Its accounting boundary—such as a single fold versus the complete experiment, conditioning preparation, validation, and inference—is not established. We therefore do not treat that number as a verified training-cost measurement or infer it from the present RTX 4090 inference benchmark. The defensible efficiency statement is limited to the measured generator parameter count, memory use, and per-tracer latency under the specified conditions; FLOPs, matched baseline runtime comparisons, and the historical training-cost estimate remain explicit limitations.
