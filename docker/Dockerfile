# syntax=docker/dockerfile:1.6

# Amatsukaze Dockerfile
# Ubuntu 24.04 ベースで Amatsukaze を実行するためのマルチステージビルド
# デバッグモードとリリースモードの両方に対応

# NVEncCのlibplacebo/Vulkanフィルタ用共有ライブラリをビルドする段階。
# Ubuntu 24.04のlibplacebo-devはVulkan無効でビルドされているため、
# NVEncC 9.30.2と同じlibplacebo 7.360.1のVulkan対応版を使用する。
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

# ビルド段階
FROM ubuntu:24.04 AS builder

# 変数の定義
ARG UBUNTU_VERSION=24.04
ARG ARCH=amd64
ARG BUILD_MODE=release

# 環境変数の設定
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo
ENV UBUNTU_VERSION=${UBUNTU_VERSION}
ENV ARCH=${ARCH}
ENV BUILD_MODE=${BUILD_MODE}

# バージョン定義
ENV AVISYNTHCUDAFILTERS_VER=0.7.1
ENV AVISYNTH_VER=3.7.5
ENV YADIFMOD2_VER=0.2.8
ENV TIVTC_VER=v1.0.29
ENV NNEDI3_REV=baa68b771e52e6daf8820531b5172253d4a504ac
ENV MASKTOOLS_REV=8291927bf6956981a6412d353da8ca39d49c9d3a
ENV MVTOOLS_VER=2.7.46
ENV RGTOOLS_VER=1.2
ENV GPAC_VER=v2.4.0
ENV LSMASH_REV=18a9ed25c7ff79a7f4f4bf850c345c72179b8998
ENV CHAPTER_EXE_REV=32880d45f088e574285a101e6a49b032bb04f6ea
ENV JOIN_LOGO_SCP_VER=v5.1.1
ENV FDK_AAC_REV=d8e6b1a3aa606c450241632b64b703f21ea31ce3
ENV FDKAAC_VER=v1.0.6
ENV TSREADEX_VER=master-240517
ENV PSISIARC_VER=master-230324
ENV B24TOVTT_VER=master-220402

# ビルドツールのインストール
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    wget \
    tzdata \
    p7zip-full \
    nasm \
    cmake \
    meson \
    ninja-build \
    pkg-config \
    autoconf \
    automake \
    libtool \
    yasm \
    locales \
    software-properties-common \
    zlib1g \
    libz-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# AmatsukazeServer / WebUI のビルドに必要な .NET SDK をインストール
RUN add-apt-repository ppa:dotnet/backports \
    && apt-get update \
    && apt-get install -y dotnet-sdk-10.0 \
    && dotnet workload install wasm-tools --skip-manifest-update \
    && rm -rf /var/lib/apt/lists/*

# AviSynth+ のインストール
RUN wget https://github.com/rigaya/AviSynthCUDAFilters/releases/download/${AVISYNTHCUDAFILTERS_VER}/avisynth_${AVISYNTH_VER}-1_${ARCH}_Ubuntu${UBUNTU_VERSION}.deb -O avisynth.deb \
    && apt-get install -y ./avisynth.deb \
    && rm ./avisynth.deb

# C++17 標準ライブラリの追加
RUN apt-get update && apt-get install -y \
    libstdc++-12-dev \
    g++-12 \
    && rm -rf /var/lib/apt/lists/*

# Avisynth プラグインのビルドとインストール
WORKDIR /tmp/plugins

# yadif
RUN git clone --depth=1 --branch ${YADIFMOD2_VER} https://github.com/Asd-g/yadifmod2 \
    && cd yadifmod2 \
    && mkdir build && cd build && cmake .. \
    && make -j$(nproc) \
    && make install

# TIVTC
RUN git clone --depth=1 --branch ${TIVTC_VER} https://github.com/pinterf/TIVTC \
    && cd TIVTC/src \
    && sed -i '14a #include <cstdint>' common/fixedfonts.cpp \
    && cmake -DCMAKE_EXPORT_COMPILE_COMMANDS=1 -B build -S . \
    && cmake --build build -j $(nproc) \
    && cd build \
    && make install

# nnedi3
RUN git clone -b avsp --single-branch https://github.com/rigaya/NNEDI3.git \
    && cd NNEDI3 \
    && git checkout ${NNEDI3_REV} \
    && mkdir build && cd build && meson setup .. \
    && ninja \
    && ninja install

# masktools
RUN git clone https://github.com/pinterf/masktools.git \
    && cd masktools \
    && git checkout ${MASKTOOLS_REV} \
    && mkdir build && cd build && cmake .. \
    && make -j$(nproc) \
    && make install

# mvtools
RUN git clone --depth=1 --branch ${MVTOOLS_VER} https://github.com/pinterf/mvtools.git \
    && cd mvtools \
    && mkdir build && cd build && cmake .. \
    && make -j$(nproc) \
    && make install

# RgTools
RUN git clone --depth=1 --branch ${RGTOOLS_VER} https://github.com/pinterf/RgTools.git \
    && cd RgTools \
    && mkdir build && cd build && cmake .. \
    && make -j$(nproc) \
    && make install

# muxer のインストール（ビルドが必要なもののみ）
# mp4box
RUN git clone --depth=1 --branch ${GPAC_VER} https://github.com/gpac/gpac.git \
    && cd gpac \
    && ./configure --static-bin \
    && make -j$(nproc) \
    && make install

# L-SMASH
RUN git clone https://github.com/l-smash/l-smash.git \
    && cd l-smash \
    && git checkout ${LSMASH_REV} \
    && ./configure \
    && make -j$(nproc) \
    && make install

# CM/ロゴ解析ツール
# chapter_exe
RUN git clone https://github.com/rigaya/chapter_exe \
    && cd chapter_exe \
    && git checkout ${CHAPTER_EXE_REV} \
    && cd src \
    && make -j$(nproc) \
    && install -D -t /usr/local/bin chapter_exe

# join_logo_scp
RUN git clone --depth=1 --branch ${JOIN_LOGO_SCP_VER} https://github.com/yobibi/join_logo_scp \
    && cd join_logo_scp/src \
    && make \
    && install -D -t /usr/local/bin join_logo_scp

# 音声エンコーダ
# fdkaac
RUN git clone https://github.com/mstorsjo/fdk-aac.git \
    && cd fdk-aac \
    && git checkout ${FDK_AAC_REV} \
    && ./autogen.sh \
    && ./configure --disable-shared --prefix=$(pwd)/fdk-aac-libs \
    && make -j$(nproc) \
    && make install \
    && cd .. \
    && git clone --depth=1 --branch ${FDKAAC_VER} https://github.com/nu774/fdkaac.git \
    && cd fdkaac \
    && autoreconf -i \
    && PKG_CONFIG_PATH=../fdk-aac/fdk-aac-libs/lib/pkgconfig ./configure \
    && make -j$(nproc) \
    && make install

# tsreadex
RUN git clone --depth=1 --branch ${TSREADEX_VER} https://github.com/xtne6f/tsreadex.git \
    && cd tsreadex \
    && make -j$(nproc) \
    && install -D -t /usr/local/bin tsreadex

# psisiarc
RUN git clone --depth=1 --branch ${PSISIARC_VER} https://github.com/xtne6f/psisiarc.git \
    && cd psisiarc \
    && make -j$(nproc) \
    && install -D -t /usr/local/bin psisiarc

# b24tovtt
RUN git clone --depth=1 --branch ${B24TOVTT_VER} https://github.com/xtne6f/b24tovtt.git \
    && cd b24tovtt \
    && make -j$(nproc) \
    && install -D -t /usr/local/bin b24tovtt

# ビルド段階のクリーンアップ
RUN rm -rf /tmp/plugins \
    && rm -rf /var/cache/apt/* \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /usr/share/doc/* \
    && rm -rf /usr/share/man/* \
    && rm -rf /usr/share/locale/* \
    && rm -rf /usr/share/info/*

# Amatsukaze本体の依存ライブラリはソースより先にビルドし、Dockerレイヤーへキャッシュする。
# ソースコードだけを変更した通常の再ビルドでは、この重い依存ビルドは再実行されない。
COPY scripts/build_dep.sh scripts/mfx.diff /tmp/amatsukaze-build-scripts/scripts/
RUN mkdir -p /tmp/amatsukaze-deps /amt \
    && cd /tmp/amatsukaze-deps \
    && /tmp/amatsukaze-build-scripts/scripts/build_dep.sh /amt \
    && rm -rf /tmp/amatsukaze-deps /tmp/amatsukaze-build-scripts

ENV AMT_BASELIBS_DIR=/amt/baselibs
ENV AMT_PKGCONFIG_FFNK_DIR=/amt/ffmpeg_nekopanda/build/lib/pkgconfig
ENV AMT_PKGCONFIG_FF612_DIR=/amt/ffmpeg_612/build/lib/pkgconfig

# cloneしたローカル作業ツリーを唯一のAmatsukazeソースとして使用する。
# .gitは.dockerignoreで除外するため、バージョン生成用の最小Git履歴をコンテナ内で作る。
COPY . /src/Amatsukaze
RUN cd /src/Amatsukaze \
    && git init \
    && git config user.name "Amatsukaze Docker Build" \
    && git config user.email "docker-build@localhost" \
    && git add -A \
    && git commit -m "Local Docker build source" \
    && git tag 0.0.0 \
    && ./scripts/build.sh /opt/amatsukaze /tmp/amatsukaze-build \
    && ./scripts/install.sh /opt/amatsukaze \
    && rm -rf /tmp/amatsukaze-build /src/Amatsukaze/.git

# 実行段階
# NVEncC 9.30.2はCUDA 13.3でビルドし、実行時NVRTCは対応ドライバで使用できる12.9系に固定する。
FROM nvidia/cuda:13.3.0-base-ubuntu24.04 AS runtime

# 変数の定義（実行段階でも使用）
ARG UBUNTU_VERSION=24.04
ARG UBUNTU_NAME=noble
ARG ARCH=amd64
ARG BUILD_MODE=release
ARG ENABLE_FASTER_WHISPER=0
ARG ENABLE_VCEENCC=0
ARG SEVENZIP_VER=26.02
ARG SEVENZIP_PKG=7z2602
ARG SEVENZIP_ARCHIVE_SHA256=41aaba7b1235304ab5aa0624530c67ae829496cd29e875925271efdccc28c03e

# 環境変数の設定
ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Asia/Tokyo
ENV UBUNTU_VERSION=${UBUNTU_VERSION}
ENV UBUNTU_NAME=${UBUNTU_NAME}
ENV ARCH=${ARCH}
ENV BUILD_MODE=${BUILD_MODE}
ENV LANG=ja_JP.UTF-8
ENV LC_ALL=ja_JP.UTF-8
ENV LC_CTYPE=ja_JP.UTF-8

# NVEncC の libplacebo/Vulkan 系フィルタには graphics capability が必要。
# compose.yml 側で未指定でも NVIDIA Container Toolkit が Vulkan ICD を注入できるようにする。
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility,video,graphics
ENV VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_egl_icd.json

ENV QSVENCC_VER=8.28
ENV NVENCC_VER=9.33.1
ENV VCEENCC_VER=9.15
ENV AMDGPU_INSTALL_VER=25.35.1
ENV AMDGPU_INSTALL_DEB_VER=7.2.1.70201-1
ENV TSREPLACE_VER=0.20
ENV AVISYNTHCUDAFILTERS_VER=0.7.3
ENV AVISYNTH_VER=3.7.5
ENV FASTER_WHISPER_VER=r245.4

# 実行に必要なパッケージのみインストール（デバッグモードの場合はビルドツールも含める）
RUN apt-get update && apt-get install -y \
    gpg \
    ca-certificates \
    curl \
    wget \
    tzdata \
    software-properties-common \
    p7zip-full \
    && wget -qO - https://repositories.intel.com/gpu/intel-graphics.key | gpg --yes --dearmor --output /usr/share/keyrings/intel-graphics.gpg \
    && echo "deb [arch=amd64,i386 signed-by=/usr/share/keyrings/intel-graphics.gpg] https://repositories.intel.com/gpu/ubuntu ${UBUNTU_NAME} unified" \
      | tee /etc/apt/sources.list.d/intel-gpu-${UBUNTU_NAME}.list \
    && if [ "$ENABLE_VCEENCC" = "1" ]; then \
        wget https://repo.radeon.com/amdgpu-install/${AMDGPU_INSTALL_VER}/ubuntu/${UBUNTU_NAME}/amdgpu-install_${AMDGPU_INSTALL_DEB_VER}_all.deb -O amdgpu-install.deb \
        && apt-get install -y ./amdgpu-install.deb \
        && rm ./amdgpu-install.deb \
        && apt-get update \
        && amdgpu-install -y --usecase=opencl --opencl=rocr --no-dkms \
        && wget https://repo.radeon.com/amdgpu/6.4.4/ubuntu/pool/proprietary/a/amdgpu-pro-core/amdgpu-pro-core_25.10-2203192.24.04_all.deb \
        && wget https://repo.radeon.com/amdgpu/6.4.4/ubuntu/pool/proprietary/liba/libamdenc-amdgpu-pro/libamdenc-amdgpu-pro_25.10-2203192.24.04_amd64.deb \
        && wget https://repo.radeon.com/amdgpu/6.4.4/ubuntu/pool/proprietary/a/amf-amdgpu-pro/amf-amdgpu-pro_1.4.37-2203192.24.04_amd64.deb \
        && apt-get remove --purge -y amf-amdgpu-pro libamdenc-amdgpu-pro || true \
        && apt-get install -y --allow-downgrades \
            ./amdgpu-pro-core_25.10-2203192.24.04_all.deb \
            ./libamdenc-amdgpu-pro_25.10-2203192.24.04_amd64.deb \
            ./amf-amdgpu-pro_1.4.37-2203192.24.04_amd64.deb \
        && apt-mark hold amdgpu-pro-core libamdenc-amdgpu-pro amf-amdgpu-pro \
        && rm -f \
            ./amdgpu-pro-core_25.10-2203192.24.04_all.deb \
            ./libamdenc-amdgpu-pro_25.10-2203192.24.04_amd64.deb \
            ./amf-amdgpu-pro_1.4.37-2203192.24.04_amd64.deb \
        && if [ ! -e /lib/x86_64-linux-gnu/libOpenCL.so ] && [ -e /lib/x86_64-linux-gnu/libOpenCL.so.1 ]; then \
            ln -s /lib/x86_64-linux-gnu/libOpenCL.so.1 /lib/x86_64-linux-gnu/libOpenCL.so; \
        fi; \
    fi \
    && apt-get update \
    && apt-get install -y \
        gosu \
        git \
        xz-utils \
        locales \
        zlib1g \
        mkvtoolnix \
        opus-tools \
        libvulkan1 \
        liblcms2-2 \
        libshaderc1 \
        libxxhash0 \
        vulkan-tools \
        intel-media-va-driver-non-free intel-opencl-icd libigfxcmrt7 libmfx1 libmfx-gen1.2 libva-drm2 libva-x11-2 ocl-icd-opencl-dev \
        cuda-nvrtc-12-9 cuda-nvrtc-dev-12-9 libnpp-13-3 \
    && wget https://github.com/rigaya/QSVEnc/releases/download/${QSVENCC_VER}/qsvencc_${QSVENCC_VER}_${ARCH}.deb -O qsvencc.deb \
        && apt-get install -y ./qsvencc.deb \
        && rm ./qsvencc.deb \
    && wget https://github.com/Oomugi413/NVEnc/releases/download/${NVENCC_VER}/nvencc_${NVENCC_VER}_${ARCH}.deb -O nvencc.deb \
        && apt-get install -y ./nvencc.deb \
        && rm ./nvencc.deb \
    && if [ "$ENABLE_VCEENCC" = "1" ]; then \
        wget https://github.com/rigaya/VCEEnc/releases/download/${VCEENCC_VER}/vceencc_${VCEENCC_VER}_${ARCH}.deb -O vceencc.deb \
        && apt-get install -y ./vceencc.deb \
        && rm ./vceencc.deb; \
    fi \
    && wget https://github.com/rigaya/tsreplace/releases/download/${TSREPLACE_VER}/tsreplace_${TSREPLACE_VER}_${ARCH}.deb -O tsreplace.deb \
        && apt-get install -y ./tsreplace.deb \
        && rm ./tsreplace.deb \
    && if [ "$BUILD_MODE" = "debug" ]; then \
        apt-get install -y \
        software-properties-common \
        build-essential \
        nasm \
        cmake \
        meson \
        ninja-build \
        pkg-config \
        autoconf \
        automake \
        libtool \
        libz-dev; \
    fi \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && apt-get autoremove -y

# libplacebo-builderでビルドしたVulkan対応libplaceboを使用する。
# Ubuntu標準のVulkan無効版libplaceboはインストールしない。
COPY --from=libplacebo-builder /opt/libplacebo-root/usr/local/lib/x86_64-linux-gnu/ /usr/local/lib/x86_64-linux-gnu/
RUN printf '%s\n' /usr/local/lib/x86_64-linux-gnu > /etc/ld.so.conf.d/libplacebo.conf \
    && ldconfig \
    && test -s /usr/local/lib/x86_64-linux-gnu/libplacebo.so.360

# NVIDIA Container Toolkit が注入する nvidia_icd.json は libGLX_nvidia.so.0 を
# 参照する環境があり、ヘッドレスコンテナでは Vulkan ICD として初期化できない場合がある。
# libEGL_nvidia.so.0 参照の ICD を用意し、NVEncC/libplacebo ではこちらを使う。
RUN mkdir -p /etc/vulkan/icd.d \
    && printf '%s\n' '{"file_format_version":"1.0.1","ICD":{"library_path":"libEGL_nvidia.so.0","api_version":"1.3.0"}}' \
      > /etc/vulkan/icd.d/nvidia_egl_icd.json

# NVEncC の --vpp-colorspace / --vpp-libplacebo-* は Vulkan、libplacebo、NVRTC を実行時に使う。
# CUDA 13.3イメージ上で12.9系NVRTCを使うため、12.9のライブラリパスを動的リンカへ登録する。
# cuda-nvrtc-dev が通常は非バージョン付き symlink を提供するが、念のため補完する。
RUN set -eux; \
    CUDA_LIB="/usr/local/cuda-12.9/targets/x86_64-linux/lib"; \
    if [ -d "$CUDA_LIB" ]; then \
        if [ ! -e "$CUDA_LIB/libnvrtc.so" ]; then \
            found="$(find "$CUDA_LIB" -maxdepth 1 -name 'libnvrtc.so.*' -print -quit)"; \
            if [ -n "$found" ]; then ln -s "$(basename "$found")" "$CUDA_LIB/libnvrtc.so"; fi; \
        fi; \
        if [ ! -e "$CUDA_LIB/libnvrtc-builtins.so" ]; then \
            found="$(find "$CUDA_LIB" -maxdepth 1 -name 'libnvrtc-builtins.so.*' -print -quit)"; \
            if [ -n "$found" ]; then ln -s "$(basename "$found")" "$CUDA_LIB/libnvrtc-builtins.so"; fi; \
        fi; \
        printf '%s\n' "$CUDA_LIB" > /etc/ld.so.conf.d/cuda-nvrtc-12-9.conf; \
    fi; \
    ldconfig; \
    ldconfig -p | grep -E 'libvulkan|libplacebo|libnvrtc' || true

# タイムゾーンを確実に JST へ固定
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone

# 日本語ロケールの設定
RUN locale-gen ja_JP.UTF-8 \
    && locale-gen en_US.UTF-8 \
    && update-locale LANG=ja_JP.UTF-8

# .NET SDK 10.0 のインストール（デバッグモードの場合のみ）
RUN if [ "$BUILD_MODE" = "debug" ]; then \
        apt add-apt-repository ppa:dotnet/backports \
        && apt update \
        && apt install -y dotnet-sdk-10.0 \
        && rm -rf /var/lib/apt/lists/*; \
    fi

# AviSynth+/AvisynthCUDAFilters のインストール（実行段階でも必要）
RUN wget https://github.com/rigaya/AviSynthCUDAFilters/releases/download/${AVISYNTHCUDAFILTERS_VER}/avisynth_${AVISYNTH_VER}-1_${ARCH}_Ubuntu${UBUNTU_VERSION}.deb -O avisynth.deb \
    && apt-get install -y ./avisynth.deb \
    && rm ./avisynth.deb \
    && wget https://github.com/rigaya/AviSynthCUDAFilters/releases/download/${AVISYNTHCUDAFILTERS_VER}/avisynthcudafilters_${AVISYNTHCUDAFILTERS_VER}-1_${ARCH}_Ubuntu${UBUNTU_VERSION}.deb -O avisynthcudafilters.deb \
    && apt-get install -y ./avisynthcudafilters.deb \
    && rm ./avisynthcudafilters.deb

RUN if [ "$ENABLE_FASTER_WHISPER" = "1" ]; then \
        wget https://github.com/Purfview/whisper-standalone-win/releases/download/Faster-Whisper-XXL/Faster-Whisper-XXL_${FASTER_WHISPER_VER}_linux.7z -O faster-whisper.7z \
        && mkdir -p /opt /app/exe_files \
        && 7z x faster-whisper.7z -o/opt/ \
        && chmod 755 /opt/ \
        && ln -s /opt/Faster-Whisper-XXL /app/exe_files/Faster-Whisper-XXL \
        && rm faster-whisper.7z; \
    fi

# ライブラリパスの設定
ENV LD_LIBRARY_PATH=/usr/local/lib:/usr/local/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH

# 作業ディレクトリの設定
WORKDIR /app

# ディレクトリ構造の作成
RUN mkdir -p /app/bat /app/config /app/exe_files/plugins64 /app/recorded /app/logo /app/output /app/profile /app/temp

# SCRename.py
RUN git clone --depth 1 -b 0.04 https://github.com/rigaya/SCRenamePy.git tmp_SCRenamePy \
    && mkdir -p exe_files/SCRenamePy \
    && mv tmp_SCRenamePy/SCRename.* exe_files/SCRenamePy/ \
    && rm -rf tmp_SCRenamePy

RUN wget https://github.com/rigaya/AutoBuildForAviUtlPlugins/releases/download/auto-build-20260905-074217/x264_3223_amd64_linux.tar.xz -O x264.tar.xz \
    && wget https://github.com/rigaya/AutoBuildForAviUtlPlugins/releases/download/auto-build-20260905-074217/x265_4.3%2B24_amd64_linux.tar.xz -O x265.tar.xz \
    && wget https://github.com/rigaya/AutoBuildForAviUtlPlugins/releases/download/auto-build-20260905-074217/SvtAv1EncApp_4.2.0-107_amd64_linux_clang.tar.xz -O svt-av1.tar.xz \
    && wget https://github.com/rigaya/AutoBuildForAviUtlPlugins/releases/download/auto-build-20250907-045307/x262_20260901.tar.gz -O x262.tar.gz \
    && tar -xf x264.tar.xz -C /app/exe_files \
    && tar -xf x265.tar.xz -C /app/exe_files \
    && tar -xf svt-av1.tar.xz -C /app/exe_files \
    && tar -xf x262.tar.gz -C /app/exe_files \
    && rm x264.tar.xz x265.tar.xz svt-av1.tar.xz x262.tar.gz

# ビルド段階から必要なファイルをコピー
COPY --from=builder /usr/local/lib /usr/local/lib
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=builder /usr/lib/x86_64-linux-gnu /usr/lib/x86_64-linux-gnu

# ローカルソースからビルドしたAmatsukazeをインストール
COPY --from=builder /opt/amatsukaze/ /app/

# CUDAフィルタを含む実行段階の全パッケージが揃った後で、AviSynthプラグインへのリンクを作成する。
# 必須プラグインが欠けたイメージを生成しないよう、リンク先の存在もここで検証する。
RUN /app/scripts/install.sh /app \
    && for plugin in \
        KUtil.so KFM.so KNNEDI3.so KTGMC.so AvsCUDA.so mt_masktools.so \
        libmvtools2.so libmasktools2.so libnnedi3.so libtivtc.so libtdeint.so librgtools.so; do \
        test -e "/app/exe_files/plugins64/${plugin}" || exit 1; \
    done \
    && ls /app/exe_files/plugins64/libyadifmod2*.so >/dev/null 2>&1

# アーカイブ展開用 7-Zip CLI（Linux x64、静的リンク版）
RUN wget https://github.com/ip7z/7zip/releases/download/${SEVENZIP_VER}/${SEVENZIP_PKG}-linux-x64.tar.xz -O ${SEVENZIP_PKG}-linux-x64.tar.xz \
    && echo "${SEVENZIP_ARCHIVE_SHA256}  ${SEVENZIP_PKG}-linux-x64.tar.xz" | sha256sum -c - \
    && mkdir -p /app/exe_files/7z \
    && tar -xf ${SEVENZIP_PKG}-linux-x64.tar.xz -C /app/exe_files/7z 7zzs License.txt \
    && chmod 755 /app/exe_files/7z/7zzs \
    && rm ${SEVENZIP_PKG}-linux-x64.tar.xz

# for debug
#COPY Amatsukaze_Ubuntu24.04_r926.tar.xz /app
#RUN tar -xJf /app/Amatsukaze_Ubuntu24.04_r926.tar.xz -C /app \
#    && if [ -f /app/scripts/install.sh ]; then /app/scripts/install.sh; fi \
#    && rm /app/Amatsukaze_Ubuntu24.04_r926.tar.xz

# デバッグ用のシェルスクリプトを作成（デバッグモードの場合のみ）
RUN if [ "$BUILD_MODE" = "debug" ]; then \
        echo '#!/bin/bash' > /app/debug-build.sh && \
        echo 'cd /app/Amatsukaze-src' >> /app/debug-build.sh && \
        echo './scripts/build.sh /app build --debug' >> /app/debug-build.sh && \
        echo 'if [ -f /app/scripts/install.sh ]; then /app/scripts/install.sh; fi' >> /app/debug-build.sh && \
        chmod +x /app/debug-build.sh; \
    fi

# エントリーポイントスクリプトを作成
RUN cat <<'EOF' > /app/entrypoint.sh
#!/bin/bash
set -e
umask 022

DEFAULT_UID=${RUN_UID:-1000}; DEFAULT_GID=${RUN_GID:-1000};
if ! getent group "$DEFAULT_GID" >/dev/null 2>&1; then groupadd -g "$DEFAULT_GID" appgroup; fi

RENDER_GROUP=""
if [ -d /dev/dri ]; then
  ls -l /dev/dri/ || true
  if [ -c /dev/dri/renderD128 ]; then
    RENDER_GID=$(stat -c "%g" /dev/dri/renderD128 2>/dev/null || echo "")
    echo "RENDER_GID: $RENDER_GID"
    if [ -n "$RENDER_GID" ] && [ "$RENDER_GID" != "" ]; then
      RENDER_GROUP=$(getent group "$RENDER_GID" | cut -d: -f1 || true)
      if [ -z "$RENDER_GROUP" ]; then
        if getent group render >/dev/null 2>&1; then
          groupmod -o -g "$RENDER_GID" render
          RENDER_GROUP=render
        else
          groupadd -g "$RENDER_GID" render
          RENDER_GROUP=render
        fi
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
if [ -n "$RENDER_GROUP" ]; then GROUPS_TO_ADD+=("$RENDER_GROUP"); elif getent group render >/dev/null 2>&1; then GROUPS_TO_ADD+=("render"); fi
if [ ${#GROUPS_TO_ADD[@]} -gt 0 ]; then
  usermod -aG "$(IFS=,; echo "${GROUPS_TO_ADD[*]}")" "$(id -nu "${DEFAULT_UID}")"
fi
exec gosu "$DEFAULT_UID" "$@"
EOF
RUN sed -i 's/\r$//' /app/entrypoint.sh \
    && chmod +x /app/entrypoint.sh

# デフォルトコマンド（モードに応じて切り替え）
ENTRYPOINT ["./entrypoint.sh"]
CMD ["/bin/sh", "-c", "if [ \"$BUILD_MODE\" = \"debug\" ]; then exec /bin/bash; else exec ./AmatsukazeServer.sh; fi"]
