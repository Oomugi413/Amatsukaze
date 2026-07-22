# Amatsukaze Docker/NVEnc 4K HLG -> SDR エンコード エラー整理

作業日: 2026-06-26

## 最終状態

最終的に `/home/oomugi413/git/Amatsukaze/docker/profile/NVENC-HEVC-4K-1080p-auto-basic.profile` で正常にエンコードできる状態になった。

現在の成功方向の要点は次の通り。

- Docker コンテナ内で NVEncC の `vulkan` / `libplacebo` / `nvrtc` が有効。
- `docker/compose.yml` で `NVIDIA_DRIVER_CAPABILITIES=compute,utility,video,graphics` を指定。
- `VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_egl_icd.json` を指定し、ヘッドレス環境でも Vulkan ICD が正しく初期化されるようにした。
- プロファイル側は AviSynth フィルタ経由を避けるため `FilterOption=None`。
- デコーダ指定は `Mpeg2Decoder=Default`, `H264Deocder=Default`, `HEVCDecoder=Default`。
- SDR 化は NVEncC の `--vpp-libplacebo-tonemapping` と `--vpp-resize libplacebo-ewa-lanczos` で行う。
- `--vpp-colorspace` は使用しない。

最終的な NVEnc オプションの方向性:

```text
-c hevc --profile main10 --output-depth 10 --qvbr 32 --multipass 2pass-full --ref 5 -b 5 --bref-mode middle --nonrefp --aq --aq-temporal --aq-strength 12 --lookahead 32 --audio-copy --colorrange limited --colormatrix bt709 --colorprim bt709 --transfer bt709 --output-res 1920x1080 --vpp-resize libplacebo-ewa-lanczos --vpp-libplacebo-tonemapping src_csp=hlg,dst_csp=sdr,src_max=1000,dst_max=203,gamut_mapping=relative,tonemapping_function=bt2446a,dst_pl_transfer=bt1886,dst_pl_colorprim=bt709
```

## 1. Linux ビルド時の `libjitterentropy.a` 不足

### 症状

`./scripts/build.sh $HOME/Amatsukaze` のリンク段階で失敗。

```text
/usr/bin/x86_64-linux-gnu-ld.bfd: -l:libjitterentropy.a が見つかりません
collect2: error: ld returned 1 exit status
```

リンク行では OpenSSL が静的リンクされ、`libssl.a` / `libcrypto.a` の private dependency として `libjitterentropy.a` が要求されていた。

### 原因

Linux 側の `meson.build` で OpenSSL を `static : true` として取得していたため、ディストリビューションの OpenSSL `.pc` が持つ `Libs.private` までリンク対象になり、環境に存在しない `libjitterentropy.a` を要求していた。

### 対処

`meson.build` の OpenSSL 依存を共有ライブラリリンクに変更した。

```meson
openssl_dep = dependency('openssl', required : true, static : false)
```

これにより OpenSSL の static private dependency に引きずられず、システムの共有 OpenSSL を使う。

## 2. NVEncC で `libplacebo` / Vulkan が使えない

### 症状

Docker ビルド後、NVEncC の libplacebo 系フィルタが使用できない。エンコード時にも Vulkan 初期化で失敗した。

代表的なログ:

```text
Failed to get device count from Vulkan interface.
y4m: failed to parse y4m header: .
failed to initialize file reader(s).
```

`y4m` のエラーは根本原因ではなく、NVEncC が先に落ちたため Amatsukaze 側の pipe/y4m 処理が後続で失敗したもの。

### 原因

コンテナ実行環境に NVEncC/libplacebo が必要とする実行時依存が不足していた。

- Vulkan runtime / ICD の問題。
- NVIDIA Container Toolkit の capabilities に `graphics` が含まれていない。
- libplacebo runtime がない、または NVEncC から見えない。
- NVRTC がない、または非バージョン付き `libnvrtc.so` を解決できない可能性。

### 対処

`docker/Dockerfile` と `docker/compose.yml` を `docker/compose.yml` 使用前提で修正した。

主な修正:

- runtime に `libvulkan1`, `vulkan-tools`, `libplacebo-dev` を追加。
- `cuda-nvrtc-12-5`, `cuda-nvrtc-dev-12-5`, `libnpp-12-5` を追加。
- `NVIDIA_DRIVER_CAPABILITIES=compute,utility,video,graphics` を設定。
- `VK_ICD_FILENAMES=/etc/vulkan/icd.d/nvidia_egl_icd.json` を設定。
- `libEGL_nvidia.so.0` 参照の Vulkan ICD JSON を作成。
- `libnvrtc.so` / `libnvrtc-builtins.so` の symlink fallback を追加。

検証:

```text
nvencc --check-environment
```

で以下を確認。

```text
vulkan     : yes
libplacebo : yes
nvrtc      : yes
```

## 3. `--vpp-colorspace` が `libnvrtc.so` を要求して失敗

### 症状

`/home/oomugi413/git/Amatsukaze/.codex/error4.txt` で確認した失敗。

```text
colorspace: --vpp-colorspace requires "libnvrtc.so", not available on your system.
Unsupported vpp filter type.
```

この時点のプロファイルは次のような NVEnc オプションを使用していた。

```text
--vpp-colorspace matrix=bt2020nc:bt709,colorprim=bt2020:bt709,transfer=bt2020-10:bt709,range=limited:limited
```

### 原因

NVEncC の `--vpp-colorspace` は NVRTC を要求する。Docker 側でも NVRTC の整備を行ったが、最終的にはこの変換を `--vpp-colorspace` に頼らない構成にする方が安定した。

また、対象は HLG (`arib-std-b67`) 入力であり、`transfer=bt2020-10:bt709` よりも HLG -> SDR のトーンマッピングとして明示した方が意図に合う。

### 対処

`--vpp-colorspace` を廃止し、libplacebo の tone mapping に置き換えた。

```text
--vpp-libplacebo-tonemapping src_csp=hlg,dst_csp=sdr,...
```

あわせて resize も NVEncC/libplacebo 側で行うようにした。

```text
--output-res 1920x1080 --vpp-resize libplacebo-ewa-lanczos
```

## 4. AviSynth フィルタ経由で `not supported conversion`

### 症状

`/home/oomugi413/git/Amatsukaze/.codex/error3.txt` および `error5.txt` で確認。

```text
AMT [error] Avisynthフィルタでエラーが発生: not supported conversion.
y4m: failed to parse y4m header: .
failed to initialize file reader(s).
```

この時の引数には `-f "/app/avscache/....avs"` が含まれており、Amatsukaze 側が AviSynth フィルタ経由で y4m を NVEncC に渡していた。

また、デコーダは次のような状態だった。

```text
デコーダ: MPEG2:CUVID H264:CUVID HEVC:CUVID
```

または一部だけ CUVID の状態。

### 原因

4K HLG HEVC 入力に対して、Amatsukaze 側の AviSynth フィルタ経由と CUVID デコーダ指定が組み合わさると、AviSynth -> y4m 出力時の pixel format / bit depth 変換で失敗するケースがあった。

実際に生成された AVS はほぼ素通しに近かったため、SDR 化やリサイズを AviSynth 側で行う必然性は低かった。

### 対処

NVEncC 側の VPP に処理を寄せ、Amatsukaze の AviSynth フィルタ指定を外した。

プロファイル側の主な修正:

```xml
<FilterOption>None</FilterOption>
<FilterPath/>
<PostFilterPath/>
<Mpeg2Decoder>Default</Mpeg2Decoder>
<H264Deocder>Default</H264Deocder>
<HEVCDecoder>Default</HEVCDecoder>
```

これにより `-f "/app/avscache/....avs"` と `--hevcdecoder CUVID` などがエンコード引数から消える。

注意点:

- 失敗済みキュー項目はプロファイル内容をスナップショットとして保持している場合がある。
- プロファイル修正後の確認は、既存失敗項目の単純再実行ではなく、新規キュー追加の方が確実。
- サーバーに確実に読み込ませるため、プロファイル編集後に `docker compose -f compose.yml restart amatsukaze` を実施した。

## 5. 対象 TS の `ffprobe` 結果に合わせた SDR 化

対象ファイル `/mnt/recording/20260626_test.ts` を `ffprobe` で確認した時点では、映像ストリームは次の形式だった。

```text
codec_name=hevc
profile=Main 10
pix_fmt=yuv420p10le
color_range=tv
color_space=bt2020nc
color_transfer=arib-std-b67
color_primaries=bt2020
r_frame_rate=60000/1001
```

ストリームは 2 本あり、主映像は 3840x2160、もう一方は 1920x1080。どちらも HLG / BT.2020 / limited range だった。

このため、SDR 化は次の方針にした。

- 入力: HLG / BT.2020 / limited
- 出力: SDR / BT.709 / limited
- HDR -> SDR の tone mapping は `bt2446a`
- 出力解像度は 1920x1080
- resize は `libplacebo-ewa-lanczos`

最終オプション:

```text
--colorrange limited --colormatrix bt709 --colorprim bt709 --transfer bt709 --output-res 1920x1080 --vpp-resize libplacebo-ewa-lanczos --vpp-libplacebo-tonemapping src_csp=hlg,dst_csp=sdr,src_max=1000,dst_max=203,gamut_mapping=relative,tonemapping_function=bt2446a,dst_pl_transfer=bt1886,dst_pl_colorprim=bt709
```

NVEncC の小さい y4m 入力テストでは、以下のように libplacebo が使われることを確認した。

```text
Vpp Filters    libplacebo-tonemapping
               resize(libplacebo-ewa-lanczos)
VUI            matrix:bt709,colorprim:bt709,transfer:bt709,range:limited
```

## 6. Docker 操作上の注意

今回の Docker Compose ファイルは以下。

```text
/home/oomugi413/git/Amatsukaze/docker/compose.yml
```

作業時は `docker/` ディレクトリで次のように指定する。

```sh
docker compose -f compose.yml build amatsukaze
docker compose -f compose.yml up -d --force-recreate amatsukaze
docker compose -f compose.yml restart amatsukaze
```

`docker compose build` 後も既存コンテナが古い環境のままだと、修正済みの Dockerfile が反映されない。必要に応じて `up -d --force-recreate` で作り直す。

## 7. まとめ

今回の失敗は複数の問題が重なっていた。

1. OpenSSL 静的リンクによる `libjitterentropy.a` 不足。
2. Docker runtime の Vulkan / libplacebo / NVRTC 整備不足。
3. `--vpp-colorspace` の NVRTC 依存。
4. AviSynth フィルタ経由と CUVID デコーダ指定による y4m 変換失敗。
5. HLG / BT.2020 入力に対する SDR 化オプションの不一致。

最終的には、Docker runtime を libplacebo/Vulkan 対応に整備し、プロファイルでは AviSynth フィルタと CUVID 指定を外し、NVEncC/libplacebo で HLG -> SDR / 1080p resize を行う構成にすることで解決した。
