# GDAL CLI (gdalwarp, gdal_translate, ogr2ogr, gdalinfo) ships in this base image.
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.9.3

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3-pip python3-dev build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# rasterio/geopandas wheels bundle their own GDAL; CLI tools come from the base.
RUN pip install --break-system-packages --upgrade pip \
    && pip install --break-system-packages -r requirements.txt

COPY . .

CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
