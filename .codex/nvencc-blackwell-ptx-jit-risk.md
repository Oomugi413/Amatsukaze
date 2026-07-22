# Blackwell GPU における NVEncC の PTX JIT 起動遅延リスク調査

## Codex チャット復元情報

- Codex Thread ID: `019f8385-9e16-71f1-adc5-1365420d8cb6`
- 対象リポジトリ: `/home/oomugi413/git/Amatsukaze`
- 調査日: 2026-07-21

## 調査目的

RTX 5070 Ti（compute capability 12.0 / `sm_120`）で Amatsukaze から NVEncC を使用した場合に、NVEncC 内蔵 CUDA コードの PTX JIT コンパイルによって起動が長時間停止するリスクがないか確認する。

本調査ではリポジトリ内のコード、設定、バイナリに変更を加えず、次の項目を確認した。

- Amatsukaze が導入する NVEncC のバージョンと入手元
- NVEncC バイナリのビルド時 CUDA バージョン
- バイナリに含まれる cubin / PTX の対象アーキテクチャ
- Amatsukaze から NVEncC への映像入力経路
- NVEncC が入力を消費しない場合の停止波及
- エンコーダ停止を検出するタイムアウトの有無
- CUDA JIT キャッシュの設定と永続化状況

## 結論

Amatsukaze でも、Blackwell GPU 上で NVEncC の PTX JIT による起動停止が発生するリスクがある。

現在の Dockerfile が導入する NVEncC 9.13 の公式 Debian バイナリは CUDA 11.2 でビルドされ、ネイティブ cubin の上限が `sm_86` である。RTX 5070 Ti の `sm_120` に対応する cubin を持たないため、実行時に `compute_86` PTX から `sm_120` 用 cubin を JIT コンパイルする必要がある。

NVEncC が JIT 中に stdin を消費しない場合、Amatsukaze の Y4M パイプ書き込みがブロックし、上流のフレームバッファも満杯になる。その結果、エンコードジョブ全体が長時間停止して見える。

Amatsukaze にはエンコーダの無進捗を短時間で異常終了させる監視は見つからなかった。JIT が正常に完了すれば、その後は通常のエンコードへ進む。一方、JIT 中もジョブの並列実行枠と割り当て済み GPU リソースを占有する。

## NVEncC バイナリの調査結果

### 現行 Dockerfile

`docker/Dockerfile` は実行段階のベースイメージとして CUDA 12.8.1 を使用している。

```dockerfile
FROM nvidia/cuda:12.8.1-base-ubuntu24.04 AS runtime
```

一方、NVEncC は `NVENCC_VER=9.13` として、本家の公式 Debian パッケージをそのまま取得している。

```dockerfile
ENV NVENCC_VER=9.13

wget https://github.com/rigaya/NVEnc/releases/download/${NVENCC_VER}/nvencc_${NVENCC_VER}_${ARCH}.deb -O nvencc.deb
apt-get install -y ./nvencc.deb
```

該当箇所:

- `docker/Dockerfile:199`
- `docker/Dockerfile:227`
- `docker/Dockerfile:289-291`

### 公式 NVEncC 9.13 Debian バイナリの実測

Dockerfile が取得する `nvencc_9.13_amd64.deb` を一時ディレクトリへ展開し、`--version`、`readelf`、`cuobjdump` で確認した。

| 項目 | 確認結果 |
|---|---:|
| NVEncC バージョン | 9.13 r3540 |
| ビルド時 CUDA | 11.2 |
| バイナリサイズ | 約176 MiB |
| `.nv_fatbin` | 約100 MiB |
| ネイティブ cubin | `sm_50`, `sm_52`, `sm_61`, `sm_75`, `sm_86` |
| PTX | `compute_50`, `compute_61`, `compute_75`, `compute_86` |
| ネイティブコード上限 | `sm_86` |

RTX 5070 Ti は `sm_120` であるため、このバイナリには直接実行できる互換 cubin がない。NVIDIA の仕様に従い、内蔵 PTX を実行時に JIT コンパイルする。

### CUDA 12.8 ベースイメージの効果

コンテナのベースイメージが CUDA 12.8.1 でも、CUDA 11.2 でビルド済みの NVEncC に `sm_120` cubinが追加されることはない。

また、Dockerfile で CUDA 12.5 の NVRTC / NPP ランタイムを導入しても、NVEncC 本体に埋め込まれた `.nv_fatbin` の内容は変化しない。

したがって、実行環境の CUDA ランタイム世代だけでは本問題を回避できない。NVEncC 自体を CUDA 12.8 以上でビルドし、バイナリへ `sm_120` cubin を含める必要がある。

### その他の Dockerfile

`docker/Dockerfile_2` は NVEncC 9.20 を CUDA 11.8 環境でソースビルドする。

```dockerfile
ENV NVENCC_VER=9.20
ENV NVENC_SOURCE_REF=9.20
```

CUDA 11.8 は `sm_120` cubinを生成できないため、この構成にも同じ根本リスクがある。

`docker/Dockerfile_1` と `docker/Dockerfile_original` も NVEncC 9.20 の公式 Debian パッケージを取得する構成であり、使用時には実際のバイナリのビルド時 CUDA バージョンと cubin 上限を確認する必要がある。

### 手動 Linux インストール

`doc/InstallLinux.md:213-218` の手順は GitHub Releases から最新の NVEncC Debian パッケージを取得する。

調査時点の最新版 9.25 の公式 Linux バイナリは CUDA 11.2 ビルドで、ネイティブコード上限は `sm_86` である。そのため、この手順で導入したバイナリも Blackwell GPU では PTX JIT が必要になる。

### 調査環境の NVEncC 9.25

調査環境の `/usr/bin/nvencc` も確認した。

| 項目 | 確認結果 |
|---|---:|
| NVEncC バージョン | 9.25 r3929 |
| ビルド時 CUDA | 11.2 |
| バイナリサイズ | 約469 MiB |
| `.nv_fatbin` | 約384 MiB |
| ネイティブコード上限 | `sm_86` |
| PTX 上限 | `compute_86` |

Amatsukaze の `NVEncPath` がこの `nvencc` を参照する環境では、同じ PTX JIT 条件になる。

## Amatsukaze の NVEncC 入力経路

Amatsukaze は NVEncC に入力ファイル名を直接渡さず、Y4M 形式の映像を標準入力へ送信する。

`Amatsukaze/TranscodeSetting.cpp:184-195` では、NVEncC の入力を次のように構成している。

```text
--y4m -i -
```

エンコーダプロセスは `Amatsukaze/Encoder.cpp:717-721` で起動され、その後にフレームの生成と送信が開始される。

単一パイプ処理では次の順序になる。

1. NVEncC プロセスを起動する。
2. フレーム送信用 `DataPumpThread` を起動する。
3. AviSynth フィルターからフレームを取得する。
4. 有界キューへフレームを投入する。
5. 送信スレッドが Y4M に変換して NVEncC の stdin へ書き込む。
6. 全フレーム送信後、stdin を閉じて NVEncC の終了を待つ。

主な該当箇所:

- `Amatsukaze/Encoder.cpp:720-721`: NVEncC プロセス起動
- `Amatsukaze/Encoder.cpp:866-874`: フレーム生成と有界キューへの投入
- `Amatsukaze/Encoder.cpp:884-886`: stdin クローズと終了待ち
- `Amatsukaze/Encoder.cpp:904-908`: フレーム送信スレッド
- `Amatsukaze/ProcessThread.cpp:38-45`: stdin への書き込み

## PTX JIT 中の停止波及

NVEncC がデバイス初期化中の PTX JIT に入ると、一定時間 stdin を読み取らない場合がある。

```text
NVEncC のデバイス初期化で PTX JIT
  → NVEncC が stdin を消費しない
  → Y4M の OS パイプが満杯になる
  → Amatsukaze のブロッキング write() が停止する
  → フレーム送信スレッドが停止する
  → DataPumpThread の有界キューが満杯になる
  → フィルター／フレーム生成側も待機する
  → エンコードジョブ全体が停止して見える
```

Linux の stdin 書き込みは `common/rgy_pipe_linux.cpp:215-228` の `write()` であり、タイムアウトのないブロッキング処理である。

```cpp
while (bytes_written < (ssize_t)dataSize) {
    ssize_t result = write(m_pipe.stdIn.h_write,
        (const char *)data + bytes_written,
        dataSize - bytes_written);
    // ...
}
```

Windows でも `common/rgy_pipe.cpp:215-223` の同期 `WriteFile()` を使用するため、NVEncC が入力を読まなければ同様に書き込みが待機する。

上流の `DataPumpThread` も `Amatsukaze/ProcessThread.h:71-95` で最大量に達すると条件変数待ちになる。

プロファイルの `NumEncodeBufferFrames` や並列パイプのバッファによって一定数のフレームは先行できるが、JIT が長時間続けば最終的には上流まで停止が伝播する。

## タイムアウトとジョブへの影響

NVEncC の終了待ちはタイムアウトなしである。

- Linux: `common/rgy_pipe_linux.cpp:332-341` の `waitpid(..., 0)`
- Windows: `common/rgy_pipe.cpp:311-322` の `WaitForSingleObject(..., INFINITE)`

サーバー側も `AmatsukazeServer/Server/TranscodeWorker.cs:1093-1097` で AmatsukazeCLI の終了と内部通信用タスクを待つ。

```csharp
await Task.WhenAll(
    p.WaitForExitAsync(),
    HostThread(pipes, ignoreResource));
```

無進捗時間を監視して NVEncC や AmatsukazeCLI を自動終了させる処理は確認できなかった。

このため、PTX JIT 中の挙動は次のようになる。

- JIT が完了すれば、そのままエンコードが開始される。
- JIT 中はエンコードジョブが停止して見える。
- ジョブの並列実行枠を占有する。
- Encode フェーズで割り当てられた GPU リソースを占有する。
- 複数の NVEncC を同時起動すると、複数ジョブが同時に JIT と待機へ入る可能性がある。
- ユーザーが停止と判断してキャンセルした場合、キャッシュ生成が完了しない可能性がある。
- キャッシュが利用できない環境では、次回起動時にも再発する可能性がある。

## CUDA JIT キャッシュ

リポジトリ内には次の設定がない。

- `CUDA_CACHE_PATH`
- `CUDA_CACHE_MAXSIZE`
- `CUDA_CACHE_DISABLE`
- `CUDA_MODULE_LOADING`
- ComputeCache 専用の永続ボリューム
- NVEncC 更新後の事前ウォームアップ処理

`docker/compose.sample.yml:19-30` のボリュームにも CUDA ComputeCache は含まれていない。

同じコンテナを単純に再起動する場合は writable layer にキャッシュが残る可能性があるが、コンテナの再作成、イメージ更新、実行ユーザー変更後の永続性は保証されない。また、実行ユーザーが既定のキャッシュディレクトリへ書き込めることも構成上明示されていない。

## リスク評価

| 使用構成 | 判定 | 理由 |
|---|---|---|
| 現行 Dockerfile の NVEncC 9.13 | 該当 | CUDA 11.2、ネイティブ上限 `sm_86` |
| Dockerfile_2 の NVEncC 9.20 | 該当 | CUDA 11.8 ビルド、`sm_120` を生成不可 |
| 最新公式 Debian NVEncC 9.25 | 該当 | CUDA 11.2、ネイティブ上限 `sm_86` |
| 手動導入した NVEncC | 条件付き | 使用バイナリのビルド CUDA と cubin 構成による |
| Windows版 NVEncC | 条件付き | 使用バイナリのビルド CUDA と cubin 構成による |
| CUDA 12.8 以上でビルドし `sm_120` cubin を含む NVEncC | 回避可能 | Blackwell 用ネイティブ cubin を直接実行できる |

根本原因の発生可能性は高い。特に空キャッシュ、NVEncC 更新直後、NVIDIA ドライバー更新後、コンテナ再作成後は注意が必要である。

一方、JIT が正常に完了する限りエンコード結果自体が破損する問題ではなく、主な影響は初回起動遅延と、その間のジョブ／GPUリソース占有である。

## 恒久対策候補

最も確実な対策は、NVEncC を CUDA 12.8 以上でビルドし、実際の配布バイナリに `sm_120` ネイティブ cubin を含めることである。

NVEncC 9.25 の Meson 定義には、CUDA 12.8 以上の場合に次の生成対象を追加する処理がある。

```text
arch=compute_120,code=[compute_120,sm_120]
```

ビルド環境の CUDA バージョン表示だけで判断せず、完成したバイナリを `cuobjdump` で確認する必要がある。

確認例:

```bash
nvencc --version
cuobjdump --list-elf "$(command -v nvencc)"
cuobjdump --list-ptx "$(command -v nvencc)"
```

## 短期対策候補

コード変更を伴わない短期対策として、次が考えられる。

1. Amatsukaze と同じ実行ユーザー、同じコンテナ、同じ NVEncC バイナリで事前エンコードを行う。
2. 実運用に近い AFS、deband、colorspace 等のオプションを使用して必要な JIT キャッシュを生成する。
3. `CUDA_CACHE_PATH` を書き込み可能な永続領域へ設定する。
4. Docker では ComputeCache の保存先をホストまたは名前付きボリュームへマウントする。
5. `CUDA_CACHE_MAXSIZE` を NVEncC の CUDA モジュール群を保持できる容量に設定する。
6. NVEncC または NVIDIA ドライバー更新後に、キュー処理開始前のウォームアップを行う。
7. ウォームアップ処理が完全に終了するまで中断しない。

単純なタイムアウト追加は、初回 JIT が数十秒から数分かかる可能性があるため、根本対策にはならない。

## 参照資料

- NVIDIA Blackwell Compatibility Guide  
  <https://docs.nvidia.com/cuda/blackwell-compatibility-guide/index.html>
- CUDA JIT cache environment variables  
  <https://docs.nvidia.com/cuda/cuda-programming-guide/05-appendices/environment-variables.html#jit-compilation>
- NVEncC 9.25 Meson definition  
  <https://github.com/rigaya/NVEnc/blob/9.25/meson.build#L107-L116>
- NVEnc Release Notes  
  <https://github.com/rigaya/NVEnc/blob/master/ReleaseNotes.md#925>

## 調査時の変更状況

本調査ではリポジトリ内のコード、設定、既存バイナリを変更していない。調査結果を保存するため、本 Markdown ファイルのみを `.codex` ディレクトリへ追加した。
