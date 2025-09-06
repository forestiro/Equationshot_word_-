# GitHub への SSH 設定と push 完全ガイド（macOS / 日本語）

目的: 「SSH とは何か」「鍵の作り方・登録の仕方」「GitHub への push の手順」を、1行ずつのターミナルコマンド中心で、超丁寧にまとめました。

---

## 1. SSH とは？（超ざっくり）
- **SSH**: ネット越しに安全に通信するためのプロトコル。
- **公開鍵/秘密鍵**: 鍵はペア。秘密鍵は手元に厳重保管、公開鍵はサーバ（GitHub）に登録。
- **仕組み**: GitHub は公開鍵を持ち、あなたの Mac は秘密鍵を持つ。両者が一致すれば本人確認OK。

---

## 2. まず現状確認（鍵の有無・指紋の確認）
- 鍵があるか確認（`id_ed25519.pub` があればOK）
```bash
ls -la ~/.ssh
```
- 公開鍵の中身を確認（1行で `ssh-ed25519 ... メールアドレス`）
```bash
cat ~/.ssh/id_ed25519.pub
```
- 公開鍵のフィンガープリント（SHA256）確認
```bash
ssh-keygen -lf ~/.ssh/id_ed25519.pub -E sha256
```

---

## 3. 新しく鍵を作る（まだ無い場合）
- Ed25519 方式で作成（推奨）。パスフレーズは任意（空でもOK）。
```bash
ssh-keygen -t ed25519 -C "あなたのメールアドレス"
```
- 公開鍵をクリップボードにコピー
```bash
pbcopy < ~/.ssh/id_ed25519.pub
```

---

## 4. GitHub に公開鍵を登録（必須）
- Web: GitHub → Settings → SSH and GPG keys → New SSH key
  - Title: 自分が分かる名前（例: MacBook-Air-5 (ed25519)）
  - Key type: Authentication Key
  - Key: `~/.ssh/id_ed25519.pub` の中身（1行の公開鍵）
- 正しい公開鍵の正式表記（例）
```text
ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAI...とても長いBase64... user@example.com
```
- 再掲: 公開鍵1行は「鍵タイプ」「Base64本体」「コメント（例: メール）」の3つを半角スペースで区切った形式。

---

## 5. macOS の ssh-agent / キーチェーン設定（便利）
- 設定ファイルを用意（無ければ作成）
```bash
mkdir -p ~/.ssh && chmod 700 ~/.ssh
```
```bash
cat > ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/id_ed25519
  IdentitiesOnly yes
  AddKeysToAgent yes
  UseKeychain yes
EOF
chmod 600 ~/.ssh/config
```
- エージェントに鍵を読み込む（起動→追加）
```bash
eval "$(ssh-agent -s)"
```
```bash
ssh-add ~/.ssh/id_ed25519
```

---

## 6. GitHub への接続確認
- 初回は `yes` を聞かれます（ホスト鍵登録）。成功すると "Hi <ユーザー名>!" が出ます。
```bash
ssh -T git@github.com
```

---

## 7. Git のユーザー設定（未設定なら）
```bash
git config --global user.name "あなたの表示名"
```
```bash
git config --global user.email "あなたのメールアドレス"
```

---

## 8. リポジトリの初期化 → 1回目の push（新規ディレクトリ）
- 例: カレントディレクトリを Git 管理下に
```bash
git init
```
- `.gitignore` を用意（例: macOSのゴミや動画を除外）
```bash
echo -e ".DS_Store\n*.mp4\n*.mov\n__pycache__/\n*.pyc" >> .gitignore
```
- すべて追加→コミット
```bash
git add .
```
```bash
git commit -m "Initial commit"
```
- ブランチを `main` に統一
```bash
git branch -M main
```
- GitHub の空リポジトリをリモートに設定（例）
```bash
git remote add origin git@github.com:<YOUR_NAME>/<REPO_NAME>.git
```
- 初回 push（追跡ブランチ設定込み）
```bash
git push -u origin main
```

---

## 9. 既存のリポジトリを push（.git が既にある場合）
- リモート設定を確認
```bash
git remote -v
```
- 無ければ追加
```bash
git remote add origin git@github.com:<YOUR_NAME>/<REPO_NAME>.git
```
- ブランチ名を `main` に揃える（必要なら）
```bash
git branch -M main
```
- push
```bash
git push -u origin main
```

---

## 10. よくあるエラーと対処
- Permission denied (publickey):
```bash
# 1) GitHub に公開鍵が登録されているか
ssh -T git@github.com
# 2) 秘密鍵の場所と設定が合っているか
cat ~/.ssh/config
# 3) 鍵をエージェントに読み込み済みか
ssh-add -l
# 4) 詳細ログで原因を探す
ssh -vT git@github.com
```
- private key invalid format（鍵の中身が壊れている/公開鍵を貼った等）:
```bash
# 先頭と末尾が以下の形式か（OpenSSH の例）
# -----BEGIN OPENSSH PRIVATE KEY-----
# ...（複数行のBase64）...
# -----END OPENSSH PRIVATE KEY-----
```
- Repository not found（URL間違い/権限無し）:
```bash
git remote -v
```
- ホスト鍵確認で止まる場合（初回）:
```bash
ssh -o StrictHostKeyChecking=accept-new -T git@github.com
```

---

## 11. 複数の鍵を使い分けたい（上級）
- 別名鍵 `~/.ssh/morimori` を GitHub 用に使う例
```bash
cat >> ~/.ssh/config << 'EOF'
Host github.com
  HostName github.com
  User git
  IdentityFile ~/.ssh/morimori
  IdentitiesOnly yes
  AddKeysToAgent yes
  UseKeychain yes
EOF
chmod 600 ~/.ssh/config
```
```bash
ssh-add ~/.ssh/morimori
```
```bash
ssh -T git@github.com
```

---

## 12. HTTPS に切り替える（SSHが使えない場合の回避）
```bash
git remote set-url origin https://github.com/<YOUR_NAME>/<REPO_NAME>.git
```
```bash
git push -u origin main
```

---

## 13. 付録（便利ワンライナー集）
- 公開鍵をクリップボードへ
```bash
pbcopy < ~/.ssh/id_ed25519.pub
```
- 公開鍵のSHA256フィンガープリント
```bash
ssh-keygen -lf ~/.ssh/id_ed25519.pub -E sha256
```
- ディレクトリ権限の修正
```bash
chmod 700 ~/.ssh && chmod 600 ~/.ssh/* 2>/dev/null || true
```
- `.DS_Store` を今後無視 + 追跡から外す
```bash
echo ".DS_Store" >> .gitignore && git rm --cached -f .DS_Store
```
- `.gitignore` 更新をコミット
```bash
git add .gitignore && git commit -m "chore: update .gitignore"
```
- リモートURLの確認/変更
```bash
git remote -v
```
```bash
git remote set-url origin git@github.com:<YOUR_NAME>/<REPO_NAME>.git
```
- ブランチ名の変更
```bash
git branch -M main
```
- Git LFS を使う（大容量ファイルに）
```bash
brew install git-lfs && git lfs install
```

---

## 14. このプロジェクトで実際にやったこと（参考）
- `id_ed25519.pub` を GitHub に登録
- `~/.ssh/config` で `IdentityFile ~/.ssh/id_ed25519` を設定
- 接続確認 `ssh -T git@github.com`
- 初回コミット → `origin` に `main` を push

困ったら、このファイルの該当セクションのコマンドを上から順に実行してください。ゆっくり確実に進めばOKです。
