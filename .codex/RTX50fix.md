# RTX 50シリーズ向けNVEncC修正

- Codex session ID: `019f86fb-e9f2-79a2-bd81-49f5c7d89220`
- 対象リポジトリ: `/home/oomugi413/git/Amatsukaze`
- 対象ファイル: `docker/Dockerfile`
- NVEncCバージョン: `9.25`

## 問題の概要

RTX 50シリーズ（Blackwell、compute capability 12.0 / `sm_120`）に対し、CUDA 11.2でビルドされたNVEncC 9.25の配布バイナリは、ネイティブGPUコードを最大`sm_86`までしか含んでいなかった。

対応するcubinがない環境では、CUDAドライバーが起動時にPTXを対象GPU向けへJITコンパイルする。NVEncC 9.25はCUDAフィルターの増加によってJIT対象が大きく、CUDAキャッシュが空の場合にはデバイス初期化が長時間停止しているように見える可能性がある。

調査では処理が`libnvidia-ptxjitcompiler.so`内にあり、`cudaStreamCreateWithFlags()`から呼ばれる`NVEncCore::InitDevice()`の途中であることを確認した。この時点ではNVENCセッション初期化や実際の映像エンコードには到達していない。

既存のCUDA JITキャッシュがある場合には同じバイナリでも短時間で開始できるため、NVEncCのエンコード機能自体の故障ではなく、未対応アーキテクチャ向けの初回JITが原因と判断した。

## 対応方針

配布debのNVEncCをインストールする方式をやめ、Dockerイメージのビルド中にNVEncC 9.25をCUDA 12.8.1でソースからビルドするようにした。

生成対象のGPUアーキテクチャは、NVEncC 9.25のMeson定義にある次の3種類へ限定した。

- `compute_75` / `sm_75`（Turing）
- `compute_86` / `sm_86`（Ampere）
- `compute_120` / `sm_120`（Blackwell）

旧世代向けの`compute_50`と`compute_61`は、NVEncCの`meson.build`からビルド時に削除する。削除前後を`grep`で検査し、NVEncC側の定義変更によって想定外の状態になった場合はDockerビルドを失敗させる。

## Dockerfileの変更

### NVEncC専用ビルドステージ

`nvidia/cuda:12.8.1-devel-ubuntu24.04`を使用する`nvencc-builder`ステージを追加した。

このステージでは次を行う。

1. NVEncCのビルド依存パッケージを導入する。
2. `libdovi`と`libhdr10plus`のビルドに必要なRustおよび`cargo-c`を導入する。
3. rigaya/NVEncの`9.25`タグをサブモジュール込みで取得する。
4. `compute_50`と`compute_61`のMeson定義を削除する。
5. CUDA 12.8.1を使用してNVEncCをビルドする。
6. `/opt/nvencc/bin/nvencc`へインストールする。
7. `cuobjdump --list-elf`で完成バイナリに`sm_75`、`sm_86`、`sm_120`が含まれることを検証する。

### 並列ビルド数

NVEncCの並列ビルド数を次のDocker build引数で4ジョブに固定した。

```dockerfile
ARG NVENC_BUILD_JOBS=4
```

実際のコンパイルでは次のように使用する。

```dockerfile
meson compile -C build -j"${NVENC_BUILD_JOBS}"
```

### runtimeステージ

runtimeステージではNVEncCの配布debを取得せず、`nvencc-builder`で生成したバイナリを使用する。

```dockerfile
COPY --from=nvencc-builder /opt/nvencc/bin/nvencc /usr/local/bin/nvencc
RUN ln -sf /usr/local/bin/nvencc /usr/bin/nvencc
```

ソースビルド版NVEncCが使用する共有ライブラリを満たすため、runtimeパッケージに`ffmpeg`と`libass9`も追加した。

## 検証

`docker`ディレクトリで、強制オプションを付けずに次を実行した。

```bash
docker compose build
```

デフォルトのComposeビルドでNVEncCステージの再ビルドが実行されたため、`--no-cache`などを使った追加の強制再ビルドは行っていない。

Mesonのログでは生成対象が次のとおりであることを確認した。

```text
--generate-code arch=compute_75,code=[compute_75,sm_75]
--generate-code arch=compute_86,code=[compute_86,sm_86]
--generate-code arch=compute_120,code=[compute_120,sm_120]
```

NVEncCのコンパイルは`-j 4`で実行され、NVEncCビルドステージは約12分16秒で完了した。Docker Compose全体のビルドは終了コード0で成功した。

- 生成イメージ: `amatsukaze`
- イメージID: `sha256:b4b7aa323179e106529a9a893b502d0cb0d505f20ca8c8d0ad49e64c6c2e9ec7`

ローカルに置かれている未修正版NVEncCは動作確認に使用していない。

## 検証方法に関する注意

完成したNVEncCへ`cuobjdump --list-elf`を実行すると、静的リンクされたCUDA/NPPライブラリ由来の旧アーキテクチャが列挙される場合がある。このため、完成バイナリ全体に`sm_50`や`sm_61`が一切ないことを条件にすると、NVEncC自身の生成対象が正しくても誤って失敗する。

現在は次の組み合わせで検証している。

- NVEncCの`meson.build`から`compute_50`と`compute_61`が削除されたことを直接確認する。
- 完成バイナリに必要な`sm_75`、`sm_86`、`sm_120`が存在することを確認する。

## 新しいイメージへの切り替え

利用者の都合のよいタイミングで次を実行する。

```bash
cd /home/oomugi413/git/Amatsukaze/docker
docker compose up -d --force-recreate amatsukaze
```

状態と起動ログは次で確認できる。

```bash
docker compose ps
docker compose logs --tail=100 amatsukaze
```

`docker compose restart`だけでは既存コンテナが従来のイメージを使い続けるため、新しいビルド結果への切り替えには`docker compose up -d --force-recreate amatsukaze`を使用する。

この調査・修正作業ではコンテナの再作成および再起動は実施していない。
