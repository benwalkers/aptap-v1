# Optional MiniLM model

Model weights are deliberately NOT bundled in this ZIP (they must be downloaded
from Hugging Face on your machine or via an approved build process). Once downloaded,
place the Sentence Transformers files in `models/minilm/`.

```
python -m pip install -r requirements-minilm.txt
python scripts/download_model.py
python -m pipeline data/ --engine minilm
```

The model is loaded with `local_files_only=True` and `HF_HUB_OFFLINE=1`.
Rebuilding the model from a pinned release/revision is recommended for production.
`all-MiniLM-L6-v2` is an EMBEDDING MODEL, not a pre-trained 10-category head.
Similarity is not probability. More complex is not automatically more accurate.
