# 2回目PAT確認・Dockerローカルビルド対応

- Codex session ID: `019f86fb-e9f2-79a2-bd81-49f5c7d89220`
- 対象: `20260722_メーデー！９：航空機事故の真実と真相[二].ts`

## 変更概要

- 録画先頭の最初のPATに指定サービスがない場合、直ちに失敗せず、事前解析と同じ別位置でPATを再確認する処理を追加した。
- 再確認でサービスを検出した場合は先頭から通常解析を継続し、検出できない場合のみ従来どおりエラーにする。最初の判定が後続PATで上書きされないよう、判定前は64 KiB単位で読み込む。
- DockerイメージをGitHub Releases APIの配布物ではなく、cloneしたローカル作業ツリーからAmatsukaze本体・Server・CLI・Web UIまでビルドする構成へ変更した。
- Composeのbuild contextをリポジトリルートに変更し、`.dockerignore`と`docker/readme.md`を追加・更新した。依存ビルドはDockerレイヤーへ分離してキャッシュする。
- runtime依存導入前に`install.sh`を実行していたため、`QPClip`を提供する`KFM.so`など6本のCUDAプラグインリンクが欠落していた。runtime側で再実行し、全必須プラグインの存在確認をビルド条件に追加した。

## 確認結果

- 対象TSで、最初のPATではサービス343がなく、別位置のPATで検出後にTS解析が継続することをログで確認した。
- `docker buildx build --check -f docker/Dockerfile .`は警告なし。
- `docker compose -f docker/compose.yml build amatsukaze`は成功。
- 生成イメージ内で全必須AviSynthプラグイン、リンク切れなし、共有ライブラリ依存不足なし、`KFM.so`内の`QPClip`を確認した。
- 検証時の生成イメージ: `sha256:6b9c9337a8f82d936195e3bee19208aa3c36db3c6942cd661970861b1d1326bb`

関連コミット: `55ed51e`（`Add 2nd PAT Try and local docker build`）、マージコミット: `cb70eb0`
