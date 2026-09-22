# syntax=docker/dockerfile:1.6

# Oomugi413版NVEncCのlibplacebo/Vulkanフィルタ用共有ライブラリをビルドする段階。
# Ubuntu 24.04のlibplacebo-devはVulkan無効でビルドされているため、
# libplacebo 7.360.1のVulkan対応版を使用する。
FROM ubuntu:24.04 AS libplacebo-builder

ARG LIBPLACEBO_VER=7.360.1

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        ca-certificates \
        git \
        liblcms2-dev \
        libshaderc-dev \
        libvulkan-dev \
        libxxhash-dev \
        meson \
        ninja-build \
        pkg-config \
    && git clone --depth=1 --branch "v${LIBPLACEBO_VER}" --recursive \
        https://code.videolan.org/videolan/libplacebo.git /tmp/libplacebo \
    && meson setup /tmp/libplacebo/build /tmp/libplacebo \
        --buildtype=release \
        --prefix=/usr/local \
        --libdir=lib/x86_64-linux-gnu \
        -Ddefault_library=shared \
        -Dprefer_static=false \
        -Dd3d11=disabled \
        -Ddemos=false \
        -Dglslang=disabled \
        -Dlcms=enabled \
        -Ddovi=disabled \
        -Dlibdovi=disabled \
        -Dopengl=disabled \
        -Dshaderc=enabled \
        -Dtests=false \
        -Dvulkan=enabled \
        -Dxxhash=enabled \
    && meson compile -C /tmp/libplacebo/build \
    && DESTDIR=/opt/libplacebo-root meson install -C /tmp/libplacebo/build \
    && test -f /opt/libplacebo-root/usr/local/lib/x86_64-linux-gnu/libplacebo.so.360 \
    && rm -rf /var/lib/apt/lists/* /tmp/libplacebo

# 配布アーカイブを使用するLinuxコンテナ。
# runtimeイメージにCUDA 12.9のNVRTCとNPPが含まれるため、別途導入しない。
FROM nvidia/cuda:12.9.2-runtime-ubuntu24.04

ARG ARCH=amd64
ARG UBUNTU_NAME=noble
ARG ENABLE_VCEENCC=0
ARG QSVENCC_VER=8.30
ARG NVENCC_VER=9.35
ARG VCEENCC_VER=9.17
ARG AMDGPU_INSTALL_VER=25.35.1
ARG AMDGPU_INSTALL_DEB_VER=7.2.1.70201-1

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo
ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8
ENV LC_CTYPE=ja_JP.UTF-8
ENV PATH="/app/exe_files:$PATH"

# NVEncCのlibplacebo/Vulkan系フィルタにはgraphics capabilityが必要。
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,video,graphics
ENV VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_egl_icd.json

# 同梱されないPythonとGPU用の実行時依存を導入する
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates curl wget gpg tzdata locales gosu python3 xz-utils \
    && wget -qO - https://repositories.intel.com/gpu/intel-graphics.key \
        | gpg --yes --dearmor --output /usr/share/keyrings/intel-graphics.gpg \
    && echo "deb [arch=amd64,i386 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu $UBUNTU_NAME unified" \
        > /etc/apt/sources.list.d/intel-gpu-$UBUNTU_NAME.list \
    && apt-get update \
    && apt-get install -y --no-install-recommends \
        intel-media-va-driver-non-free intel-opencl-icd libigfxcmrt7 \
        libmfx1 libmfx-gen1.2 libva-drm2 libva-x11-2 ocl-icd-libopencl1 \
        libvulkan1 liblcms2-2 libshaderc1 libxxhash0 vulkan-tools \
    && wget -q "https://github.com/rigaya/QSVEnc/releases/download/${QSVENCC_VER}/qsvencc_${QSVENCC_VER}_${ARCH}.deb" -O /tmp/qsvencc.deb \
    && apt-get install -y --no-install-recommends /tmp/qsvencc.deb \
    && wget -q "https://github.com/Oomugi413/NVEnc/releases/download/${NVENCC_VER}/nvencc_${NVENCC_VER}_${ARCH}.deb" -O /tmp/nvencc.deb \
    && apt-get install -y --no-install-recommends /tmp/nvencc.deb \
    && if [ ! -e /lib/x86_64-linux-gnu/libOpenCL.so ] && [ -e /lib/x86_64-linux-gnu/libOpenCL.so.1 ]; then \
        ln -s /lib/x86_64-linux-gnu/libOpenCL.so.1 /lib/x86_64-linux-gnu/libOpenCL.so; \
    fi \
    && if [ "$ENABLE_VCEENCC" = "1" ]; then \
        wget -q "https://repo.radeon.com/amdgpu-install/${AMDGPU_INSTALL_VER}/ubuntu/${UBUNTU_NAME}/amdgpu-install_${AMDGPU_INSTALL_DEB_VER}_all.deb" -O /tmp/amdgpu-install.deb \
        && apt-get update \
        && apt-get install -y --no-install-recommends software-properties-common /tmp/amdgpu-install.deb \
        && amdgpu-install -y --usecase=opencl --opencl=rocr --no-dkms \
        && wget -q https://repo.radeon.com/amdgpu/6.4.4/ubuntu/pool/proprietary/a/amdgpu-pro-core/amdgpu-pro-core_25.10-2203192.24.04_all.deb -O /tmp/amdgpu-pro-core.deb \
        && wget -q https://repo.radeon.com/amdgpu/6.4.4/ubuntu/pool/proprietary/liba/libamdenc-amdgpu-pro/libamdenc-amdgpu-pro_25.10-2203192.24.04_amd64.deb -O /tmp/libamdenc-amdgpu-pro.deb \
        && wget -q https://repo.radeon.com/amdgpu/6.4.4/ubuntu/pool/proprietary/a/amf-amdgpu-pro/amf-amdgpu-pro_1.4.37-2203192.24.04_amd64.deb -O /tmp/amf-amdgpu-pro.deb \
        && (apt-get remove --purge -y amf-amdgpu-pro libamdenc-amdgpu-pro || true) \
        && apt-get install -y --allow-downgrades \
            /tmp/amdgpu-pro-core.deb /tmp/libamdenc-amdgpu-pro.deb /tmp/amf-amdgpu-pro.deb \
        && apt-mark hold amdgpu-pro-core libamdenc-amdgpu-pro amf-amdgpu-pro \
        && wget -q "https://github.com/rigaya/VCEEnc/releases/download/${VCEENCC_VER}/vceencc_${VCEENCC_VER}_${ARCH}.deb" -O /tmp/vceencc.deb \
        && apt-get install -y --no-install-recommends /tmp/vceencc.deb \
        && rm -f /tmp/amdgpu-install.deb /tmp/amdgpu-pro-core.deb \
            /tmp/libamdenc-amdgpu-pro.deb /tmp/amf-amdgpu-pro.deb /tmp/vceencc.deb; \
    fi \
    && locale-gen ja_JP.UTF-8 en_US.UTF-8 \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo "$TZ" > /etc/timezone \
    && rm -f /tmp/qsvencc.deb /tmp/nvencc.deb \
    && rm -rf /var/lib/apt/lists/*

# Vulkan対応libplaceboを実行イメージへ配置する。
COPY --from=libplacebo-builder /opt/libplacebo-root/usr/local/lib/x86_64-linux-gnu/ /usr/local/lib/x86_64-linux-gnu/
RUN printf '%s\n' /usr/local/lib/x86_64-linux-gnu > /etc/ld.so.conf.d/libplacebo.conf \
    && ldconfig \
    && test -s /usr/local/lib/x86_64-linux-gnu/libplacebo.so.360

# NVIDIA Container Toolkitが注入するICDは、ヘッドレスコンテナで
# libGLX_nvidia.so.0を初期化できない場合があるため、EGL経由のICDを使用する。
RUN mkdir -p /etc/vulkan/icd.d \
    && printf '%s\n' '{"file_format_version":"1.0.1","ICD":{"library_path":"libEGL_nvidia.so.0","api_version":"1.3.0"}}' \
      > /etc/vulkan/icd.d/nvidia_egl_icd.json

# Amatsukaze本体を展開する
ARG AMATSUKAZE_ARCHIVE=
ARG AMATSUKAZE_CACHE_BUST=
# アーカイブ未指定時にもCOPYを成立させるため、Dockerfileは常にコピーする
COPY Dockerfile ${AMATSUKAZE_ARCHIVE} /build-context/
RUN : "$AMATSUKAZE_CACHE_BUST" \
    && mkdir -p /app \
    && if [ -n "$AMATSUKAZE_ARCHIVE" ]; then \
        tar -xf "/build-context/$AMATSUKAZE_ARCHIVE" -C /app; \
    else \
        ARCHIVE_URL=$(curl -fsSL https://api.github.com/repos/Oomugi413/Amatsukaze/releases/latest \
            | sed -n 's/.*"browser_download_url":[[:space:]]*"\([^"]*\.tar\.xz\)".*/\1/p' \
            | grep 'Amatsukaze_linux_.*_x64\.tar\.xz' | head -1) \
        && test -n "$ARCHIVE_URL" \
        && curl -fL --retry 3 "$ARCHIVE_URL" | tar -xJ -C /app; \
    fi \
    && grep -Fq '"complete":true' /app/basepkg-manifest.json \
    && rm -rf /build-context \
    && mkdir -p /app/bat /app/config /app/recorded /app/logo /app/output /app/profile /app/temp

# Faster-Whisper-XXLを展開する
ARG ENABLE_FASTER_WHISPER=0
ARG FASTER_WHISPER_VER=r245.4
RUN if [ "$ENABLE_FASTER_WHISPER" = "1" ]; then \
        wget -q "https://github.com/Purfview/whisper-standalone-win/releases/download/Faster-Whisper-XXL/Faster-Whisper-XXL_${FASTER_WHISPER_VER}_linux.7z" -O /tmp/faster-whisper.7z \
        && mkdir -p /opt \
        && /app/exe_files/7z/7zzs x /tmp/faster-whisper.7z -o/opt/ \
        && chmod 755 /opt/Faster-Whisper-XXL/faster-whisper-xxl \
        && ln -s /opt/Faster-Whisper-XXL /app/exe_files/Faster-Whisper-XXL \
        && rm -f /tmp/faster-whisper.7z; \
    fi

WORKDIR /app

# 起動時にホストのUIDとGIDへ合わせる
RUN cat <<'ENTRYPOINT_SCRIPT' > /app/entrypoint.sh && chmod +x /app/entrypoint.sh
#!/bin/bash
set -e
umask 022

DEFAULT_UID=${RUN_UID:-1000}
DEFAULT_GID=${RUN_GID:-1000}
if ! getent group "$DEFAULT_GID" >/dev/null 2>&1; then groupadd -g "$DEFAULT_GID" appgroup; fi

RENDER_GROUP=""
if [ -d /dev/dri ]; then
    ls -l /dev/dri/ || true
    if [ -c /dev/dri/renderD128 ]; then
        RENDER_GID=$(stat -c "%g" /dev/dri/renderD128 2>/dev/null || echo "")
        echo "RENDER_GID: $RENDER_GID"
        if [ -n "$RENDER_GID" ]; then
            RENDER_GROUP=$(getent group "$RENDER_GID" | cut -d: -f1 || true)
            if [ -z "$RENDER_GROUP" ]; then
                if getent group render >/dev/null 2>&1; then
                    groupmod -o -g "$RENDER_GID" render
                else
                    groupadd -g "$RENDER_GID" render
                fi
                RENDER_GROUP=render
            fi
        fi
    fi
fi

if ! getent passwd "$DEFAULT_UID" >/dev/null 2>&1; then useradd -u "$DEFAULT_UID" -g "$DEFAULT_GID" -m -s /bin/bash appuser; fi
chown -R --no-dereference "$DEFAULT_UID:$DEFAULT_GID" /app
if [ -d /opt/Faster-Whisper-XXL ]; then
    find /opt/Faster-Whisper-XXL -type d -exec chown "$DEFAULT_UID:$DEFAULT_GID" {} +
    chmod ugo+rx /opt/Faster-Whisper-XXL/faster-whisper-xxl
fi
GROUPS_TO_ADD=()
if getent group video >/dev/null 2>&1; then GROUPS_TO_ADD+=("video"); fi
if [ -n "$RENDER_GROUP" ]; then
    GROUPS_TO_ADD+=("$RENDER_GROUP")
elif getent group render >/dev/null 2>&1; then
    GROUPS_TO_ADD+=("render")
fi
if [ ${#GROUPS_TO_ADD[@]} -gt 0 ]; then
    usermod -aG "$(IFS=,; echo "${GROUPS_TO_ADD[*]}")" "$(id -nu "$DEFAULT_UID")"
fi
if [ -x /app/exe_files/AmatsukazeDockerConfigFix ]; then
    gosu "$DEFAULT_UID" /app/exe_files/AmatsukazeDockerConfigFix \
        /app/config/AmatsukazeServer.xml /app/exe_files || \
        echo "警告: Docker用実行ファイル設定の補正に失敗しました" >&2
fi
exec gosu "$DEFAULT_UID" "$@"
ENTRYPOINT_SCRIPT

ENTRYPOINT ["./entrypoint.sh"]
CMD ["./AmatsukazeServer.sh"]
