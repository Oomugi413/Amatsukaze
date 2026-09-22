# RTX 50シリーズ向けNVEncC修正

- Codex session ID: `019f86fb-e9f2-79a2-bd81-49f5c7d89220`
- 対象リポジトリ: `/home/oomugi413/git/Amatsukaze`
- 対象ファイル: `docker/Dockerfile`
- NVEncCバージョン: `9.35`
- NVEncC取得元: `https://github.com/Oomugi413/NVEnc`
- CUDAバージョン: `12.9`

## 問題の概要

従来のNVEncC 9.25では、RTX 50シリーズ（Blackwell、compute capability 12.0）でデバイス初期化が長時間停止する問題が発生した。

その後の調査でNVEncC本体に問題があることが判明したため、Dockerイメージ内でNVEncCを独自ビルドする方式ではなく、修正版を含む`Oomugi413/NVEnc`のリリースパッケージを使用する方針へ変更した。

## 現在の対応

RTX50fixコミット`f03fb6e`で追加したNVEncC専用ビルドステージと関連処理は、すべて削除した。

現在のDockerfileは、Oomugi413版NVEncCのdebパッケージをインストールする方式を使用し、NVEncCのバージョンと取得元を次のように指定している。

```dockerfile
ARG NVENCC_VER=9.35

RUN wget https://github.com/Oomugi413/NVEnc/releases/download/${NVENCC_VER}/nvencc_${NVENCC_VER}_${ARCH}.deb -O nvencc.deb \
    && apt-get install -y ./nvencc.deb \
    && rm ./nvencc.deb
```

使用するリリースは次のとおり。

- `https://github.com/Oomugi413/NVEnc/releases/tag/9.35`
- パッケージ: `nvencc_9.35_amd64.deb`（x86_64の場合）

## CUDA実行環境

Dockerの実行環境はUbuntu 24.04 / CUDA 12.9に統一している。Blackwell対応はOomugi413版NVEncCで行い、実行環境にはCUDA 12.9のNVRTC/NPPを使用する。

```dockerfile
FROM nvidia/cuda:12.9.2-runtime-ubuntu24.04
```

このruntimeイメージには必要なNVRTC/NPPが含まれる。ベースイメージまたはNVEncCを更新するときは、NVRTC/NPPとNVEncCのビルド時CUDAのバージョンの組み合わせに留意し、`nvencc --check-environment`と実エンコードで確認する。

確認したCUDA 12.9 runtimeのパッケージは次のとおり。

- `cuda-nvrtc-12-9`: `12.9.86-1`
- `libnpp-12-9`: `12.4.1.87-1`

## 検証結果

現行Dockerfileでは次の確認を行った。

```bash
docker buildx build --check -f docker/Dockerfile docker
docker buildx build --target libplacebo-builder -f docker/Dockerfile docker
```

Dockerfileの静的検査は警告なしで、Vulkan対応libplacebo 7.360.1のビルドステージも成功した。CUDA 12.9 runtimeにNVRTC/NPPが含まれることも確認した。NVEncCやCUDAの更新時は、実使用の想定されるCUDA/Nvidia Linux Open Driverとのバージョン相性を再確認する。

## 新しいイメージへの切り替え

ビルド済みイメージを現在のコンテナへ反映する場合は、実行中のエンコードがないことを確認してから次を実行する。

```bash
cd /home/oomugi413/git/Amatsukaze/docker
docker compose up -d --force-recreate amatsukaze
```

状態とログは次のコマンドで確認できる。

```bash
docker compose ps
docker compose logs --tail=100 amatsukaze
```

`docker compose restart`だけでは既存コンテナが以前のイメージを使い続けるため、新しいイメージへの切り替えには`--force-recreate`を使用する。

この変更ではコンテナの再作成および再起動は行っていない。
