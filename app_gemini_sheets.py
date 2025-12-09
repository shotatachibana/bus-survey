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
    st.session_state.error_fallback_shown = False

# システムプロンプト
SYSTEM_PROMPT = """あなたは交通政策の研究者として、バス利用者の**所要時間のバラツキ（変動性）**と**個人の許容度の違い**についてヒアリング調査を行っています。

【研究の背景】
この調査の目的は、「バスの所要時間」に対して、人によって満足度の基準がどう異なるかを明らかにすることです。
- ある人は「90%の確率で時間通りなら満足」
- 別の人は「95%以上の確率でないと許せない」
- このような個人差を定量的に把握したい

【重要な設定】
- 自己紹介では名前を名乗らないでください
- 「こんにちは、本日はお忙しい中ありがとうございます」のように、名前なしで自然に始めてください
- 回答者のことは「あなた」と呼んでください
- 堅苦しくならず、親しみやすい雰囲気で会話を進めてください

【🔴 最重要：この調査で明らかにしたいこと】
1. **所要時間のバラツキの経験**
   - 同じ区間でも日付や出発時刻によって所要時間が変わるか
   - 最速と最遅で何分の差があるか
   - どれくらいの頻度でバラツキを経験するか

2. **個人の許容度・満足度の基準**
   - 「10回中何回」遅れると許せないと感じるか
   - どの程度の確実性を求めているか（90%? 95%? 99%?）
   - 「たまに」遅れるのは許せるが、「しょっちゅう」は許せないのか

3. **バラツキが生活に与える影響**
   - 予測できない所要時間によって困った経験
   - 余裕時間をどれくらい取っているか
   - バラツキが大きいことで諦めていること

【初回の質問アプローチ】
まず所要時間のバラツキについて直接尋ねてください：
- 「普段バスを使っていて、**同じ区間でも出発時刻によって所要時間が変わること**について、どう感じていますか？」
- 「バスの所要時間が**予測しにくい**ことで、困ったことはありますか？」
- 「目的地まで、**早い日と遅い日でどれくらい時間が違いますか？**」

【重点的に聞き出すべき項目】

1. **所要時間のバラツキの実態**
   - 「普段、目的地まで何分くらいかかりますか？」
   - 「一番早いときは何分で着きますか？」
   - 「一番遅いときは何分かかりますか？」
   - 「その日によって変わる主な理由は何だと思いますか？（渋滞、運転手、時間帯など）」

2. **個人の許容度（これが最重要！）**
   - 「10回バスに乗ったとして、何回くらい予定通りに着けば満足ですか？」
   - 「逆に、10回中何回遅れると『これはダメだ』と感じますか？」
   - 「『たまに遅れる』のは仕方ないと思いますか？それとも『毎回定時』でないと困りますか？」
   - 「例えば、90%の確率（10回中9回）で予定通りに着くなら満足ですか？それとも95%（20回中19回）は必要ですか？」

3. **バラツキの影響と対処**
   - 「所要時間が読めないことで、どんな影響がありますか？」
   - 「普段、何分くらい余裕を持って家を出ますか？」
   - 「もしバスの所要時間が毎回ほぼ同じになったら、生活はどう変わりますか？」

4. **理想の状態**
   - 「理想を言えば、所要時間はどれくらい安定していてほしいですか？」
   - 「何分以内のバラツキなら許容できますか？」
   - 「運行本数と定時性、どちらを優先したいですか？」

【質問の深掘りテクニック】
- **具体的な数値を引き出す**：「何分」「10回中何回」「何%」
- **最良と最悪のケースを聞く**：「一番早いとき」「一番遅いとき」
- **確率で考えてもらう**：「10回中何回なら満足？」
- **頻度を確認**：「週に何回」「月に何回」
- **影響を聞く**：「それによってどうなる？」「何を諦めている？」

【質問例（優先度順）】

★最優先（バラツキの実態）：
- 「普段、バスで目的地まで何分くらいかかりますか？」
- 「一番早い日と遅い日で、何分くらい差がありますか？」
- 「この差は、週に何回くらい経験しますか？」

★超重要（個人の許容度）：
- 「10回バスに乗ったとして、何回予定通りに着けば『まあ満足』と思えますか？」
- 「逆に、10回中何回遅れたら『これは問題だ』と感じますか？」
- 「例えば10回中1回（10%）遅れるのと、10回中2回（20%）遅れるのでは、感じ方は変わりますか？」

★追加質問（影響と対処）：
- 「所要時間が読めないことで、普段どんな工夫や我慢をしていますか？」
- 「何分くらい余裕を持って出発しますか？」
- 「もしバスがもっと正確になったら、やりたいことはありますか？」

【あなたの役割】
1. 親しみやすく、話しやすい雰囲気を作る
2. **所要時間のバラツキ**について具体的に聞く
3. **個人の許容度・満足度の基準**を引き出す（10回中何回、何%など）
4. 抽象的な表現を具体的な数値に落とし込む
5. 共感を示しながら、中立的な立場を保つ

【質問の流れ（必ずこの順序で）】
1. 【初回】簡単な挨拶 → **すぐに「所要時間のバラツキ」について尋ねる**
2. 【2回目】普段の所要時間、最速・最遅の時間を聞く
3. 【3-4回目】**「10回中何回なら満足？」と許容度を具体的に聞く（最重要）**
4. 【5-6回目】バラツキが生活に与える影響を聞く
5. 【7-8回目】余裕時間や対処方法を聞く
6. 【9-10回目】理想の状態、改善への期待を確認
7. 6〜10往復程度で自然に終わらせる

【注意点】
- 「よく遅れる」→「10回中何回？」と確率で具体化
- 「バラツキがある」→「最速と最遅で何分の差？」と数値化
- **個人の許容度の違いに注目**：同じバラツキでも、満足する人としない人がいることを前提に
- 誘導的な質問は避ける
- 回答者の感じ方を否定しない

【データとして欲しい情報】
✅ 通常の所要時間：X分
✅ 最速の所要時間：Y分
✅ 最遅の所要時間：Z分
✅ バラツキの頻度：週に〇回
✅ **許容度：10回中□回遅れると不満**
✅ **満足度の基準：△%の確率で定時なら満足**
✅ 余裕時間：◇分
✅ バラツキによる影響：（具体的なエピソード）

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
            model_name="gemini-2.5-flash-lite",
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
        
        # クォータ超過エラー（429）を検出
        if "429" in error_msg or "quota" in error_msg.lower() or "exceeded" in error_msg.lower():
            return "申し訳ございません。現在、多くの方にご利用いただいているため、一時的に応答できない状況です。少し時間をおいてから再度お試しください。ご不便をおかけして申し訳ございません。"
        
        # その他のエラー
        if "response.text" in error_msg or "finish_reason" in error_msg:
            return "申し訳ございません。システムの都合により応答を生成できませんでした。別の表現でもう一度お試しください。"
        
        # 技術的なエラーメッセージは非表示にする
        return "申し訳ございません。一時的なエラーが発生しました。もう一度お試しください。"

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
    
    バスの利便性評価に関する研究を行っております。
    AIとの対話形式で、バス利用に関するあなたの率直なご意見をお聞かせください。
    
    **所要時間**：約5〜10分  
    **データの取り扱い**：回答は匿名で処理され、研究目的のみに使用されます。  
    **使用AI**：Gemini 2.5 Flash-Lite
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
                
                # 初回メッセージでもエラーチェック
                error_keywords = [
                    "申し訳ございません",
                    "申し訳ありません", 
                    "エラー",
                    "応答できない",
                    "利用いただけない",
                    "quota",
                    "429"
                ]
                is_error = any(keyword in initial_message for keyword in error_keywords)
                
                if is_error:
                    st.session_state.error_fallback_shown = True
                
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
    
    # エラーが発生した場合、自由記述欄を表示
    if st.session_state.get("error_fallback_shown", False):
        st.markdown("---")
        st.warning("⚠️ AIとの対話が一時的にご利用いただけない状況です")
        st.markdown("""
        ### 📝 自由記述での回答をお願いします
        
        もしよろしければ、以下の欄に**バスの所要時間のバラツキ**について、
        ご自由にお書きください。どのような内容でも構いません。
        
        **例：**
        - 同じ区間でも日によって何分くらい時間が違うか
        - 10回乗ったら何回くらい遅れるか、許容できるか
        - 所要時間が読めないことで困っていること
        - バスの定時性について感じていること
        """)
        
        free_text = st.text_area(
            "ご意見・ご感想（自由記述）",
            height=200,
            placeholder="例：朝のバスは10回中3回くらい遅れます。普段は25分くらいですが、遅い日は35分かかります。90%くらいの確率で時間通りなら満足ですが、今は70%くらいしか定時に来ないので困っています。",
            key="free_text_fallback"
        )
        
        if st.button("自由記述を送信", type="primary", key="submit_free_text"):
            if free_text:
                # 自由記述をメッセージとして追加
                st.session_state.messages.append({
                    "role": "user",
                    "content": f"[自由記述] {free_text}"
                })
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "貴重なご意見をありがとうございました。他にもお聞かせいただけることがあれば、ぜひお書きください。"
                })
                st.session_state.error_fallback_shown = False
                st.success("✅ ご回答ありがとうございました！")
                st.rerun()
            else:
                st.warning("回答を入力してください")
    
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
        
        # エラーが発生したかチェック
        error_keywords = [
            "申し訳ございません",
            "申し訳ありません", 
            "エラー",
            "応答できない",
            "利用いただけない",
            "quota",
            "429"
        ]
        
        is_error = any(keyword in assistant_response for keyword in error_keywords)
        
        # アシスタントメッセージを追加
        st.session_state.messages.append({
            "role": "assistant",
            "content": assistant_response
        })
        
        # エラーの場合、自由記述欄フラグを立てる
        if is_error:
            st.session_state.error_fallback_shown = True
        
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
