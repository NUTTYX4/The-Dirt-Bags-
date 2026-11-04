# Kaggle Chilli baseline

This kernel trains only the six-class **original** CH-001 Chilli dataset. Put
`chilli-original-images.zip` at the root of the private Kaggle dataset
`ashray777/cropscope-chilli-original-v1`, then run `kaggle kernels push -p .`
from this directory. The script extracts safely into `/kaggle/working/data`,
writes all artifacts to `/kaggle/working/cropscope_outputs`, and never changes
the attached input archive.

Use `--smoke-test` to validate the full pipeline using two batches per split.
