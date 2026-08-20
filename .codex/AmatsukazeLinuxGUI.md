# Amatsukaze Linux簡易GUI 設計・実装計画

- 作成日: 2026-08-20
- 状態: 初版実装済み（P0起動・REST読み取り確認済み、実キュー追加結合試験待ち）
- 対象: Linux版Amatsukazeを同一端末から操作する簡易GUI
- 最優先動作環境: この開発PC（Ubuntu 26.04 LTS / GNOME Shell 50.1 / Wayland）

## 1. 結論

Linux GUIは、Windows版WPF GUIの直接移植ではなく、**GTK 4とPyGObjectで新規に作成するネイティブWayland対応のクライアント専用GUI**とする。

初版は次の構成を採用する。

- GUIは `AmatsukazeLinuxGUI/` 以下に独立したPython 3/PyGObjectアプリケーションとして配置する。
- GUIからサーバーを内包・直接参照せず、Python標準ライブラリから既存REST APIを呼び出す。
- GTKのGDK Waylandバックエンドを使用し、P0環境の試験では `GDK_BACKEND=wayland` を指定してXWaylandへフォールバックしていないことを保証する。
- 最低限、現在のWebUIの「タスク追加」画面と同等の設定を行えるようにする。
- Linuxのファイルマネージャーから入力ファイルをドラッグ＆ドロップできるようにする。
- Windows版と同様に、複数の入力ファイルを1つの `AddQueueRequest` にまとめ、同一の出力先・プロファイル・優先度・処理モード・追加時バッチで一括追加できるようにする。
- 初版は、GUIと `AmatsukazeServerCLI` が**同一ホストで動作し、入力・出力を同じ絶対パスで参照できる構成**を正式対応とする。同一パスのbind mountを使用するDocker版も含む。
- GUI起動時点でサーバーが起動済みであることを前提とする。サーバーの自動起動は後続機能とする。
- 実装本体、画像、ランチャー原本、GUI固有テストは原則としてすべて `AmatsukazeLinuxGUI/` に置く。他フォルダーの変更はビルド、配布、ドキュメントへの最小限の追記に限定する。
- 可能な限り多くのLinux環境で動く構成を維持するが、設計判断、実装順序、障害修正、リリース判定ではこの開発PCでの動作を最優先する。

この構成なら、Windows専用コードを持ち込まず、既存サーバーのキュー追加処理と入力検証を再利用できる。WebUIで不可能だった「ブラウザー外から渡されたローカル絶対パスの取得」も、デスクトップアプリのドラッグ＆ドロップAPIで実現できる。

### 1.1 対象環境の優先順位

動作環境は次の優先順位で扱う。

| 優先度 | 環境 | 扱い |
|---|---|---|
| P0 | この開発PC: Ubuntu 26.04 LTS、GNOME Shell 50.1、Wayland、x64 | 設計・実装・手動試験・リリース判定の基準。失敗時はリリース不可 |
| P1 | 同じPC上のGTK X11バックエンド、他のUbuntu GNOME Wayland | 退行確認・参考試験。初版のリリース判定はブロックしない |
| P2 | KDE、X11、他Linuxディストリビューション | 可搬性を意識して実装し、環境を用意できる場合だけ参考試験。初版を原則ブロックしない |

原則として手動の動作試験はP0環境で行う。他環境のためにP0環境の安定性、操作性、実装速度を低下させる設計は採用しない。ただし、次の移植性方針は維持する。

- Waylandプロトコルを独自実装せず、GTK 4、GDK、GIO、PyGObjectの公開APIを利用する。
- パス、設定、ログはLinux標準とXDG Base Directoryに従う。
- セッション種別やデスクトップ環境名をハードコードせず、必要な機能の有無を実行時に判定する。
- GTK 4とPyGObject以外の外部Pythonパッケージを原則追加せず、ディストリビューション標準パッケージで起動できるようにする。
- 他環境の不具合修正がP0を壊さない範囲であれば、移植性改善を取り込む。

GTK 4はUnix上でWaylandバックエンドが既定で有効になり、`GDK_BACKEND=wayland` で明示的に選択できる。このPCでネイティブWayland接続を強制した実機試験結果をリリース可否の根拠とする。

## 2. 採用案の比較

| 案 | 実現性 | 主な問題 | 判定 |
|---|---:|---|---|
| 既存WPF GUIを通常の.NETとしてLinuxへ移植 | 不可 | WPF自体がWindows専用 | 不採用 |
| Avalonia XPFで既存WPFを動作させる | 技術的には可能 | 商用ライセンス、未対応機能、Win32/WPF専用依存、`AmatsukazeServerWin` 依存の検証量が大きい | 初版では不採用 |
| AvaloniaでLinux GUIを新規作成 | 可能 | ネイティブWaylandバックエンドが実験的で、安定動作を最優先する要件と合わない | 不採用 |
| GTK 4＋GirCore（C#） | 可能 | .NET資産を使えるが、GirCoreは1.0未満でAPI変更と未実装機能のリスクがある | 予備候補 |
| GTK 4＋PyGObject（Python） | 可能 | `AmatsukazeShared` を直接参照できない | **採用** |
| GTK 4＋gtkmm/C++ | 可能 | REST DTO・JSON・非同期通信を別実装し、ビルド依存も増える | 第二予備候補 |
| GTK 4＋Rust | 可能 | 新しいビルド基盤とREST実装を導入する必要がある | 不採用 |

### 2.1 GTK 4＋PyGObjectを採用する理由

- GTK 4のWaylandバックエンドは実験的機能ではなく、GNOME Wayland環境で標準的に利用されている。
- PyGObjectはGNOMEが案内するGTKのPythonバインディングであり、GTK 4のGObject Introspection APIを直接公開する。
- 現在PCにはPython 3.14.3、PyGObject 3.56.2、GTK 4.22.4が導入済みである。
- 調査用最小アプリは `GDK_BACKEND=wayland` を指定した状態で `wayland-0` へ正常接続した。
- 現在環境には `Gdk.FileList`、`Gtk.DropTarget`、`Gtk.FileDialog.open_multiple` が存在し、必要なD&Dと複数ファイル選択APIを利用できる。
- GUIの機能範囲が限定されるため、REST JSONをPythonで明示的に構築するコストは小さい。

PyGObjectはPythonコードからGTKのネイティブライブラリを呼び出す。WebViewやブラウザーUIではなく、D&D、ファイルダイアログ、日本語入力、描画はGTK/GDKのWayland経路で処理される。

### 2.2 Windows版GUIを直接移植しない理由

調査時点の `AmatsukazeGUI` は約2.5万行のXAML/C#からなり、次の依存を持つ。

- `net10.0-windows` とWPF
- Livet、WPF Behaviors、通知領域ライブラリ
- `AmatsukazeServerWin`
- Windowsのレジストリ、ウィンドウハンドル、テーマ、通知領域などのWindows固有処理

Microsoftの公式説明でもWPFはWindows上だけで動作するフレームワークである。Avalonia XPFは既存WPFアプリをLinuxで動かす選択肢だが、商用製品であり、WPF APIの不足部分やWindows固有処理を別途解消する必要がある。今回必要なのはタスク追加機能であり、GUI全体の移植は変更量と保守コストが要件に対して過大となる。

将来Windows GUI相当の全機能が必要になった場合も、まず新規GUIへ画面を段階的に追加する。XPFによる全面移植は、ライセンス条件を受け入れた上で別途短期間の実証を行う場合にだけ再検討する。

## 3. 対応範囲

### 3.1 初版で実装する機能

- ローカルRESTサーバーへの接続、接続状態表示、再接続
- 入力TSファイルのドラッグ＆ドロップ
- ファイル選択ダイアログからの入力追加
- 複数入力ファイルの一覧、個別削除、全消去
- 一覧にある全入力ファイルへの同一設定の一括適用・一括タスク追加
- 実行時間が長い一括追加処理のキャンセル
- 入力パスの手入力
- 出力先ディレクトリの入力とフォルダー選択
- プロファイル選択
- 優先度選択
- 追加時バッチ選択
- 処理モード選択
- キューへの追加
- 入力不足、接続失敗、APIエラーの画面表示
- WebUIと同じサーバー側UI状態を利用した前回値の復元
- GUIログの保存

### 3.2 初版で実装しない機能

- Windows GUIのキュー管理、ログ表示、設定編集、進捗監視などの全面移植
- GUIプロセス内へのAmatsukazeServerの組み込み
- GUIからのサーバー自動起動・終了
- 別PC上のサーバーへのファイルドラッグ＆ドロップ
- ホストとコンテナーで異なるパスを使用するDocker構成への自動パス変換
- WebUIやWindows GUIの置き換え

### 3.3 正式対応条件

初版のドラッグ＆ドロップは、次の条件をすべて満たす構成を正式対応とする。ServerCLIはホスト上で直接動かしても、Dockerコンテナー内で動かしてもよい。

1. GUIとサーバーを同じLinux端末で動かす。
2. GUIから見える絶対パスをサーバープロセスからも同じ絶対パスとして参照できる。
3. Docker版では、入力先と出力先を `/mnt:/mnt` のような**同一パスのbind mount**でコンテナーへ公開する。
4. シンボリックリンクを使用する場合は、そのリンク先もコンテナーから同じ絶対パスで参照できる。
5. ServerCLIの実行ユーザーが入力を読み取れ、出力先へ書き込める。通常モードで入力を移動する場合は、入力ディレクトリに必要な更新権限も持つ。
6. GUIはローカルループバックアドレスへ公開されたREST APIへ接続する。

同一ホストでも、GUIが `/home/user/video.ts` を渡し、コンテナー内では `/app/input/video.ts` としてしか参照できない構成は初版の対象外となる。将来リモート接続や異なるパスのDocker構成へ対応する場合は、サーバー側パス選択APIと明示的なパスマッピングを別機能として設計する。

### 3.4 同一パスbind mount型Dockerへの対応

同一パスbind mount型Dockerは、将来対応ではなく**初版と同時に対応・検証する**。

Linux GUIが送るのは絶対パスを含む通常の `AddQueueRequest` であり、サーバーがホストプロセスかコンテナープロセスかによってリクエスト形式は変わらない。REST APIはコンテナー内で各Targetへ `File.Exists` を実行するため、同じパスでbind mountされていれば既存処理だけで検証とキュー追加が成立する。GUIにDockerソケットへのアクセスやコンテナー操作権限を与える必要はない。

対応構成例は次のとおりとする。

```yaml
ports:
  - "32769:32769"
volumes:
  - /mnt:/mnt
environment:
  - RUN_UID=1000
  - RUN_GID=1000
```

この例では、ホストの `/mnt/recording/example.ts` をドロップすると、GUIとコンテナー内ServerCLIの双方が `/mnt/recording/example.ts` として参照する。出力先も `/mnt` 以下を選べば、追加の変換設定は不要である。

実装時には「Dockerモード」のような分岐をGUIへ設けない。接続先がループバックであり、サーバーが送信したパスを参照できれば同じ処理を使う。互換性の判定は次の二段階で行う。

1. GUIがホスト側で入力ファイルの存在を確認する。
2. REST APIがサーバー側、すなわちDocker利用時はコンテナー内で同じパスの存在を確認する。

出力先については現行REST APIが書き込み可能性まで検証しないため、Docker結合試験でServerCLI実行ユーザーのUID/GIDとbind mountの権限を確認する。初版で追加のDocker制御APIは作らず、必要条件と診断方法を文書化する。

### 3.5 現在の開発環境での確認結果

2026-08-20時点のこの開発環境では、同一パスbind mount型Dockerとして利用できることを次の読み取り専用確認で確認済みである。

- `docker/compose.yml` に `32769:32769` と `/mnt:/mnt` が設定されている。
- コンテナーがポート32769をホストへ公開している。
- ホストの `http://127.0.0.1:32769/api/health` が正常応答する。
- RESTのパス候補APIが `/mnt/recording` 以下のTSファイルを、ホストと同じ `/mnt/recording/...` という絶対パスで返す。
- コンテナー内のServerCLIプロセスはUID/GID 1000で動作している。

したがって、この環境の `/mnt` 以下にある入力・出力については、GUI側にパス変換機能がない初版でも対応対象となる。実際のキュー追加とエンコードはファイルを変更するため、設計調査では実行せず、実装後のDocker結合試験で確認する。

## 4. 全体構成

```text
Linuxファイルマネージャー
        │ ファイルをドロップ
        ▼
AmatsukazeLinuxGUI (GTK 4 / PyGObject / Python 3)
        │
        ├─ Python標準HTTP/JSON APIクライアント
        │
        ▼ HTTP (既定: 127.0.0.1:32769)
AmatsukazeServerCLI REST API
        │
        ▼
既存QueueManager / AmatsukazeCLI
```

GUIはクライアントとしてのみ動作する。`AmatsukazeServer`、`AmatsukazeServerWin`、`AmatsukazeGUI` のコードやバイナリは参照しない。これにより、Linux GUIの障害や終了が実行中のエンコード処理に影響しない構成とする。

### 4.1 GUIフレームワーク

- `/usr/bin/python3` 3.14.3（P0環境の確認値）
- PyGObject 3.56.2（P0環境の確認値）
- GTK 4.22.4（P0環境の確認値）
- GDK Waylandバックエンド
- UIはGTK 4のみで構成し、初版ではlibadwaitaを必須にしない。
- Python標準ライブラリの `urllib.request`、`json`、`threading`、`logging`、`pathlib`、`unittest` を利用する。
- 外部PyPIパッケージは原則使用しない。

通常起動ではWaylandを第一候補とし、他環境での可搬性のためX11を第二候補にできる。ただしP0試験では必ず `GDK_BACKEND=wayland` を設定し、Waylandへ接続できなければ起動失敗とする。起動ログに `Gdk.Display.get_default().get_name()` とセッション関連情報を記録し、誤ってXWaylandで合格していないことを確認する。

### 4.2 非同期処理

GTKはメインスレッド以外から操作しない。REST通信、ディレクトリ列挙、ファイル事前検証は `threading.Thread` または `concurrent.futures.ThreadPoolExecutor` で実行し、結果だけを `GLib.idle_add()` でGTKメインループへ戻す。

HTTPタイムアウト、終了通知、二重送信防止の状態は専用Serviceで管理する。Pythonスレッド自体を強制終了せず、キャンセルフラグ、HTTPタイムアウト、既存の追加処理キャンセルAPIを組み合わせる。

## 5. プロジェクト構成

実装時は次の構成を基本とする。名前は実装時の責務分割により微調整してよいが、GUI固有ファイルを他プロジェクトへ分散させない。

```text
AmatsukazeLinuxGUI/
├── pyproject.toml
├── amatsukaze_linux_gui.py
├── amatsukaze_linux_gui/
│   ├── __init__.py
│   ├── application.py
│   ├── main_window.py
│   ├── api_client.py
│   ├── dto.py
│   ├── path_service.py
│   ├── settings_service.py
│   ├── log_service.py
│   └── task_add_service.py
├── Assets/
│   └── アプリアイコン
├── Packaging/
│   ├── AmatsukazeLinuxGUI.sh
│   └── AmatsukazeLinuxGUI.desktop（将来オプション）
└── Tests/
    ├── test_api_client.py
    ├── test_dto.py
    ├── test_path_service.py
    └── test_task_add_service.py
```

### 5.1 REST契約の管理

PythonからC#の `AmatsukazeShared` を直接参照しない。`AmatsukazeShared` のDTOと `IAmatsukazeApi` を契約の正本として読み、Linux GUI内の `dto.py` と `api_client.py` に必要なフィールドだけを明示する。

- JSONキーは既存REST APIの実レスポンスに合わせる。
- 未知のレスポンスフィールドは無視し、不足する必須フィールドは説明付きエラーにする。
- 送信JSONをゴールデンデータと比較する単体テストを置き、DTOのずれを検出する。
- API変更時に追従箇所が分かるよう、各メソッドへ対応するC# DTO/API名をコメントする。
- 不足するREST APIが実装中に見つかった場合は、まず既存APIの組み合わせで解決し、それでも不足する場合だけ `AmatsukazeShared` と `AmatsukazeServer/Rest` に最小限の追加を行う。

## 6. 画面設計

初版は1ウィンドウ構成とする。

```text
┌─────────────────────────────────────────────────────┐
│ Amatsukaze Linux GUI       接続済み  [接続設定][再接続] │
├─────────────────────────────────────────────────────┤
│ 入力ファイル                                         │
│ ┌─────────────────────────────────────────────────┐ │
│ │ ここにTSファイルをドロップ                       │ │
│ └─────────────────────────────────────────────────┘ │
│ [ファイルを選択] [パスを追加] [全消去]              │
│  /recorded/a.ts                              [削除] │
│  /recorded/b.ts                              [削除] │
│                                                     │
│ プロファイル [________________▼]                    │
│ 出力先       [____________________] [フォルダー選択] │
│ 優先度       [__▼]   処理モード [____________▼]     │
│ 追加時バッチ [_______________________________▼]     │
│                                                     │
│                 [キューに追加] [以降の追加を停止]    │
│ 状態: 5件の追加要求を処理中                          │
└─────────────────────────────────────────────────────┘
```

### 6.1 起動時の処理

1. ローカル設定からRESTポートを読み込む。未設定時は `32769` とする。
2. `http://127.0.0.1:{port}` へ接続する。
3. 次の情報を可能な範囲で並列取得する。
   - `GetProfilesAsync()`
   - `GetProfileOptionsAsync()`
   - `GetUiStateAsync()`
   - `GetInfoSummaryAsync()` または同等のサーバー確認API
4. WebUIと同じ規則で前回のプロファイル、出力先、追加時バッチを初期選択する。
5. 一部の取得だけ失敗した場合は、取得できた項目を表示しつつ再試行可能にする。

プロファイル名は現行WebUIと同様に、JSON内の `Name` と `name` の両方を許容する。処理モードは `QueueSettingExtensions.QueueProcModes`、優先度は共有側に既存の選択肢があればそれを利用し、GUI内で列挙値を重複定義しない。

### 6.2 接続設定

- 初版で指定できるのはポート番号、またはループバックURLだけとする。
- ホスト名として `127.0.0.1`、`localhost`、`::1` 以外を入力した場合は接続しない。
- サーバーがポート競合回避で別ポートへ移動した場合に備え、画面上でポートを変更できるようにする。
- ポートを無差別に走査しない。誤ったHTTPサービスへ接続しないよう、ユーザーが指定した接続先でAmatsukaze固有APIの応答を確認する。
- 接続不能時もアプリを終了せず、原因と接続先を表示して再接続できるようにする。

## 7. ドラッグ＆ドロップとパス処理

### 7.1 実装方針

ドロップ領域へ `Gtk.DropTarget` を追加し、受け入れ型を `Gdk.FileList`、actionを `Gdk.DragAction.COPY` とする。drop signalで `Gdk.FileList.get_files()` から `Gio.File` を取得し、`Gio.File.get_path()` が返すローカルパスを絶対パスへ正規化して入力一覧へ追加する。

`Gio.File.get_path()` が `None` となるリモートURIや仮想ファイルは初版では受け付けず、「ローカルファイルではありません」と表示する。P0試験では `GDK_BACKEND=wayland` を強制したGUIへGNOME Filesからドロップし、ネイティブWayland経路であることを確認する。

処理規則は次のとおりとする。

- 通常ファイルは、現行QueueManagerの列挙条件に合わせ、映像コンテナーとしてのTSファイルを表す拡張子 `.ts` または `.m2t` のみ受け付ける。`.m2ts` は対象にしない。拡張子比較は大文字・小文字を区別しない。
- ディレクトリがドロップされた場合は直下の対象ファイルだけを列挙し、再帰検索しない。
- `os.path.abspath()` と `os.path.normpath()` で、シンボリックリンクを強制解決せずに絶対パスへ正規化する。
- Linuxのパス規則に合わせ、重複判定は大文字・小文字を区別する。
- 同じ絶対パスは重複登録しない。
- 読み取り不能、存在しない、対象拡張子でない項目は追加せず、除外件数と理由を表示する。
- シンボリックリンクは最終的にサーバーから参照可能であれば許可する。リンク解決後のパスへの強制置換は行わない。
- 空白、日本語、記号を含むパスを文字列連結やシェル経由で処理しない。

Windows GUIと同様に複数ファイルを扱えるため、WebUIの単一パス入力よりわずかに機能が増える。ただしREST APIの `Targets` は既に複数入力を表現できるため、サーバー変更は不要である。

### 7.2 ファイル選択ダイアログ

- OSのファイル選択ダイアログを使用する。
- GTK 4.10以降の `Gtk.FileDialog.open_multiple()` と `Gtk.FileDialog.select_folder()` を使用する。
- 複数選択を許可する。
- フィルターはTSファイル（`.ts`、`.m2t`）とする。
- ドラッグ＆ドロップと同じ検証サービスへ入力を渡し、挙動を統一する。
- 出力先はフォルダー選択ダイアログで選択する。

## 8. REST APIとの対応

| 画面上の処理 | 使用する既存API/DTO | 用途 |
|---|---|---|
| プロファイル一覧 | `GetProfilesAsync()` | プロファイル選択肢 |
| 追加時バッチ一覧 | `GetProfileOptionsAsync()` | `PreBatFiles` の選択肢 |
| 前回値 | `GetUiStateAsync()` | プロファイル、出力先、バッチの初期値 |
| サーバー確認 | `GetInfoSummaryAsync()` 等 | Amatsukaze接続の確認 |
| キュー追加 | `AddQueueAsync(AddQueueRequest)` | タスク登録 |

### 8.1 複数ファイルへの同一設定の一括適用

**実現可能であり、サーバーやREST APIの追加実装は不要である。**

Windows版の `QueueViewModel.FileDropped` は、ドロップされた複数ファイルを `AddQueueRequest.Targets` に格納し、出力設定を選択した後、リクエストを1回だけ送信している。サーバーの `QueueManager.AddQueue` は `Targets` を順に処理し、同じ `Outputs`、`Mode`、`AddQueueBat`、`Tags` を使ってファイルごとのキュー項目へ展開する。Linux GUIはWindows版のUIコードを移植せず、このDTOと同じJSONをPythonで生成して既存サーバー動作を再利用する。

Linux GUIでの操作と送信単位は次のとおりとする。

1. ドラッグ＆ドロップ、ファイル選択、パス手入力を、画面上の1つの入力一覧へ蓄積する。
2. ユーザーは入力一覧全体に対するプロファイル、出力先、優先度、処理モード、追加時バッチを1組だけ指定する。
3. 送信前に一覧の全ファイルを検証する。
4. 全ファイルを `Targets` に格納し、設定を1組だけ持つ `AddQueueRequest` を1回送信する。
5. サーバーが各Targetを既存仕様どおり個別のキュー項目へ展開する。

初版ではファイルごとの設定上書きは設けない。異なる設定で追加したい場合は、入力一覧を分けて複数回追加する。この制約により、画面上の設定と実際に全Targetへ適用される設定が一致していることを明確にする。

`Targets` には各ファイルの絶対パスを入れるため、複数の異なるディレクトリにあるファイルを同時に追加できる。`DirPath` は最初のファイルの親ディレクトリとするが、`Targets` が指定されている場合、サーバーは `DirPath` の全ファイルを再列挙せず、明示されたTargetだけを処理する。

### 8.2 一括追加時の検証と失敗時の扱い

一括追加は「すべてのファイルが必ず成功するトランザクション」ではない。既存サーバーとの互換性を保ち、次の規則とする。

- GUIの事前検証で存在しないファイルや対象外拡張子が1件でもある場合は送信せず、該当行を表示する。
- REST APIも全Targetの存在を検証するため、送信時点で1件でも消失していればHTTPエラーとなり、そのリクエストの追加処理は開始されない。
- REST検証後のTS解析失敗は、既存サーバー仕様どおり、そのファイルに対応する `PreFailed` のキュー項目として扱われる。他の正常なファイルの追加は継続する。
- 既にアクティブなキューへ存在する対象は、既存 `QueueManager` の重複除外規則に従う。
- サーバー処理中にキャンセルした場合は、キャンセルまでに追加された項目が残る可能性がある。GUIは「全件取り消し」ではなく「以降の追加処理を停止」と表示する。
- 一括処理中は入力と設定を編集不可にして二重送信を防ぎ、送信したTarget総数を表示する。現行APIからTarget単位の進捗は取得できないため、未確認の進捗や現在ファイル名は表示せず、処理中表示とキャンセル操作を提供する。

キャンセルには `CancelAddQueueAsync()` と同じ既存RESTエンドポイントを利用する。キャンセル要求自体が失敗した場合は追加処理が継続している可能性を画面へ明示する。

`AddQueueRequest` は次のように組み立てる。

- `DirPath`: 最初の入力ファイルの親ディレクトリ
- `Targets`: 正規化済み絶対パスの一覧
- `Outputs`: 選択されたプロファイル、出力先、優先度を持つ1要素
- `Outputs[0].Priority`: 入力一覧の全Targetへ適用する優先度
- `Mode`: 選択された処理モード
- `AddQueueBat`: 「なし」の場合は `null`、それ以外は選択値
- タグ: 初版ではWebUIと同様、既定値または空

送信前にGUIでも全Targetの必須項目と `os.path.isfile()` を確認するが、最終判断は既存REST APIの検証に任せる。送信中は追加ボタンを無効化して二重登録を防ぎ、ウィンドウ終了時は未完了のHTTPリクエストだけでなく、必要に応じてサーバーの一括追加処理もキャンセルするかをユーザーへ確認する。

成功時は入力一覧を消去し、プロファイル、出力先、優先度などは次の追加に再利用できるよう保持する。失敗時は入力を保持し、修正後に再送できるようにする。

## 9. エラー表示、設定、ログ

### 9.1 エラー表示

- 入力エラーは対象フィールド付近に日本語で表示する。
- REST APIが返したエラーメッセージは、WebUIと同じく可能な範囲で本文から抽出して表示する。
- 通信不能、タイムアウト、サーバー検証エラー、予期しない例外を区別する。
- 予期しない例外の詳細はログへ書き、画面には簡潔なメッセージを表示する。

### 9.2 ローカル設定

GUI固有設定はXDG Base Directoryに従って保存する。

- 設定: `$XDG_CONFIG_HOME/Amatsukaze/LinuxGUI.json`
- `XDG_CONFIG_HOME` が未設定の場合: `~/.config/Amatsukaze/LinuxGUI.json`
- 初版で保存する値: RESTポート、ウィンドウサイズ

プロファイル、出力先、追加時バッチの前回値は既存サーバーのUI状態を使用し、GUI側へ二重保存しない。

### 9.3 ログ

- ログ: `$XDG_STATE_HOME/Amatsukaze/LinuxGUI/AmatsukazeLinuxGUI.log`
- `XDG_STATE_HOME` が未設定の場合: `~/.local/state/Amatsukaze/LinuxGUI/AmatsukazeLinuxGUI.log`
- 起動、接続先、接続結果、キュー追加結果、除外したドロップ項目、例外を記録する。
- ファイルパスは操作確認に必要なため記録するが、HTTP本文や将来の秘密情報を無条件に記録しない。
- 日時はロケールに依存しないISO 8601形式で記録する。
- ログが無制限に増えないよう、サイズまたは世代数によるローテーションを実装する。

## 10. ビルド・配布への組み込み

初版実装時に、`AmatsukazeLinuxGUI/` 外で変更する予定のファイルは次に限定する。

| ファイル | 予定する変更 |
|---|---|
| `scripts/build.sh` | Python構文検査を行い、GUIモジュールとランチャーを配布物へコピー |
| `doc/BuildLinux.md` | GUIのビルド、起動、必要なLinuxパッケージを追記 |
| `docker/readme.md` | 同一パスbind mount、ポート公開、UID/GID、GUI接続方法を追記 |

Pythonアプリは.NETソリューションへ追加しない。既存REST APIで不足がなければ、`AmatsukazeServer` と `AmatsukazeShared` の変更は行わない。GitHub Actionsは既存の `scripts/build.sh` を呼ぶため、GUI追加だけを理由とするworkflowファイルの変更は原則不要とする。

### 10.1 配布方針

- GUIのPythonモジュールは既存Linuxパッケージの `exe_files/AmatsukazeLinuxGUI/` に置く。
- Pythonコードを単一バイナリへ凍結しない。PyInstaller等はGTK typelibやテーマ、入力メソッドの組み込みを複雑にし、P0の安定性を下げるため初版では使用しない。
- ビルド時に `python3 -m compileall` とGUI非依存の単体テストを実行する。
- ランチャー原本は `AmatsukazeLinuxGUI/Packaging/AmatsukazeLinuxGUI.sh` に置き、ビルド時に配布物のルートへコピーする。
- ランチャーは `/usr/bin/python3`、PyGObject、GTK 4の存在を確認し、GUIのPythonエントリーポイントを直接 `exec` する。
- WaylandセッションではWaylandを第一候補にする。P0試験用の起動では `GDK_BACKEND=wayland` を明示し、フォールバックを禁止する。
- 利用者が明示した `GDK_BACKEND` は尊重し、他Linux環境ではGTKが対応するX11バックエンドも使用可能とする。

Ubuntu/Debian系の実行依存として、少なくとも `python3`、`python3-gi`、`gir1.2-gtk-4.0`、`libgtk-4-1` を `doc/BuildLinux.md` と配布ドキュメントへ明記する。他ディストリビューションについては対応するPyGObject/GTK 4パッケージ名を例示する。libadwaitaは初版の必須依存にしない。

## 11. 実装フェーズ

### フェーズ0: 技術検証

Docker対応を後から追加するのではなく、フェーズ0からホスト上ServerCLIと同一パスbind mount型Dockerを並行して確認する。

1. `AmatsukazeLinuxGUI/` に最小のGTK 4/PyGObjectアプリを作成する。
2. `GDK_BACKEND=wayland` を強制して、このPCの `wayland-0` へ接続することを確認する。
3. 起動ログとGTK Inspectorで使用中のdisplay/backendを確認し、XWaylandへフォールバックしていないことを確認する。
4. GNOME FilesからGUIへ単一・複数ファイルとディレクトリをドロップし、`Gdk.FileList` から日本語・空白を含む絶対パスを取得する。
5. `Gtk.FileDialog` で複数ファイル選択とフォルダー選択を行う。
6. 日本語入力、クリップボード、ウィンドウ描画、表示倍率、終了処理を確認する。
7. Python標準HTTPクライアントからローカルServerCLIのプロファイル一覧を取得する。
8. Docker版で `32769:32769` と同一パスbind mountを設定し、ホストGUIとコンテナー内ServerCLIの双方から同じ入力パスが見えることを確認する。
9. 配布用ランチャーからこのPCの通常利用環境で起動することを確認する。

**完了条件:** このPCのGNOME WaylandセッションでGUIが安定して動作し、ドロップした日本語・空白を含むファイルの絶対パスを取得でき、ホスト上ServerCLIと同一パスbind mount型Docker版の両方でREST接続とパス参照が成立すること。

### フェーズ1: アプリケーション基盤

1. `Gtk.Application`、`Gtk.ApplicationWindow`、画面Widget、Serviceの基本構成を作る。
2. REST APIクライアント、JSON DTO変換、タイムアウト、キャンセル、接続状態管理を実装する。
3. XDG準拠の設定保存とログを実装する。
4. 起動時データ取得とWebUI同等の既定値復元を実装する。
5. GTKを必要としないService単体テスト基盤を `unittest` で作る。
6. REST通信とファイル列挙をバックグラウンドスレッドへ置き、`GLib.idle_add()` で画面を更新する。

**完了条件:** サーバー起動中・停止中の両方でGUIが安定して起動し、再接続できること。

### フェーズ2: タスク追加機能

1. 入力一覧、ファイル選択、ドラッグ＆ドロップ、手入力を実装する。
2. プロファイル、出力先、優先度、バッチ、処理モードの入力を実装する。
3. 入力検証と `AddQueueRequest` 生成を実装する。
4. 全Targetへ同一設定を適用した1リクエストでの一括追加を実装する。
5. キュー追加、二重送信防止、処理中表示、キャンセル、成功・失敗表示を実装する。
6. 複数ファイル、異なる親ディレクトリ、ディレクトリドロップ、重複、無効パスを検証する。
7. 同一パスbind mount型Dockerに対して同じ `AddQueueRequest` で一括追加できることを検証する。

**完了条件:** WebUIのタスク追加画面で設定できる全項目を指定でき、Windows版と同様に、複数ファイルを同一設定で1回のRESTリクエストから追加できること。

### フェーズ3: ビルド・配布統合

1. `scripts/build.sh` へPython構文検査、単体テスト、GUIファイルの配布物コピーを追加する。
2. ランチャーと必要なGTK/PyGObjectランタイム依存を整備する。
3. `doc/BuildLinux.md` へ依存パッケージ、起動方法、Wayland確認方法を追記する。
4. `docker/readme.md` と `docker/compose.sample.yml` へ同一パスbind mount型GUI接続例を追記する。
5. 既存のLinuxパッケージ作成CIで成果物を確認する。

**完了条件:** 通常のLinuxパッケージ作成手順だけでGUIを含む配布物が生成され、ホスト上ServerCLIと同一パスbind mount型Dockerの両方の起動・接続条件が文書化されていること。

### フェーズ4: 結合試験とリリース判定

1. 実ServerCLIへ全処理モード・優先度・バッチの組み合わせで登録する。
2. このPCのUbuntu 26.04、GNOME Shell 50.1、Waylandセッションで全手動操作試験を行う。
3. GNOME FilesからのD&D、ファイルダイアログ、日本語入力、クリップボード、キーボード操作、フォーカス順、表示倍率を確認する。
4. サーバー停止、誤ポート、通信切断、ファイル消失時のエラーを確認する。
5. Docker版で入力読み取り、出力書き込み、通常モードの入力移動、複数ファイル追加を確認する。
6. Docker版で同一パスmount不足、権限不足、シンボリックリンク先不足を再現し、理解できるエラーになることを確認する。
7. このPC上で配布成果物を `GDK_BACKEND=wayland` 付きで起動し、必要パッケージ、ランチャー、設定、ログ出力を確認する。
8. 他のUbuntu、KDE、X11は、利用可能な環境と時間がある場合だけ参考試験を行う。

**完了条件:** 後述の受け入れ条件をすべて満たし、既存ServerCLI/WebUIの動作を壊していないこと。

### 将来フェーズ: 機能拡張

- ホストとコンテナーで異なるパスを使うDocker構成の明示的なパス変換
- キュー一覧、進捗、キャンセル、ログ表示
- プロファイル編集
- サーバー側パス候補APIを使うリモート接続モード
- `.desktop` ファイルとデスクトップメニューへの登録

サーバー自動起動を追加する場合も、GUIプロセスへサーバーを埋め込まない。既存 `AmatsukazeServerCLI` を独立プロセスとして起動し、GUI終了後も実行中タスクを継続できるライフサイクルにする。

## 12. テスト計画

### 12.1 単体テスト

偽のREST transportと一時ファイルを用い、少なくとも次を検証する。

- プロファイル名の `Name` / `name` 取り扱い
- UI状態からの既定値復元
- ファイル拡張子、重複、存在確認、ディレクトリ展開
- 日本語、空白、シンボリックリンクを含むパス
- `AddQueueRequest` の全フィールド対応
- 複数Targetに対して `Outputs`、`Mode`、`AddQueueBat`、`Tags` が1組だけ生成されること
- 異なるディレクトリのTargetでも各絶対パスが保持されること
- 1件でも事前検証に失敗した場合はAPIを呼ばないこと
- REST検証で1件が失敗した場合に、そのリクエストからキュー項目が追加されないこと
- バッチ「なし」の `null` 変換
- 二重送信防止とキャンセル
- APIエラー本文の抽出
- 設定ファイル破損時の既定値復帰

### 12.2 ビルド試験

- `python3 -m compileall AmatsukazeLinuxGUI`
- `python3 -m unittest discover AmatsukazeLinuxGUI/Tests`
- 既存 `scripts/build.sh` による配布物生成
- 配布物内ランチャーの依存確認と起動
- `git diff --check` と既存テスト

### 12.3 手動結合試験

- 単一・複数ファイルの選択とドロップ
- 複数ファイルへ同一のプロファイル、出力先、優先度、処理モード、追加時バッチが適用されること
- 異なるディレクトリにある複数ファイルの一括追加
- 一括追加中のキャンセルと、キャンセル前に追加済みとなった項目の表示
- 同一パスbind mount型Dockerへの単一・複数ファイル追加
- Docker版での通常モードによる入力移動と、テストモードで入力が残ること
- bind mount不足、入力権限不足、出力権限不足、リンク先mount不足
- ディレクトリのドロップ
- このPCのGNOME Filesから、Waylandセッション上のGUIへのドロップ
- Ubuntu 26.04 LTS、GNOME Shell 50.1、Wayland、GTK 4.22.4、PyGObject 3.56.2
- ファイルダイアログ、日本語入力、クリップボード、ウィンドウ再表示、終了
- `GDK_BACKEND=wayland` 強制時に起動し、displayが `wayland-0` であること
- 他のUbuntu、KDE、X11は環境を用意できる場合の参考試験
- 全処理モード、優先度1～5、プロファイル、追加時バッチ
- サーバー停止、再起動、誤ポート、タイムアウト
- 入力ファイルまたは出力先が送信直前に消えた場合
- GUIを閉じてもServerCLIの処理が継続すること

## 13. 受け入れ条件

初版は次をすべて満たした時点で完了とする。

1. このPCのUbuntu 26.04 LTS、GNOME Waylandセッションで、配布パッケージからLinux GUIを安定して起動・終了できる。
2. `GDK_BACKEND=wayland` を指定して起動でき、起動ログまたはGTK InspectorでWayland displayへ接続していることを確認できる。XWaylandでの動作はP0合格としない。
3. ネイティブWayland上でD&D、ファイルダイアログ、日本語入力、クリップボード、描画が正常に動く。
4. ローカルServerCLIへの接続状態と接続エラーが分かる。
5. `.ts` / `.m2t` をGNOME Filesからドロップして絶対パスを取得でき、`.m2ts` は対象外となる。
6. ファイルダイアログと手入力でも同じ入力一覧を作れる。
7. WebUIのタスク追加画面と同等のプロファイル、出力先、優先度、追加時バッチ、処理モードを指定できる。
8. 複数ファイルを1つの `AddQueueRequest` にまとめ、同一のプロファイル、出力先、優先度、処理モード、追加時バッチで登録できる。
9. サーバー上では、各Targetが既存仕様どおり個別のキュー項目へ展開される。
10. `/mnt:/mnt` のような同一パスbind mount型Dockerへ、ホスト上ServerCLIと同じGUI操作でタスクを追加できる。
11. Docker版でServerCLIの実行ユーザーに必要な権限があれば、入力読み取り、出力作成、通常モードの入力移動が完了する。
12. 無効な入力、mount不足、権限不足、サーバー停止、API検証エラーでGUIが異常終了しない。
13. 二重クリックで同じタスクが重複登録されない。
14. 一括追加をキャンセルした場合、部分的に追加済みとなり得ることが画面で分かる。
15. GUIを終了してもサーバーと実行中タスクへ影響しない。
16. GUI固有の実装ファイルが `AmatsukazeLinuxGUI/` 以下にまとまっている。
17. 既存ファイルの変更を、配布・起動・Docker説明などに必要な最小限へ限定する。
18. 既存のServerCLI、WebUI、AddTaskのビルドと基本動作が維持される。

## 14. リスクと対策

| リスク | 対策 |
|---|---|
| GTKまたはPyGObject更新でAPIや挙動が変わる | P0環境で確認したバージョンを記録し、更新時にネイティブWayland回帰試験を行う |
| GNOME FilesからのD&DでURIやファイル一覧の扱いが異なる | `Gdk.FileList` と `Gio.File.get_path()` を用い、GNOME Filesとの実操作をフェーズ0で最初に検証する |
| Python側DTOがサーバーのC# DTOとずれる | `AmatsukazeShared` を契約の正本とし、実例JSONを用いたgolden testとAPI結合試験を置く |
| 他Linux環境でGTK/PyGObjectのバージョンやパッケージ名が異なる | 初版のリリース判定はP0環境を優先し、GTK 4標準APIだけを使う。対応確認済み環境を文書化する |
| ServerCLIのRESTポートが既定値から移動する | ポートを画面表示・編集可能にし、再接続を用意する |
| GUIとサーバーでパスの見え方が異なる | 初版を同一ホスト・同一絶対パスに限定し、Dockerでは同一パスbind mountを要求してサーバー側でも存在確認する |
| Dockerのbind mountは正しいが権限が不足する | `RUN_UID` / `RUN_GID` と入力・出力ディレクトリの権限を文書化し、通常モードの入力移動まで結合試験する |
| シンボリックリンクがmount外を指す | リンク先も同一パスでmountする条件を明記し、サーバー側の存在確認エラーを表示する |
| Python worker threadからGTKを操作して不安定になる | バックグラウンド処理はUIへ触れず、完了通知と画面更新を `GLib.idle_add()` でGTKメインループへ戻す |
| UIスレッドでファイル列挙や通信が停止する | ディレクトリ列挙とREST通信をworker threadへ移し、キャンセル可能にする |
| 既存APIのエラー形式が一定でない | WebUIと同等の抽出処理をGUI内に閉じ込め、予期しない本文はログへ残す |
| `CancelAddQueueAsync()` がリクエストIDを受け取らない | 自動キャンセルせず、Linux GUI自身の送信が処理中の場合だけ明示確認後に呼び出す。複数クライアント同時操作は制約として文書化する |
| 実行環境にGTK 4またはPyGObjectがない | ランチャーの開始時に依存を検査し、必要なディストリビューションパッケージ名を表示する |

## 15. 公式資料と調査根拠

- [WPF overview（Microsoft Learn）](https://learn.microsoft.com/en-us/dotnet/desktop/wpf/overview/): WPFはWindows上で動作するデスクトップUIフレームワーク。
- [GTK Wayland backend](https://docs.gtk.org/gtk4/wayland.html): Unix上でWaylandバックエンドが標準提供され、`GDK_BACKEND=wayland` で明示選択できる。
- [GTK drag and drop](https://docs.gtk.org/gtk4/drag-and-drop.html): GTK 4のD&Dモデルと `Gtk.DropTarget`。
- [Gdk.FileList](https://docs.gtk.org/gdk4/struct.FileList.html): ファイルのドラッグ＆ドロップで複数の `Gio.File` を受け取る型。
- [Gtk.FileDialog](https://docs.gtk.org/gtk4/class.FileDialog.html): GTK 4の非同期ファイル選択API。
- [PyGObject](https://pygobject.gnome.org/): GTKを含むGObjectライブラリの公式Pythonバインディング。
- [PyGObject threading guide](https://pygobject.gnome.org/guide/threading.html): worker threadとGLibメインループを安全に連携する方法。
- [GirCore](https://github.com/gircore/gir.core): GTKをC#から利用できる候補。ただし1.0以前でAPI変更可能性と未実装機能が明記されているため初版では予備候補。
- [Avalonia Linux platform guide](https://docs.avaloniaui.net/docs/platform-specific-guides/linux): AvaloniaのネイティブWaylandバックエンドが実験的であることを、不採用判断の根拠とした。
- [Avalonia XPF overview](https://docs.avaloniaui.net/xpf/): WPFアプリを他OSで動かす商用選択肢。
- [Avalonia XPF missing features](https://docs.avaloniaui.net/xpf/version-info/missing-features): XPFで未対応または制約のあるWPF機能。

## 16. 実装開始時の確認事項

実装着手時には、次の順序で前提を再確認する。

1. このPCのPython、PyGObject、GTK 4のバージョンと、使用予定APIが利用可能であることを再確認する。
2. `GDK_BACKEND=wayland` を指定した最小アプリを起動し、Wayland displayへの接続、GNOME FilesからのD&D、ファイルダイアログ、日本語入力を確認する。
3. ServerCLIのREST既定ポートとポート競合時の挙動を実機で確認する。
4. WebUIのタスク追加DTOとUI項目に変更がないか確認する。
5. フェーズ0の技術検証を完了してから、配布統合を含む本実装へ進む。

PyGObject固有の解消困難な問題が見つかった場合も、ネイティブWaylandを優先してGTK 4自体は維持し、GirCoreによるC#実装、次にgtkmmによるC++実装の順で再評価する。AvaloniaやWindows WPF全体の移植へ自動的に切り替えない。

## 17. 入力・出力拡張子の全体調査結果

### 17.1 QueueManagerの現行TS入力条件との整合

Linux GUIの入力拡張子は、現行QueueManagerの列挙条件に合わせて `.ts` と `.m2t` とし、`.m2ts` は対象外とする。

現行の `AmatsukazeServer/Server/QueueManager.cs` では、`AddQueueRequest.Targets` が `null` の場合に行うディレクトリ自動列挙の条件が `.ts` または `.m2t` となっている。本設計ではこれをバグとは扱わず、後段の `TsInfo` / `Mpeg2TsParser` が188バイトのTSパケット（`TS_PACKET_LENGTH = 188`）を前提に処理し、192バイト経路が実装上使われていないため、188バイトTSを受け入れる入力候補として `.m2ts` を除外する現行方針と解釈する。

Linux GUIは、ファイルダイアログ、ドラッグ＆ドロップ、手入力のすべてで同じ `.ts` / `.m2t` フィルターを使用する。`Targets != null` の明示Targetはサーバー側で拡張子フィルターを持たず、`TsInfo` の内容解析へ進むが、Linux GUIはサーバーのこの挙動に依存せず、`.m2ts` を送信前に除外する。

実装時は少なくとも次を試験する。

1. `Targets == null` のディレクトリ列挙で `.ts` と `.m2t` が追加対象になる。
2. 同じ列挙、ファイルダイアログ、ドラッグ＆ドロップで `.m2ts` が対象外になる。
3. `.TS` と `.M2T` は大文字・小文字を区別せず処理される。
4. 188バイトTSの `.ts` / `.m2t` サンプルがQueueManagerの `TsInfo` 解析を通過する。

QueueManagerのコード自体は変更せず、Linux GUI側でこの既存条件を再現する。

### 17.2 経路別の入力判定

| 経路 | 拡張子による扱い | 実際の内容判定・注意点 |
|---|---|---|
| `AmatsukazeServer` の `AddQueueRequest.Targets == null` | `QueueManager.cs` がディレクトリから現行条件どおり `.ts` または `.m2t` を列挙 | 列挙後は `TsInfo` が188バイトTSを前提にMPEG-TSとして解析する。現行条件では `.m2ts` を自動列挙しない。なお、現行RESTアダプターは `Targets == null` を空リストへ変換してから渡すため、この分岐はREST経由ではなく、サーバー内部/APIのnull指定時の挙動である |
| `AddQueueRequest.Targets` を明示 | RESTは存在確認だけで、拡張子フィルターなし。Linux GUIは `.ts` / `.m2t` に限定 | `QueueManager` が `TsInfo` で解析するため、通常キューは188バイトTS内容が必要。拡張子だけでは最終的な可否は決まらない |
| WebUIタスク追加 | パス候補表示は `Extensions=".ts"` のみ | 送信時は入力文字列を `Targets` に入れるだけで、WebUI自身は拡張子を強制しない |
| Windows GUIのファイルドロップ | 直接ファイルは無条件。ディレクトリは `EndsWith("ts")` | 既存Windows GUIでは `.ts` と `.m2ts` も末尾が `ts` のため列挙されるが、Linux GUIではQueueManager条件に合わせて `.m2ts` を除外する |
| `AmatsukazeAddTask` | ファイル存在確認のみで拡張子制限なし | 実際のサーバー追加時に上記 `Targets` 経路へ入る |
| `AmatsukazeCLI` の通常 `ts` / `cm` モード | `-i` の拡張子制限なし | `TsInfo`、TSパケット解析で内容を読む。コード上の通常パケット長は188バイトで、192バイト経路は使用箇所を確認できない |
| `AmatsukazeCLI --mode g` | `-i` の拡張子制限なし | `avformat_open_input()` に形式を固定せず、同梱FFmpegのプローブ・デマルチプレクサで判定するため、対応範囲はFFmpegビルドに依存する |
| `AmatsukazeGenLogo` / ロゴ解析 | ヘルプやGUIフィルターはTS（GUIは `.ts` / `.m2ts`） | 実処理は `TsInfo` で内容を読むため、拡張子そのものでは判定しない |

以上から、Linux GUIの初版で表示・選択対象を `.ts` と `.m2t` に限定し、`.m2ts` を除外するのは現行QueueManagerとの整合上妥当である。最終的な受け付け可否はサーバー側のTS解析結果で決まり、188バイトTSとして解析できる実ファイルで結合試験する必要がある。

### 17.3 出力拡張子

出力形式は `MP4`、`MKV`、`M2TS`、`TS`、`TSREPLACE` の5種類で、サーバーとC++ CLIの対応は一致している。

| 出力形式 | 生成拡張子 | 備考 |
|---|---|---|
| MP4 | `.mp4` | MP4Box等を使用 |
| MKV | `.mkv` | mkvmerge等を使用 |
| M2TS | `.m2ts` | tsmuxer用のmetaファイルを生成 |
| TS | `.ts` | tsmuxer用のmetaファイルを生成 |
| TSREPLACE | `.ts` | 中間ベース名に映像コーデック用サフィックスを付ける場合がある |

関連して、Windows GUIの出力ファイル探索フォールバックは `.mp4`、`.mkv`、`.ts` だけを検索しており、`.m2ts` を含まない。これは入力判定ではないが、M2TS出力をGUIで再検出する場合の別の確認事項である。
