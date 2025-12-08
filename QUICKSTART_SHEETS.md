# Google Sheets版 - 簡易セットアップガイド

## 🚀 3ステップで公開

### ステップ1: Google Cloud設定（10分）

1. **Google Cloud Console**: https://console.cloud.google.com/
2. 新規プロジェクト作成：`bus-survey`
3. APIを有効化：
   - Google Sheets API
   - Google Drive API
4. サービスアカウント作成：
   - 名前：`bus-survey-bot`
   - ロール：「編集者」
5. **JSONキーをダウンロード**（重要！）
6. `client_email`をコピー：`xxx@xxx.iam.gserviceaccount.com`

### ステップ2: Google Sheets準備（3分）

1. **新規スプレッドシート作成**: https://sheets.google.com/
2. 名前：「バス調査データ」
3. **共有**ボタン → サービスアカウントのメールアドレスを追加
   - 権限：「編集者」
4. **スプレッドシートのURLをコピー**

### ステップ3: Streamlit Cloudデプロイ（5分）

1. **GitHubにプッシュ**:
```bash
git init
git add app_gemini_sheets.py requirements_sheets.txt
git commit -m "Initial commit"
git push origin main
```

2. **Streamlit Cloud**: https://streamlit.io/cloud
   - 「New app」
   - Repository選択
   - Main file: `app_gemini_sheets.py`
   - Deploy!

3. **Secrets設定** (⚙️ → Secrets):
```toml
GEMINI_API_KEY = "AIzaSy..."

spreadsheet_url = "https://docs.google.com/spreadsheets/d/..."

[gcp_service_account]
type = "service_account"
project_id = "bus-survey-xxxxx"
private_key_id = "xxxxx"
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "bus-survey-bot@bus-survey-xxxxx.iam.gserviceaccount.com"
client_id = "xxxxx"
auth_uri = "https://accounts.google.com/o/oauth2/auth"
token_uri = "https://oauth2.googleapis.com/token"
auth_provider_x509_cert_url = "https://www.googleapis.com/oauth2/v1/certs"
client_x509_cert_url = "https://www.googleapis.com/robot/v1/metadata/x509/..."
```

**重要**: JSONファイルの内容をそのまま貼り付け（改行含む）

---

## ✅ 完成！

アプリのURL（例：`https://your-app.streamlit.app`）を共有すれば調査開始！

データは自動的にGoogle Sheetsに保存されます。

---

## 📊 データ確認

Google Sheetsを開くと：
- **summary**シート：調査の要約
- **details**シート：全対話履歴

リアルタイムで確認・分析できます！

---

## 🆘 トラブル時

詳細は `SETUP_SHEETS.md` を参照してください。
