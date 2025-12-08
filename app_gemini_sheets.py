import streamlit as st
import google.generativeai as genai
import pandas as pd
from datetime import datetime
import uuid
import os
import json
import gspread
from google.oauth2.service_account import Credentials

# ページ設定
st.set_page_config(
    page_title="バス利用に関するヒアリング調査",
    page_icon="🚌",
    layout="centered"
)

# APIキーの設定（環境変数から読み込み）
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# Google Sheets設定
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

# セッション状態の初期化
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
    st.session_state.messages = []
    st.session_state.user_info = {}
    st.session_state.survey_started = False
    st.session_state.survey_completed = False
    st.session_state.chat = None
    st.session_state.sheets_client = None
    st.session_state.spreadsheet = None

# システムプロンプト
SYSTEM_PROMPT = """あなたは交通政策の研究者として、バス利用者の不満や課題についてヒアリング調査を行っています。

【重要な設定】
- 自己紹介では名前を名乗らないでください
- 「こんにちは、本日はお忙しい中ありがとうございます」のように、名前なしで自然に始めてください
- 回答者のことは「あなた」と呼んでください
- 堅苦しくならず、親しみやすい雰囲気で会話を進めてください

【調査の目的】
バスのダイヤ（運行本数・時刻）、所要時間、定時性に関する具体的な不満や問題点を深く理解すること

【重点的に聞き出すべき項目】
1. **ダイヤ・運行頻度**
   - 待ち時間が長すぎる（何分待つのか）
   - 本数が少ない（朝/昼/夕方/夜の時間帯別に）
   - 時刻表がわかりにくい
   - 乗りたい時間に便がない（具体的に何時頃）

2. **所要時間**
   - 目的地まで時間がかかりすぎる（何分かかるのか、理想は何分か）
   - 渋滞で遅れる（どの区間・時間帯か）
   - 遠回りのルート（どこを通るのか）
   - 停留所の数が多すぎて遅い

3. **定時性・遅延**
   - 時刻表通りに来ない（何分遅れるのか、頻度は）
   - 早発（予定時刻より早く出発してしまう）
   - 到着時刻が読めない（通勤・通学への影響）
   - 遅延の理由（渋滞、運転手不足など）

4. **乗り継ぎ・接続**
   - 乗り継ぎ時間が長い（何分待つのか）
   - 接続が悪い（電車やほかのバスとの連携）
   - 乗り継ぎ場所が不便

【質問の深掘りテクニック】
- 「具体的に何分くらい」と数値を引き出す
- 「いつ頃」「何時台」と時間帯を特定する
- 「週に何回くらい」と頻度を確認する
- 「どの路線・区間」と場所を特定する
- 「それによってどんな影響が」と結果を聞く

【質問例】
- 「バスを待つとき、平均どれくらい待ちますか？」
- 「理想的には何分間隔で来てほしいですか？」
- 「目的地まで実際は何分かかって、本当は何分で着きたいですか？」
- 「時刻表より何分くらい遅れることが多いですか？」
- 「遅れは週に何回くらい経験しますか？」

【あなたの役割】
1. 親しみやすく、話しやすい雰囲気を作る
2. 抽象的な不満を具体的な数値や状況に落とし込む
3. 「いつ」「どこで」「何分」「週何回」といった定量情報を引き出す
4. 1回の質問は1〜2つに絞り、回答者の負担を減らす
5. 共感を示しながら、中立的な立場を保つ

【質問の流れ（柔軟に対応）】
- バス利用の目的と頻度を確認
- よく使う路線・時間帯を特定
- ダイヤ・運行本数の不満を聞く（具体的な数値を引き出す）
- 所要時間や遅延の問題を深掘り（何分かかるか、何分遅れるか）
- 理想の状態を聞く（何分間隔、何分で到着など）
- 改善への優先順位や期待を確認
- 6〜10往復程度で自然に終わらせる

【注意点】
- 堅苦しくならず、会話形式で進める
- 「よく遅れる」→「週に何回くらい？」「何分くらい？」と具体化
- 「時間がかかる」→「何分かかる？」「理想は何分？」と数値化
- 回答者が話したいことを優先しつつ、上記の項目を自然に聞き出す
- 誘導的な質問は避ける

回答は簡潔に、1〜3文程度にしてください。"""

def initialize_google_sheets():
    """Google Sheetsクライアントを初期化"""
    try:
        # Streamlit Secretsから認証情報を取得
        if "gcp_service_account" in st.secrets:
            credentials = Credentials.from_service_account_info(
                st.secrets["gcp_service_account"],
                scopes=SCOPES
            )
            client = gspread.authorize(credentials)
            
            # スプレッドシートを開く（URLまたはキーで指定）
            if "spreadsheet_url" in st.secrets:
                spreadsheet = client.open_by_url(st.secrets["spreadsheet_url"])
            elif "spreadsheet_key" in st.secrets:
                spreadsheet = client.open_by_key(st.secrets["spreadsheet_key"])
            else:
                return None, "スプレッドシートのURLまたはキーが設定されていません"
            
            return spreadsheet, None
        else:
            return None, "Google Cloud認証情報が設定されていません"
    
    except Exception as e:
        return None, f"Google Sheets初期化エラー: {str(e)}"

def save_to_google_sheets(spreadsheet):
    """対話履歴をGoogle Sheetsに保存"""
    try:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # 要約シートに保存
        try:
            summary_sheet = spreadsheet.worksheet("summary")
        except:
            # シートがなければ作成
            summary_sheet = spreadsheet.add_worksheet(title="summary", rows="1000", cols="10")
            # ヘッダー行を追加
            summary_sheet.append_row([
                "session_id", "timestamp", "age_group", "usage_frequency", 
                "location", "message_count", "completed"
            ])
        
        # 要約データを追加
        summary_sheet.append_row([
            st.session_state.session_id,
            timestamp,
            st.session_state.user_info.get("age_group", ""),
            st.session_state.user_info.get("usage_frequency", ""),
            st.session_state.user_info.get("location", "未記入"),
            len(st.session_state.messages),
            "完了"
        ])
        
        # 詳細シートに対話履歴を保存
        try:
            detail_sheet = spreadsheet.worksheet("details")
        except:
            # シートがなければ作成
            detail_sheet = spreadsheet.add_worksheet(title="details", rows="10000", cols="10")
            # ヘッダー行を追加
            detail_sheet.append_row([
                "session_id", "timestamp", "age_group", "usage_frequency",
                "location", "message_number", "role", "content"
            ])
        
        # 各メッセージを保存
        for i, msg in enumerate(st.session_state.messages):
            detail_sheet.append_row([
                st.session_state.session_id,
                timestamp,
                st.session_state.user_info.get("age_group", ""),
                st.session_state.user_info.get("usage_frequency", ""),
                st.session_state.user_info.get("location", "未記入"),
                i + 1,
                msg["role"],
                msg["content"]
            ])
        
        return True, None
    
    except Exception as e:
        return False, f"保存エラー: {str(e)}"

def initialize_chat():
    """Gemini チャットセッションを初期化"""
    if not GEMINI_API_KEY:
        return None
    
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        
        # モデルの設定
        generation_config = {
            "temperature": 0.7,
            "top_p": 0.95,
            "top_k": 40,
            "max_output_tokens": 1024,
        }
        
        # セーフティ設定（バス調査は安全な内容なので緩和）
        safety_settings = [
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_ONLY_HIGH"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_ONLY_HIGH"
            }
        ]
        
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-exp",
            generation_config=generation_config,
            safety_settings=safety_settings,
            system_instruction=SYSTEM_PROMPT
        )
        
        chat = model.start_chat(history=[])
        return chat
    
    except Exception as e:
        st.error(f"チャット初期化エラー：{str(e)}")
        return None

def get_gemini_response(user_message):
    """Gemini APIを呼び出して応答を取得"""
    if not GEMINI_API_KEY:
        return "エラー：APIキーが設定されていません。"
    
    try:
        # チャットセッションがなければ初期化
        if st.session_state.chat is None:
            st.session_state.chat = initialize_chat()
            if st.session_state.chat is None:
                return "エラー：チャットセッションを初期化できませんでした。"
        
        # メッセージを送信して応答を取得
        response = st.session_state.chat.send_message(user_message)
        
        # 応答が正常に生成されたか確認
        if response.parts:
            return response.text
        else:
            # 応答が生成されなかった場合の詳細を確認
            finish_reason = getattr(response.candidates[0], 'finish_reason', None) if response.candidates else None
            
            # フィルタリングされた可能性がある場合
            if finish_reason == 2:  # SAFETY
                return "申し訳ございません。システムの都合により応答を生成できませんでした。別の表現で入力いただけますでしょうか。"
            elif finish_reason == 3:  # MAX_TOKENS
                return "応答が長すぎたため、途中で切れてしまいました。もう一度お試しください。"
            else:
                return f"応答の生成に失敗しました。もう一度お試しください。（理由コード: {finish_reason}）"
    
    except AttributeError as e:
        # response.text が存在しない場合
        return "申し訳ございません。応答を生成できませんでした。もう一度お試しください。"
    
    except Exception as e:
        error_msg = str(e)
        if "response.text" in error_msg or "finish_reason" in error_msg:
            return "申し訳ございません。システムの都合により応答を生成できませんでした。別の表現でもう一度お試しください。"
        return f"エラーが発生しました：{error_msg}"

# メインUI
st.title("バス利用に関するヒアリング調査")

# Google Sheets初期化（初回のみ）
if st.session_state.spreadsheet is None:
    spreadsheet, error = initialize_google_sheets()
    if spreadsheet:
        st.session_state.spreadsheet = spreadsheet
    elif error:
        st.error(f"⚠️ Google Sheets接続エラー: {error}")
        st.info("""
        **セットアップが必要です：**
        1. Google Cloud Platformでサービスアカウントを作成
        2. Streamlit SecretsにJSON認証情報を設定
        3. スプレッドシートをサービスアカウントと共有
        
        詳細は SETUP_SHEETS.md を参照してください。
        """)
        st.stop()

# APIキーの確認
if not GEMINI_API_KEY:
    st.warning("⚠️ APIキーが設定されていません")
    st.info("👉 Google AI StudioでAPIキーを取得: https://makersuite.google.com/app/apikey")
    api_key_input = st.text_input("Gemini APIキーを入力してください：", type="password")
    if api_key_input:
        GEMINI_API_KEY = api_key_input
        genai.configure(api_key=GEMINI_API_KEY)
        st.success("✅ APIキーが設定されました！")
        st.rerun()
    st.stop()

# 調査開始前の基本情報入力
if not st.session_state.survey_started:
    st.markdown("""
    ### ご協力のお願い
    
    この調査は、バス交通の改善を目的とした学術研究です。
    AIとの対話形式で、バス利用に関するあなたの率直なご意見をお聞かせください。
    
    **所要時間**：約5〜10分  
    **データの取り扱い**：回答は匿名で処理され、研究目的のみに使用されます。  
    **使用AI**：Google Gemini 2.0 Flash
    """)
    
    with st.form("user_info_form"):
        st.subheader("基本情報")
        
        age_group = st.selectbox(
            "年齢層",
            ["選択してください", "10代", "20代", "30代", "40代", "50代", "60代", "70代以上"]
        )
        
        usage_frequency = st.selectbox(
            "バスの利用頻度",
            ["選択してください", "ほぼ毎日", "週に数回", "月に数回", "年に数回", "ほとんど利用しない"]
        )
        
        st.markdown("---")
        st.markdown("### お住まいの地域（任意）")
        st.caption("より地域に即した改善提案のため、差し支えなければご記入ください。")
        
        location_input = st.text_input(
            "お住まいの場所",
            placeholder="例：郵便番号（920-1192）、町名（角間町）、目印（金沢大学の近く）など",
            help="郵便番号、町字、近くの目印（駅名・大学名・商業施設など）のいずれかで構いません。入力は任意です。"
        )
        
        submitted = st.form_submit_button("調査を開始する")
        
        if submitted:
            if age_group == "選択してください" or usage_frequency == "選択してください":
                st.error("年齢層とバス利用頻度を選択してください。")
            else:
                st.session_state.user_info = {
                    "age_group": age_group,
                    "usage_frequency": usage_frequency,
                    "location": location_input if location_input else "未記入"
                }
                st.session_state.survey_started = True
                
                # チャットセッションを初期化
                st.session_state.chat = initialize_chat()
                
                # 初回メッセージ
                location_info = f"\n- お住まいの地域：{location_input}" if location_input else ""
                initial_context = f"""調査対象者の基本情報：
- 年齢層：{age_group}
- バス利用頻度：{usage_frequency}{location_info}

この情報を踏まえて、自然な挨拶と最初の質問をしてください。"""
                
                initial_message = get_gemini_response(initial_context)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": initial_message
                })
                st.rerun()

# 調査中の対話
elif st.session_state.survey_started and not st.session_state.survey_completed:
    st.markdown("---")
    
    # 対話履歴の表示
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
    
    # ユーザー入力
    user_input = st.chat_input("メッセージを入力してください...")
    
    if user_input:
        # ユーザーメッセージを追加
        st.session_state.messages.append({
            "role": "user",
            "content": user_input
        })
        
        # Gemini応答を取得
        with st.spinner("考え中..."):
            assistant_response = get_gemini_response(user_input)
        
        # アシスタントメッセージを追加
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        st.rerun()
    
    # 調査終了ボタン
    st.markdown("---")
    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("調査を終了", type="primary"):
            # Google Sheetsに保存
            with st.spinner("データを保存中..."):
                success, error = save_to_google_sheets(st.session_state.spreadsheet)
                if success:
                    st.session_state.survey_completed = True
                    st.rerun()
                else:
                    st.error(f"保存に失敗しました: {error}")

# 調査完了
else:
    st.success("✅ ご協力ありがとうございました！")
    st.markdown("""
    ### 調査完了
    
    お忙しい中、貴重なご意見をいただきありがとうございました。  
    いただいた情報は、バス交通の改善に向けた研究に活用させていただきます。
    
    """)
    
    if st.button("新しい調査を開始"):
        # セッションをリセット
        for key in list(st.session_state.keys()):
            if key not in ["spreadsheet", "sheets_client"]:  # Google Sheets接続は保持
                del st.session_state[key]
        st.rerun()
