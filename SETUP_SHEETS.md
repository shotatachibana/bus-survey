# Google Sheets版セットアップガイド

このガイドでは、調査データをGoogle Sheetsに保存し、Streamlit Cloudで公開する方法を説明します。

## 📋 目次

1. Google Cloudの設定（10分）
2. Google Sheetsの準備（3分）
3. Streamlit Cloudへのデプロイ（5分）
4. 動作確認とテスト

---

## 1. Google Cloudの設定

### ステップ1: Google Cloud Platformにアクセス

https://console.cloud.google.com/ にアクセスしてログイン

### ステップ2: 新しいプロジェクトを作成

1. 画面上部の「プロジェクトを選択」をクリック
2. 「新しいプロジェクト」をクリック
3. プロジェクト名：`bus-survey`（任意）
4. 「作成」をクリック

### ステップ3: Google Sheets APIを有効化

1. 左側メニュー → 「APIとサービス」 → 「ライブラリ」
2. 検索ボックスで「Google Sheets API」を検索
3. 「Google Sheets API」をクリック
4. 「有効にする」をクリック

### ステップ4: Google Drive APIも有効化

1. 同じく「ライブラリ」で「Google Drive API」を検索
2. 「Google Drive API」をクリック
3. 「有効にする」をクリック

### ステップ5: サービスアカウントを作成

1. 左側メニュー → 「APIとサービス」 → 「認証情報」
2. 「認証情報を作成」→「サービスアカウント」をクリック
3. サービスアカウント名：`bus-survey-bot`（任意）
4. 「作成して続行」をクリック
5. ロール：「編集者」を選択
6. 「完了」をクリック

### ステップ6: JSONキーをダウンロード

1. 作成したサービスアカウントをクリック
2. 「キー」タブをクリック
3. 「鍵を追加」→「新しい鍵を作成」
4. 「JSON」を選択して「作成」
5. **JSONファイルがダウンロードされます（重要！大切に保管）**

ダウンロードしたJSONファイルの例：
```json
{
  "type": "service_account",
  "project_id": "bus-survey-xxxxx",
  "private_key_id": "xxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...",
  "client_email": "bus-survey-bot@bus-survey-xxxxx.iam.gserviceaccount.com",
  ...
}
```

### ステップ7: サービスアカウントのメールアドレスをコピー

JSONファイル内の`client_email`の値をコピーしておきます。
例：`bus-survey-bot@bus-survey-xxxxx.iam.gserviceaccount.com`

---

## 2. Google Sheetsの準備

### ステップ1: 新しいスプレッドシートを作成

1. https://sheets.google.com/ にアクセス
2. 「空白」をクリックして新規スプレッドシート作成
3. 名前を「バス調査データ」などに変更

### ステップ2: サービスアカウントと共有

1. 右上の「共有」ボタンをクリック
2. 先ほどコピーしたサービスアカウントのメールアドレスを貼り付け
   例：`bus-survey-bot@bus-survey-xxxxx.iam.gserviceaccount.com`
3. 権限：「編集者」を選択
4. 「送信」をクリック（通知メールは不要）

### ステップ3: スプレッドシートのURLをコピー

ブラウザのアドレスバーからURLをコピーします。
例：`https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit`

---

## 3. Streamlit Cloudへのデプロイ

### ステップ1: GitHubにコードをアップロード

```bash
# プロジェクトディレクトリで実行
cd bus_survey
git init
git add app_gemini_sheets.py requirements_sheets.txt
git commit -m "Initial commit"

# GitHubで新しいリポジトリを作成後
git remote add origin https://github.com/YOUR_USERNAME/bus-survey.git
git push -u origin main
```

### ステップ2: Streamlit Cloudにデプロイ

1. https://streamlit.io/cloud にアクセス
2. GitHubアカウントでサインイン
3. 「New app」をクリック
4. 設定：
   - Repository: `YOUR_USERNAME/bus-survey`
   - Branch: `main`
   - Main file path: `app_gemini_sheets.py`
5. 「Deploy!」をクリック

### ステップ3: Secretsを設定

デプロイ後、アプリの設定画面で：

1. 右下の「⚙️」（設定）→「Secrets」をクリック
2. 以下を貼り付け（**自分の値に置き換えてください**）：

```toml
# Gemini API Key
GEMINI_API_KEY = "AIzaSyAklhSD19pkozORLqMZsoYsKiAvSAJrnmQ"

# Google Sheets URL
spreadsheet_url = "https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz1234567890/edit"

# Google Cloud Service Account (ダウンロードしたJSONファイルの内容をそのまま貼り付け)
[gcp_service_account]
type = "service_account"
project_id = "bus-survey-xxxxx"
private_key_id = "xxxxx"
private_key = "-----BEGIN PRIVATE KEY-----\nMIIEvQIBA...\n-----END PRIVATE KEY-----\n"
client_email = "bus-survey-bot@bus-survey-xxxxx.iam.gserviceaccount.com"
client_id = "xxxxx"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

**重要な注意点：**
- `private_key`の値は改行（`\n`）を含めてそのままコピー
- TOMLフォーマットなので、文字列は`"`で囲む
- `[gcp_service_account]`セクションはインデントなし

3. 「Save」をクリック
4. アプリが自動的に再起動します

---

## 4. 動作確認

### ステップ1: アプリにアクセス

デプロイされたURLにアクセス（例：`https://your-app.streamlit.app`）

### ステップ2: テスト調査を実施

1. 基本情報を入力
2. AIと数回対話
3. 「調査を終了」をクリック

### ステップ3: Google Sheetsで確認

1. 先ほど作成したGoogle Sheetsを開く
2. 新しいシート「summary」と「details」が自動作成されているはず
3. データが保存されていることを確認

**summaryシートの構造：**
| session_id | timestamp | age_group | usage_frequency | message_count | completed |
|------------|-----------|-----------|-----------------|---------------|-----------|
| uuid... | 2024-12-06 12:34:56 | 30代 | 週に数回 | 12 | 完了 |

**detailsシートの構造：**
| session_id | timestamp | age_group | usage_frequency | message_number | role | content |
|------------|-----------|-----------|-----------------|----------------|------|---------|
| uuid... | 2024-12-06 12:34:56 | 30代 | 週に数回 | 1 | assistant | こんにちは... |
| uuid... | 2024-12-06 12:34:56 | 30代 | 週に数回 | 2 | user | バスが遅れる... |

---

## 📊 データの分析

### Google Sheets上で直接分析

- ピボットテーブルで年齢層別集計
- フィルタ機能で特定の回答を抽出
- グラフ作成

### Excelでダウンロード

1. Google Sheetsで「ファイル」→「ダウンロード」→「Microsoft Excel」
2. Excelで開いて分析

### Pythonで分析

```python
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# 認証
credentials = Credentials.from_service_account_file(
    'path/to/service-account.json',
    scopes=['https://www.googleapis.com/auth/spreadsheets']
)
client = gspread.authorize(credentials)

# データ読み込み
spreadsheet = client.open('バス調査データ')
summary_sheet = spreadsheet.worksheet('summary')
details_sheet = spreadsheet.worksheet('details')

# DataFrameに変換
summary_df = pd.DataFrame(summary_sheet.get_all_records())
details_df = pd.DataFrame(details_sheet.get_all_records())

print(summary_df.head())
```

---

## 🎉 完成！

アプリのURLを調査対象者に共有すれば、誰でもアクセスして回答できます。

**公開URL例：**
`https://bus-survey.streamlit.app`

---

## トラブルシューティング

### エラー: "Google Sheets接続エラー"

**原因1**: サービスアカウントとスプレッドシートの共有ができていない
- 解決：スプレッドシートの共有設定を再確認

**原因2**: Secretsの設定が間違っている
- 解決：`gcp_service_account`のJSON形式を確認
- 特に`private_key`の改行（`\n`）が正しいか確認

**原因3**: APIが有効化されていない
- 解決：Google Sheets APIとGoogle Drive APIの有効化を確認

### エラー: "insufficient authentication scopes"

スコープが不足しています。
- `app_gemini_sheets.py`の`SCOPES`を確認
- サービスアカウントに「編集者」権限があるか確認

### データが保存されない

- ネットワークタブ（F12）でエラーを確認
- スプレッドシートのURLが正しいか確認
- サービスアカウントのメールアドレスが正しいか確認

---

## セキュリティに関する注意

- **JSONキーは絶対に公開しない**（GitHubにコミットしない）
- `.gitignore`に`*.json`を追加
- Streamlit Secretsは安全（暗号化されている）
- スプレッドシートは調査者（あなた）のみがアクセス可能

---

## 次のステップ

1. ✅ テスト調査で動作確認
2. ✅ URLを調査対象者に共有
3. ✅ リアルタイムでGoogle Sheetsを確認
4. ✅ データが集まったら分析開始

何か問題があれば、いつでも相談してください！
