"""Export a report figure from the reviewed XML-product counts."""
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

OUT = Path(__file__).resolve().parent
d = pd.read_csv(OUT / 'image_metadata.csv', keep_default_na=False)
d = d[d.modality == 'PET']
labels = {
    'Coreg, Avg, Std Img and Vox Siz, Uniform 6mm Res': 'FDG: uniform 6 mm',
    'Coreg, Avg, Standardized Image and Voxel Size': 'FDG: standardized image / voxel size',
    'AV45 Coreg, Avg, Std Img and Vox Siz, Uniform 6mm Res': 'AV45: uniform 6 mm',
    'AV45 Coreg, Avg, Standardized Image and Voxel Size': 'AV45: standardized image / voxel size',
    'Co-registered Dynamic': 'FDG: co-registered dynamic',
    'AV45-Early Coreg, Avg, Standardized Image and Voxel Size': 'AV45-Early: standardized image / voxel size',
    'Co-registered, Averaged': 'FDG: co-registered and averaged',
    'AV45 Co-registered Dynamic': 'AV45: co-registered dynamic',
    'FBB Coreg, Avg, Standardized Image and Voxel Size': 'FBB label / AV45 protocol: tracer unresolved',
    'AV45-Early Coreg, Avg, Std Img and Vox Siz, Uniform 6mm Res': 'AV45-Early: uniform 6 mm',
}
counts = d.processed_data_label.value_counts()
assert set(counts.index) == set(labels) and counts.sum() == 602
data = counts.rename_axis('original_product_label').reset_index(name='image_count')
data['figure_label'] = data.original_product_label.map(labels)
data.to_csv(OUT / 'pet_product_figure_data.csv', index=False, encoding='utf-8-sig')
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 11})
fig, ax = plt.subplots(figsize=(12.4, 6.8))
fig.subplots_adjust(left=.40, right=.95, top=.86, bottom=.17)
bars = ax.barh(range(len(data)), data.image_count, color='#2d668f', height=.65)
ax.set_yticks(range(len(data)), data.figure_label)
ax.invert_yaxis()
ax.set_xlim(0, 210)
ax.set_xlabel('Number of downloaded metadata records')
ax.xaxis.grid(True, color='#dddddd', linewidth=.6)
ax.set_axisbelow(True)
for spine in ['top', 'right']:
    ax.spines[spine].set_visible(False)
for bar, count in zip(bars, data.image_count):
    ax.text(count + 2, bar.get_y() + bar.get_height()/2, str(count), va='center', fontsize=11)
fig.suptitle('PET processing products in the supplied metadata (n = 602)',
             x=.02, ha='left', fontsize=15, fontweight='bold')
fig.text(.02, .05, 'Scope: historical clinical-source Image IDs; actual study NIfTI identity remains unverified.\n'
         'Source: 1103_IDA_Metadata.zip, processedDataLabel and original Radiopharmaceutical fields.',
         fontsize=10, color='#444444', va='bottom')
fig.savefig(OUT / 'pet_processing_products.png', dpi=160)
fig.savefig(OUT / 'pet_processing_products.svg')
plt.close(fig)
