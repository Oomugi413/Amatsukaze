# CUDA / PTX問題に関するAmatsukaze側の変更

Codex session ID: `019fceed-24b2-7c83-ac28-4068c31a6bb0`

NVEnc側での原因調査・修正の経緯は、以下を参照する。

- [Oomugi413/NVEnc/.codex/CUDA13-PTXfix.md](https://github.com/Oomugi413/NVEnc/blob/master/.codex/CUDA13-PTXfix.md)

## Amatsukaze側の変更

主な変更対象は [docker/Dockerfile](../docker/Dockerfile) である。

- 実行イメージで使用するNVEncCをOomugi413版 `9.35` に変更した。
- 実行イメージをUbuntu 24.04 / CUDA 12.9へ統一した。
  - `nvidia/cuda:12.9.2-runtime-ubuntu24.04`
  - runtimeイメージに含まれるCUDA 12.9系NVRTC/NPPを使用する。
  - ベースイメージまたはNVEncCの更新時は、NVRTC/NPPとNVEncCのビルド時CUDAのバージョンの組み合わせに留意する。
- Ubuntu 24.04標準の `libplacebo-dev` はVulkan無効版のため、インストールしないようにした。
- libplacebo `7.360.1` を別のビルドステージでVulkan・shaderc有効の共有ライブラリとしてビルドし、実行イメージへ配置するようにした。
  - `libplacebo.so.360` を使用
  - `libvulkan1`、`libshaderc1`、`liblcms2-2`、`libxxhash0` を実行時依存として追加
  - Ubuntu 24.04では不要と判断したため、libplaceboのdovi/libdoviは無効化
  - `ldconfig` と `LD_LIBRARY_PATH` でビルドしたlibplaceboを優先

## 検証

NVEncC `9.30.2 (r4024)`を使用した過去の実エンコードでは、以下のTSでPTXエラーが発生しないことを確認した。この結果は問題修正時の記録である。

`/mnt/recording/20260805_[4K]運転席からの風景　ＪＲ鶴見線.ts`

- `vpp-colorspace`: NVRTC 12.9.86によるPTX生成、104フレーム出力に成功
- `vpp-libplacebo-tonemapping`: libplacebo 7.360.1によるVulkanデバイス作成、shadercコンパイル、104フレーム出力に成功
