# Linux向けAmatsukazeServerのビルド手順

## 必要なツールと依存パッケージのインストール

```bash
sudo apt update
sudo apt install -y build-essential git wget curl nasm cmake meson ninja-build pkg-config autoconf automake libtool \
    libssl-dev libz-dev python3 python3-gi gir1.2-gtk-4.0 libgtk-4-1
```
次に .NET 10.0 SDKをインストールします。下記はUbuntu 24.04の例を示します。その他の環境については、[リンク先](https://learn.microsoft.com/ja-jp/dotnet/core/install/linux)を参照してください。

```bash
# .NET
wget https://packages.microsoft.com/config/ubuntu/24.04/packages-microsoft-prod.deb -O packages-microsoft-prod.deb
sudo dpkg -i ./packages-microsoft-prod.deb
sudo apt update
sudo apt install -y dotnet-sdk-10.0
dotnet workload install wasm-tools --skip-manifest-update
```

`AmatsukazeWebUI` は Blazor WebAssembly を publish するため、`wasm-tools` workload がないと
`Publishing without optimizations...` という警告が表示され、WebUI が非最適化で公開されます。

## AviSynthのインストール

Linuxでは、AviSynth+をインストールする必要があります。[こちら](https://github.com/rigaya/AviSynthCUDAFilters/releases)から最新版のdebパッケージをダウンロードしてインストールしてください。

```bash
sudo apt install -y ./avisynth_<version>_amd64_Ubuntuxx.xx.deb
```

自ビルドする場合は[こちら](https://github.com/rigaya/AviSynthCUDAFilters/blob/master/README_LINUX.md)を参考にしてください。

## Amatsukaze本体のビルド

下記では、Amatsukazeを ```$HOME/Amatsukaze``` にインストールする例を示します。

```./scripts/build.sh``` により下記が自動的に実行されます。

- AmatsuakzeCLI, libAmatsukaze.soのビルド (C++)
  - 依存するffmpeg関連ライブラリのビルドを含む
- AmatsuakzeServer, AmatsuakzeServerCLI, AmatsuakzeAddTask のビルド (C# dotnet)
- WebUI静的ファイルの公開と配置 (`exe_files/wwwroot`)
- インストール先への実行ファイルの配置
- GTK 4/PyGObject版Linux GUIの構文検査・単体テストと配置 (`exe_files/AmatsukazeLinuxGUI`)

```bash
git clone https://github.com/Oomugi413/Amatsukaze.git --recursive
cd Amatsukaze
./scripts/build.sh $HOME/Amatsukaze
```


## 各Avisynthプラグインへのリンクの作成
  
実際にAmatsuakzeを使用するには、各種Avisynthプラグインをインストール後、```exe_files/plugins64```にそのリンクを作成する必要があります。

```./scripts/install.sh```を実行するとインストール済みの各Avisynthプラグインへのリンクが```exe_files/plugins64```に自動的に作成されます。

```bash
cd $HOME/Amatsukaze
./scripts/install.sh
```

## Linux GUI

ServerCLIを起動した状態で、インストール先のランチャーを実行します。

```bash
cd $HOME/Amatsukaze
GDK_BACKEND=wayland ./AmatsukazeLinuxGUI.sh
```

初期接続先は `http://127.0.0.1:32769` です。GUIは入力として `.ts` と `.m2t` を受け付け、`.m2ts` は現行QueueManagerの条件に合わせて除外します。PyGObject/GTK 4が見つからない場合は、上記の実行依存パッケージを確認してください。

### Ubuntuのアプリ一覧・Dockへの登録

ビルド・インストール後、配布物のルートで次を一度実行すると、現在のユーザーのアプリ一覧へ登録されます。

```bash
cd $HOME/Amatsukaze
./AmatsukazeLinuxGUI.sh --install-desktop
```

アプリ一覧から「Amatsukaze Linux GUI」を起動し、起動したアイコンを右クリックして「お気に入りに追加」を選ぶとDockへ固定できます。登録の削除は次のコマンドです。

```bash
./AmatsukazeLinuxGUI.sh --uninstall-desktop
```

登録スクリプトはroot権限を要求せず、`XDG_DATA_HOME`（未設定時は `~/.local/share`）へデスクトップエントリとアイコンを配置します。
