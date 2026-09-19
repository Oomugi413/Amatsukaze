# CUVID／DefaultのAvisynth画素形式対応

- Codex session ID: `019fb711-a128-7c80-b001-e68d766db6ae`
- 実施日: `2026-07-31`
- 対象リポジトリ: `/home/oomugi413/git/Amatsukaze`
- 対象プロファイル: `docker/profile/NVENC-HEVC-4K-1080p-23f-colormap_codex.profile`

## 背景

`NVENC-HEVC-4K-1080p-23f-colormap_codex.profile`でHEVCデコーダをCUVIDにすると、Avisynth処理中に次のエラーが発生していた。

```text
Avisynthフィルタでエラーが発生: not supported conversion.
```

プロファイルは`FilterOption=None`で、リサイズはNVEnc側に移している。NVEncオプションには次の設定が入っていることを確認した。

```text
--output-res 1920x1080 --vpp-resize libplacebo-ewa-lanczos
```

このプロファイル自体は変更していない。

## 実装した変更

### AMTSourceの出力ビット深度決定

`Amatsukaze/AMTSource.cpp`の`UpdateVideoInfo()`で、Avisynth側の出力形式をデコーダの形式ではなく入力ストリームの画素形式を基準に決めるよう変更した。

- 10bit入力はAvisynth側も10bitを基準にする
- DefaultのYUV420P10LEに対応する
- CUVIDのNV12、P010など、実際のAVFrame形式は`MakeFrame()`で出力形式へ変換する
- `codecCtx()->pix_fmt`と実際のAVFrame形式が異なる場合にも、実フレームのビット深度に合わせて変換関数を選択する

### 画素形式・ビット深度変換

`Amatsukaze/AMTSource.h`、`ConvertPix.cpp`、`ConvertPix.h`、`ConvertPixAVX2.cpp`を変更した。

- 8bit、10bit、12bit、P010相当の16bit格納形式に対応
- 8⇔10bit、8⇔12bit、10⇔12bit、16⇔8/10/12bitの変換関数を追加
- P010のようなNV12系インターリーブドUVにも対応
- 既存の16bit→10/12bit AVX2変換は維持
- 既存の`Convert2_16_to_12`の変換方向を修正
- 未対応の場合、入力画素形式とビット深度を含むエラーを表示するよう変更

画素変換はAvisynthへフレームを渡すAMTSource内のCPU処理であり、色空間変換やトーンマッピングそのものを無効化する変更ではない。

## 確認結果

次のコマンドを実行した。

```bash
git diff --check
docker compose -f docker/compose.yml build amatsukaze
```

- `git diff --check`: 成功
- Dockerビルド: 成功（終了コード0）
- C++本体`libAmatsukaze.so`を含むビルド: 成功
- C# Server／CLI／WebUIのビルド: 成功
- 生成イメージ名: `amatsukaze`
- ビルド時イメージID: `sha256:2dc8551218b0491117851a84647a70d4904a77d8fa15bdc32bc9e18e0182d5e2`

エンコードテストは実施していない。また、稼働中のコンテナの再起動・再作成も行っていない。

## CPU／GPU使用状況の確認

コンテナ内の`top`を確認した時点では、次の値だった。

```text
AmatsukazeCLI  210% CPU
nvencc         170% CPU
CPU全体        72% idle
```

同時点の`nvidia-smi`は次の値だった。

```text
GPU使用率       52%
Encoder使用率   11%
Decoder使用率   24%
VRAM使用量      8354 MiB / 16303 MiB
```

CUVID／Defaultの画素形式変換はCPUで行われる。Defaultで形式が一致する場合は主にCPUコピー、CUVIDのNV12/P010とAvisynth形式が異なる場合はCPUでビット深度・平面形式変換を行う。リサイズ、decimate、libplaceboトーンマッピング、HEVCエンコードはGPU側で処理する。

## 実行中コンテナへの反映

ビルド済みイメージを実行中コンテナへ反映する場合は、エンコードが実行されていないことを確認してから次を実行する。

```bash
docker compose -f docker/compose.yml up -d --force-recreate amatsukaze
```

