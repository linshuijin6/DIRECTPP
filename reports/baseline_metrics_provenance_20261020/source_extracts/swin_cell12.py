# Original=source_archive/vscode-3002/home/ssddata/liutuo/mri2pet swinunet useful.ipynb
# original_sha256=36b1db9e305c6b05b22f4398129e3ea385e99c5d102a08ebf040db99444fc53e; zero_based_cell=12
from monai.networks.nets import ViT, ViTAutoEnc, SwinUNETR


roi = (160,192,160)
batch_size = 1
sw_batch_size = 2
infer_overlap = 0.5
max_epochs = 500
val_every = 10


model = SwinUNETR(
    img_size=(160,192,160),
    in_channels=1,
    out_channels=1,
    feature_size=48,
    drop_rate=0.0,
    attn_drop_rate=0.0,
    dropout_path_rate=0.0,
    use_checkpoint=False,
).to(device)
optimizer = torch.optim.Adam(params=model.parameters(), lr=1e-5)