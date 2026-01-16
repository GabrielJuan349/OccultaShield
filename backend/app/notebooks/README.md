# Testing Notebooks - OccultaShield Backend

This folder contains notebooks for testing backend modules in isolation.

## Requirements

Make sure you have the project dependencies and `jupyter`/`notebook` installed.

```bash
pip install jupyter matplotlib ipykernel nest_asyncio
```

## Prior Configuration

1.  **YOLO Model**: Make sure you have `yolov10m.pt` (or whichever you use) in `backend/app/`.
2.  **Test Video**: Place an mp4 video in `backend/storage/uploads/` (e.g., `car.mp4`) or update the `VIDEO_PATH` variable in the notebook.

## Notebooks

### 1. [01_detection_module.ipynb](./01_detection_module.ipynb)
Test the YOLO detector and tracking.
- **Input**: Local video.
- **Output**: Track information and detection crops in `storage/captures/notebook_test`.

### 2. [02_edition_module.ipynb](./02_edition_module.ipynb)
Test video anonymization.
- **Input**: Local video.
- **Output**: Modified video with blur/pixelation.

### 3. [03_verification_module.ipynb](./03_verification_module.ipynb)
Test GDPR analysis (RAG + LLM).
- **Input**: Cropped images (captures).
- **Output**: Violations report.

### 4. [04_full_pipeline.ipynb](./04_full_pipeline.ipynb)
Run the entire flow in sequence without starting the API server.

## Execution

From the `backend/app` folder:

```bash
jupyter notebook notebooks/
```
