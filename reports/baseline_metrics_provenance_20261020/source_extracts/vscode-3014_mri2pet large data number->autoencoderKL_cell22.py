# Original=source_archive/vscode-3014/mnt/ssd/liutuo/mri2pet large data number->autoencoderKL.ipynb
# original_sha256=dff52671131500db1ae00555ce93a2148cfbfa8775d7b18c2362be13d7712566; zero_based_cell=22
        from generative.metrics import SSIMMetric
        from monai.metrics import (MAEMetric,MSEMetric,PSNRMetric,)
        ssim_metric = SSIMMetric(spatial_dims=3, data_range=1.0, kernel_size=7)
        psnr_metric=PSNRMetric(1.0)
        

        ssim_value = ssim_metric(labels, current_img)
        psnr_value = psnr_metric(labels, current_img)

        print(f"SSIM: {ssim_value.mean().item()}")
        print(f"PSNR: {psnr_value.mean().item()}") 