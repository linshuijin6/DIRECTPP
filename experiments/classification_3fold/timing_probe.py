#!/usr/bin/env python3
"""A few real training batches for cost estimation; no full fits or checkpoints."""
import argparse
import gc
import json
import os
import random
import subprocess
import time
from pathlib import Path

import numpy as np
import pandas as pd
from run import CONDITIONS, FEATURES, ROOT, SUBJECTS, REPORT, CLINICAL, load_subjects


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gpu", type=int, required=True)
    p.add_argument("--batch-size", type=int, required=True)
    p.add_argument("--memory-limit-gib", type=float, default=12)
    p.add_argument("--data-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    args = p.parse_args()
    uuid = subprocess.check_output(["nvidia-smi", "-i", str(args.gpu),
        "--query-gpu=uuid", "--format=csv,noheader"], text=True).strip()
    os.environ["CUDA_VISIBLE_DEVICES"] = uuid
    import torch
    from monai.data import CacheDataset, DataLoader
    from monai.transforms import Compose, LoadImaged, EnsureChannelFirstd, Identityd
    from monai.networks.nets import DenseNet121
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = torch.device("cuda:0")
    torch.cuda.set_per_process_memory_fraction(
        args.memory_limit_gib * 2**30 / torch.cuda.get_device_properties(device).total_memory)
    df = load_subjects(SUBJECTS, args.data_root).set_index("PTID")
    s = pd.read_csv(REPORT / "splits.csv")
    train = s[(s.task == "mci_cn") & (s.fold == 1) & (s.split == "train")]
    n = 6 * args.batch_size  # Two warm-up batches and four measured batches.
    subset = train.head(n)
    clinical = pd.read_csv(CLINICAL).set_index("Subject ID").loc[train.PTID, FEATURES]
    clinical["Sex"] = clinical.Sex.map({"M": 1, "F": 0})
    clinical = clinical.apply(pd.to_numeric, errors="coerce")
    clinical.loc[clinical.Weight.isin([0, 2.3]), "Weight"] = np.nan
    clinical = clinical.fillna(clinical.median())
    clinical = ((clinical - clinical.mean()) / clinical.std(ddof=0).replace(0, 1)).astype("float32")
    results = dict(gpu_uuid=uuid, gpu=torch.cuda.get_device_name(), batch_size=args.batch_size,
                   memory_limit_GiB=args.memory_limit_gib, warmup_batches=2, measured_batches=4,
                   data_source="mci_cn fold1 train only", conditions={})
    for condition in ["mri_syn_both", "mri", "mri_syn_fdg", "mri_clinical", "clinical"]:
        random.seed(143); np.random.seed(143); torch.manual_seed(143); torch.cuda.manual_seed_all(143)
        keys = CONDITIONS[condition]
        records = []
        for r in subset.itertuples():
            record = dict(PTID=r.PTID, label=r.y_true, clinical=clinical.loc[r.PTID].to_numpy())
            record.update({k: str(ROOT / df.at[r.PTID, k]) for k in keys})
            records.append(record)
        transform = Compose([LoadImaged(keys=keys),
            EnsureChannelFirstd(keys=keys, channel_dim="no_channel"), Identityd(keys=["label"])]) if keys else Compose([Identityd(keys=["label"])])
        start = time.perf_counter()
        dataset = CacheDataset(records, transform=transform, num_workers=4, progress=False)
        loader = DataLoader(dataset, batch_size=args.batch_size, num_workers=0, shuffle=False)
        cache_s = time.perf_counter() - start
        torch.cuda.empty_cache(); torch.cuda.reset_peak_memory_stats()
        if condition == "clinical":
            model = torch.nn.Linear(8, 2)
        else:
            model = DenseNet121(spatial_dims=3, in_channels=len(keys), out_channels=2)
            if condition == "mri_clinical":
                d = model.class_layers.out.in_features
                model.class_layers.out = torch.nn.Identity()
                model.clinical_head = torch.nn.Linear(d + 8, 2)
        model = model.to(device)
        optimizer = torch.optim.Adam(model.parameters(), lr=1e-4)
        loss_function = torch.nn.CrossEntropyLoss()
        train_times, inference_times = [], []
        for i, batch in enumerate(loader):
            images = torch.cat([batch[k].to(device) for k in keys], dim=1) if keys else None
            c = batch["clinical"].to(device)
            labels = batch["label"].long().to(device)
            def forward():
                if condition == "clinical":
                    return model(c)
                z = model(images)
                return model.clinical_head(torch.cat([z, c], dim=1)) if condition == "mri_clinical" else z
            model.train(); torch.cuda.synchronize(); start = time.perf_counter()
            optimizer.zero_grad(); outputs = forward(); loss = loss_function(outputs, labels)
            loss.backward(); optimizer.step(); torch.cuda.synchronize()
            train_s = time.perf_counter() - start
            model.eval(); start = time.perf_counter()
            with torch.no_grad():
                torch.softmax(forward(), dim=1)[:, 1].cpu().tolist()
            torch.cuda.synchronize(); inference_s = time.perf_counter() - start
            if i >= 2:
                train_times.append(train_s); inference_times.append(inference_s)
        result = dict(cache_s=cache_s, subjects=n, train_batch_s=train_times,
                      inference_batch_s=inference_times,
                      parameters=sum(x.numel() for x in model.parameters()),
                      peak_allocated_MiB=torch.cuda.max_memory_allocated() / 2**20,
                      peak_reserved_MiB=torch.cuda.max_memory_reserved() / 2**20)
        results["conditions"][condition] = result
        args.output.write_text(json.dumps(results, indent=2) + "\n")
        print(condition, json.dumps(result), flush=True)
        del loss, outputs, optimizer, model, images, c, labels, batch, loader, dataset
        gc.collect(); torch.cuda.empty_cache()


if __name__ == "__main__":
    main()
