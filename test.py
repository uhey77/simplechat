# lambda/index.py  ─── すべて置き換え
import json
import os
import urllib.request
import urllib.error

# --------------------------------------------------------------------
# 環境変数
#   CDK の Lambda 環境変数で渡す。例:
# environment={"MODEL_API_URL": "https://467d-34-172-59-183.ngrok-free.app/generate"}
# --------------------------------------------------------------------
# MODEL_API_URL = os.environ.get("MODEL_API_URL")  # 末尾まで含める → .../generate
MODEL_API_URL = "https://3f56-34-16-218-226.ngrok-free.app/generate"
if not MODEL_API_URL:
    raise RuntimeError("環境変数 MODEL_API_URL が設定されていません")

# --------------------------------------------------------------------
# FastAPI (/generate) へ POST する関数
# --------------------------------------------------------------------
def call_local_llm(prompt: str,
                   max_new_tokens: int = 512,
                   temperature: float = 0.7,
                   top_p: float = 0.9,
                   timeout: int = 15) -> str:
    """
    Colab で立てた FastAPI の /generate エンドポイントを呼び出し
    戻り値: 生成テキスト（str）
    """
    payload = {
        "prompt": prompt,
        "max_new_tokens": max_new_tokens,
        "temperature": temperature,
        "top_p": top_p,
        "do_sample": True
    }

    data = json.dumps(payload).encode("utf-8")

    req = urllib.request.Request(
        MODEL_API_URL,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Model API returned status {resp.status}")
            body = json.load(resp)
            if "generated_text" not in body:
                raise RuntimeError("Model API response に 'generated_text' がありません")
            return body["generated_text"]
    except urllib.error.URLError as e:
        raise RuntimeError(f"モデル API 呼び出しに失敗しました: {e}") from e


# --------------------------------------------------------------------
# Lambda エントリーポイント
# --------------------------------------------------------------------
def lambda_handler(event, context):
    try:
        # ------------- リクエスト解析 -------------
        body = json.loads(event.get("body", "{}"))
        user_message = body["message"]                     # 必須
        history       = body.get("conversationHistory", [])  # 任意

        # ------------- プロンプト構築 -------------
        #
        # ここでは要件に合わせ **単純に直近メッセージだけ** を送る。
        # 发展: history をまとめて 1 つのテキストに連結して送るなども可。
        prompt_text = user_message

        # ------------- モデル呼び出し -------------
        assistant_reply = call_local_llm(prompt_text)

        # 履歴を更新して返す（クライアントが再利用できるように）
        history.append({"role": "user",      "content": user_message})
        history.append({"role": "assistant", "content": assistant_reply})

        # ------------- 成功レスポンス -------------
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                # CORS 設定
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
            },
            "body": json.dumps({
                "success": True,
                "response": assistant_reply,
                "conversationHistory": history,
            }),
        }

    # ---------------------------------------------------------------
    # 失敗時
    # ---------------------------------------------------------------
    except Exception as err:
        print("Error:", err)
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token",
                "Access-Control-Allow-Methods": "OPTIONS,POST",
            },
            "body": json.dumps({"success": False, "error": str(err)}),
        }

if __name__ == "__main__":
    event = {"body": json.dumps({"message": "こんにちは"})}
    print(lambda_handler(event, None))
