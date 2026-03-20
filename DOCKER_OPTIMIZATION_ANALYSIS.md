# Docker Image Size Analysis & Optimization Report

## Current Issue: ~8GB Image Size

Your Docker image is oversized primarily due to **PyTorch dependency** being pulled in by sentence-transformers.

---

## Root Causes (Detailed Breakdown)

### 1. **PyTorch - The Main Culprit (1.5-2GB+)**
```
├─ sentence-transformers==2.3.1
│  └─ depends on: torch (2.10.0)
│     ├─ PyTorch core (500MB-700MB)
│     ├─ Pre-trained model weights (500MB-800MB)
│     ├─ CUDA libraries (if GPU version) (1GB+)
│     └─ Linked C++ dependencies
```

**Why it's so large:**
- PyTorch includes full ML framework (computation kernels, BLAS, LAPACK)
- Not stripped down for inference-only usage
- By default includes CPU+partial GPU support

### 2. **Heavy Dependencies (200-300MB)**
```
scipy==1.16.3          ~150MB (numerical computing)
numpy==2.3.5           ~50MB  (numerical arrays)
scikit-learn (implicit)~50MB  (ML utilities)
pandas (implicit)      ~30MB  (data processing)
```

### 3. **Inefficient Backend Dockerfile Pattern (Previous)**
```dockerfile
COPY . .  # Copies entire directory including:
          # - test_*.py files (not needed in production)
          # - migrate_*.py files (not needed in production)
          # - .git/ metadata (excluded in .dockerignore, good)
          # - __pycache__/ (excluded in .dockerignore, good)
          # - reg_db.sqlite3 (now excluded)
```

### 4. **Python Base Image Overhead**
- `python:3.11-slim` base: ~150-200MB (already optimized)
- Uncompressed installed packages: 1-2GB+

---

## Applied Fixes

### ✅ Fix #1: Multi-Stage Build (Dockerfile)
**Before:**
```dockerfile
FROM python:3.11-slim
RUN apt-get install gcc
RUN pip install -r requirements.txt  # Full install with build tools
COPY . .  # All files included
```

**After:**
```dockerfile
# Stage 1: Builder - compiles dependencies
FROM python:3.11-slim AS builder
RUN apt-get install gcc g++  # Build tools only here
RUN pip wheel -r requirements.txt  # Pre-compiles wheels (C extensions)

# Stage 2: Runtime - only needs runtime
FROM python:3.11-slim
RUN apt-get install --no-install-recommends  # No build tools
COPY --from=builder /wheels .
RUN pip install --no-index --find-links=/wheels  # Uses pre-built wheels
COPY app/ app/  # Only copies necessary files
```

**Impact:** 
- Removes 300-500MB of build tools (gcc, g++, headers)
- Pre-compiled wheels are smaller and install faster
- Excludes build dependencies from final image

### ✅ Fix #2: Improved .dockerignore
Added explicit exclusions:
```
test_*.py              # Exclude test files
migrate_*.py           # Exclude migration scripts
reg_db.sqlite3         # Exclude local database
railway.json           # Exclude config files
*.db *.sqlite *.sqlite3  # Exclude any DB files
node_modules/          # Exclude if any
.next/                 # Exclude if any
```

**Impact:** 
- Ensures test/migration files don't ship to production
- Prevents accidental DB file inclusion

### ✅ Fix #3: Security & Resource Improvements
```dockerfile
# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser
```

---

## Estimated Size Reduction

| Layer | Before | After | Savings |
|-------|--------|-------|---------|
| Build tools (gcc, g++) | +300MB | 0MB | **300MB** ↓ |
| Python packages | ~1.5GB | ~1.5GB | — |
| PyTorch | ~2GB | ~2GB | — |
| Unnecessary files | ~100MB | ~10MB | **90MB** ↓ |
| **Total** | **~8GB** | **~7.6GB** | **~400MB ↓** |

---

## Further Optimization Options (Advanced)

### Option A: Use CPU-Only PyTorch (Saves 500MB-1GB)
Replace in `requirements.txt`:
```diff
sentence-transformers==2.3.1
- torch>=1.11.0
+ torch==2.0.0+cpu  # Forces CPU-only version
```

**Trade-off:** Makes package harder to build across platforms. Works well on Railway.

### Option B: Use ONNX Instead of PyTorch (Saves 1.5GB+)
Replace:
```python
# Current: vector embeddings via sentence-transformers + torch
from sentence_transformers import SentenceTransformer

# Alternative: lighter ONNX version
pip install onnx onnxruntime-python
```

**Benefit:** ONNX Runtime is 10x smaller (~100MB vs 2GB)
**Cost:** Requires rewriting RAG embedding code in `ai_service.py` and `rag_service.py`

### Option C: Remove Unnecessary Dependencies
Audit requirements.txt:
```python
# Check if these are actually used:
deep-translator==1.11.4   # Only used if translation feature is active
reportlab==4.0.7          # Only used if PDF generation is active
pdfplumber==0.10.3        # Only used if PDF reading is active
```

Run:
```bash
pip install pipdeptree
pipdeptree --graph-output png > deps.png  # Visual dependency tree
```

### Option D: Use BuildKit with Cache Optimization
In `docker-compose.yml`:
```yaml
services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
      cache_from:
        - type=local,src=path/to/cache  # Cache reuse
```

---

## Verification Steps

After changes, rebuild and check size:

```powershell
# Build backend image
docker build -t reg-backend:optimized ./backend

# Get image size
docker images reg-backend:optimized
# Shows: SIZE column

# To see layer breakdown:
docker history reg-backend:optimized

# To inspect what's inside:
docker run --rm reg-backend:optimized du -sh /usr/local/lib/python3.11/site-packages/*
```

Expected output after optimization: **7.5-7.8GB** (if using PyTorch)

---

## Detailed Recommendations

### 🎯 Recommended for Railway Deployment

1. **Use the updated Dockerfile** (multi-stage) ✅ Already done
2. **Update .dockerignore** (exclude unnecessary files) ✅ Already done
3. **Monitor pip installations** - avoid bloat:
   ```bash
   # Check what's eating space
   pip install pipdeptree
   pipdeptree | grep -E "torch|scipy|numpy"
   ```

### 🔮 If You Need 50%+ Size Reduction

Switch to **ONNX runtime** with quantized models:
- Estimated size: 3-4GB (from 8GB)
- Requires code changes to `services/rag_service.py` and `services/ai_service.py`
- Would be worth it if deploying to constrained environments

### 🚀 Production Best Practices

1. **Use `.dockerignore` aggressively** (exclude: tests, docs, examples, migrations)
2. **Multi-stage builds always** (separates build-time from runtime deps)
3. **Minimal base images** (`*-slim` tags for Python/Node)
4. **Pin versions** (prevents unexpected dependency bloat)
5. **Use `--no-cache-dir`** for pip (already done ✓)
6. **Non-root user** for security (added ✓)

---

## What's Taking Up Space (Breakdown)

**Inside /usr/local/lib/python3.11/site-packages/:**

```
torch/                  ~700-900MB  (PyTorch kernels + libraries)
sentence_transformers/  ~200MB     (Transformer models + utils)
numpy/                  ~50MB      (Numerical computing)
scipy/                  ~150MB     (Scientific computing)
groq/                   ~5MB       (Small, just API client)
fastapi/                ~3MB       (Small, just web framework)
sqlalchemy/             ~8MB       (Small, just ORM)
[All other packages]    ~100MB     (Various utilities)
```

**Total: ~1.2GB in site-packages alone**

---

## Files Modified

✅ **backend/Dockerfile** - Multi-stage build pattern applied
✅ **backend/.dockerignore** - Enhanced with explicit exclusions

---

## Next Steps

1. **Test locally:**
   ```powershell
   cd backend
   docker build -t reg-backend:test .
   docker run -p 8000:8000 reg-backend:test
   # Verify app starts and works
   ```

2. **Deploy to Railway** - the optimized image will build faster

3. **Monitor build time** - should be faster due to layer caching

4. **If size still critical** - consider ONNX migration (Option B above)
