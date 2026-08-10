# RTX 50シリーズ向けNVEncC修正

- Codex session ID: `019f86fb-e9f2-79a2-bd81-49f5c7d89220`
- 対象リポジトリ: `/home/oomugi413/git/Amatsukaze`
- 対象ファイル: `docker/Dockerfile`
- NVEncCバージョン: `9.25.1`
- NVEncC取得元: `https://github.com/Oomugi413/NVEnc`
- CUDAバージョン: `13.3`

## 問題の概要

従来のNVEncC 9.25では、RTX 50シリーズ（Blackwell、compute capability 12.0）でデバイス初期化が長時間停止する問題が発生した。

その後の調査でNVEncC本体に問題があることが判明したため、Dockerイメージ内でNVEncCを独自ビルドする方式ではなく、修正版を含む`Oomugi413/NVEnc`のリリースパッケージを使用する方針へ変更した。

## 現在の対応

RTX50fixコミット`f03fb6e`で追加したNVEncC専用ビルドステージと関連処理は、すべて削除した。

現在のDockerfileは、RTX50fix以前と同じdebパッケージのインストール方式を使用し、NVEncCのバージョンと取得元を次のように変更している。

```dockerfile
ENV NVENCC_VER=9.25.1

RUN wget https://github.com/Oomugi413/NVEnc/releases/download/${NVENCC_VER}/nvencc_${NVENCC_VER}_${ARCH}.deb -O nvencc.deb \
    && apt-get install -y ./nvencc.deb \
    && rm ./nvencc.deb
```

使用するリリースは次のとおり。

- `https://github.com/Oomugi413/NVEnc/releases/tag/9.25.1`
- パッケージ: `nvencc_9.25.1_amd64.deb`
- SHA-256: `f941b7e026e95d76ecf1d1058e282a983173bd45dad3a225c470f7b0dda945ba`

## CUDA実行環境

NVEncC 9.25.1はNVENC API 13.0およびCUDA 13.3でビルドされているため、DockerのruntimeとNVRTC/NPPも同じ世代へ統一した。

```dockerfile
FROM nvidia/cuda:13.3.0-base-ubuntu24.04 AS runtime
```

導入するCUDAパッケージは次のとおり。

```text
cuda-nvrtc-13-3
cuda-nvrtc-dev-13-3
libnpp-13-3
```

確認した実際のパッケージバージョンは次のとおり。

- `cuda-nvrtc-13-3`: `13.3.33-1`
- `cuda-nvrtc-dev-13-3`: `13.3.33-1`
- `libnpp-13-3`: `13.1.2.81-1`

ホスト環境はNVIDIAドライバー`610.43.02`、CUDA UMD 13.3であり、コンテナのCUDA 13.3と整合している。

## 検証結果

次のコマンドでDockerイメージをビルドした。

```bash
cd /home/oomugi413/git/Amatsukaze/docker
docker compose build
```

ビルドは終了コード0で成功した。

- 生成イメージ: `amatsukaze`
- イメージID: `sha256:72531eabe0bcb600941b40fd3aeafb995f33c596488609d681e8f99064a19933`
- NVEncC: `9.25.1 (r3933)`
- NVENC API: `13.0`
- CUDA: `13.3`

Amatsukazeと同じY4M入力経路でH.264エンコードを実行し、120フレームすべてを終了コード0で処理した。

さらにNVRTCを使用する`--vpp-colorspace`を有効にしたテストでも、120フレームすべてを終了コード0で処理した。これにより、NVENCによるエンコードとCUDA 13.3のNVRTCフィルターがコンテナ内で動作することを確認した。

なお、TSをNVEncCへ直接渡して`--frames 300`で打ち切るテストでは、273フレーム処理後にNVDEC終了エラーとなった。これはNVDECを使用する直接入力の打ち切り終了経路で発生したもので、Amatsukazeが使用するY4M入力経路では正常に完走している。

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
