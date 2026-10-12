# Mapterhorn の pipelines を手元で動かすための環境（自治体 DEM の検証用）
# pipelines/README.md の Requirements（gdal, uv, unzip, un7z）に合わせる
FROM ghcr.io/osgeo/gdal:ubuntu-small-3.10.3

RUN apt-get update \
 && apt-get install -y --no-install-recommends curl unzip p7zip-full ca-certificates python3-venv \
 && rm -rf /var/lib/apt/lists/*

COPY --from=ghcr.io/astral-sh/uv:0.7.8 /uv /uvx /usr/local/bin/

# uv の仮想環境はマウントしたクローンの外に置く（クローンを汚さない）
ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    UV_CACHE_DIR=/opt/uv-cache

COPY pyproject.toml uv.lock /opt/pipelines/
RUN cd /opt/pipelines && uv sync --frozen --no-install-project

WORKDIR /work
