# Amatsukaze Linux GUI

GTK 4 / PyGObjectで実装した、AmatsukazeServerのタスク追加用GUIです。

## 起動

ServerCLIを起動した状態で、配布物のランチャーを実行します。

```sh
GDK_BACKEND=wayland ./AmatsukazeLinuxGUI.sh
```

## Ubuntuのアプリ一覧・Dockへ登録

配布物のルートで次を一度実行すると、現在のユーザーのアプリ一覧へ登録されます。登録先は `XDG_DATA_HOME`（未設定時は `~/.local/share`）です。

```sh
./AmatsukazeLinuxGUI.sh --install-desktop
```

アプリ一覧から「Amatsukaze Linux GUI」を起動し、Dockのアイコンを右クリックして「お気に入りに追加」を選ぶとDockへ固定できます。DockのFavorites設定はスクリプトから変更しません。

登録を削除する場合は次を実行します。

```sh
./AmatsukazeLinuxGUI.sh --uninstall-desktop
```

初期接続先は `http://127.0.0.1:32769` です。接続設定画面からRESTポートを変更できます。接続先は安全のためループバックアドレスだけを受け付けます。

入力対象は、現行QueueManagerの条件に合わせて `.ts` と `.m2t` です。`.m2ts` はGUIで除外します。複数ファイルを選択・ドロップすると、同一設定の1件の `AddQueueRequest` として送信されます。

Dockerで使用する場合は、GUIから見える入力・出力の絶対パスをコンテナー内でも同じパスで参照できるようにbind mountしてください。例えば `/mnt:/mnt` です。
