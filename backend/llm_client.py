"""
Chutes AI integration with retry logic, concurrent control, and Pydantic validation.
"""
import asyncio
import json
import os
from typing import Optional
import httpx
from dotenv import load_dotenv
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)
from pydantic import ValidationError

from schemas import ChatLLMOutput, PropertyRemark, RemarksResponse
from npp_enum import NPP_ENUM_FULL

# Load .env at module import (idempotent)
load_dotenv()

# Semaphore for LLM concurrent call limit
# Read from config.yaml in production
llm_semaphore = asyncio.Semaphore(3)

# FIX B5: read credentials from .env per Backend.md §2 instead of hardcoded placeholder.
CHUTES_AI_API_KEY = os.getenv("CHUTES_AI_API_KEY", "")
CHUTES_AI_BASE_URL = os.getenv("CHUTES_AI_BASE_URL", "https://llm.chutes.ai/v1")

if not CHUTES_AI_API_KEY:
    print(
        "[llm_client] WARNING: CHUTES_AI_API_KEY is empty. "
        "Set it in backend/.env before calling LLM endpoints."
    )


class LLMClient:
    def __init__(self, api_key: str = CHUTES_AI_API_KEY, base_url: str = CHUTES_AI_BASE_URL):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=5, min=5, max=20),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        reraise=True,
    )
    async def _call_api(self, payload: dict) -> dict:
        """
        Internal API call with exponential backoff: 5s → 10s → 20s.
        Raises on final failure.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        response = await self.client.post(
            f"{self.base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()

    async def chat(self, messages: list[dict], model: str = "deepseek-ai/DeepSeek-V3-0324") -> ChatLLMOutput:
        """
        Call Chutes AI for chat with structured JSON output.
        Returns validated ChatLLMOutput or raises exception.
        """
        async with llm_semaphore:
            try:
                payload = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": 2000,
                    "response_format": {"type": "json_object"},
                }

                response = await self._call_api(payload)

                # Extract content from response
                content = response["choices"][0]["message"]["content"]
                parsed = json.loads(content)

                # Validate with Pydantic
                output = ChatLLMOutput(**parsed)
                return output

            except ValidationError as e:
                # Validation failure - return degraded response
                print(f"LLM output validation failed: {e}")
                raise
            except Exception as e:
                print(f"LLM call failed: {e}")
                raise

    async def semantic_alignment(self, description: str) -> dict[str, list[str]]:
        """
        Identify BOTH positive and negative property preferences.

        The LLM is the sole authority on validity and polarity. We do NOT
        constrain output to PPP_ENUM_FULL / NPP_ENUM_FULL — the existing
        enums are passed only as hints / canonical naming examples so the
        model prefers known keys when the concept matches.

        Returns {"positive": [...tags...], "negative": [...tags...]}.
        On any failure returns {"positive": [], "negative": []}.
        """
        from positive_enum import PPP_ENUM_FULL

        # Escape description so embedded quotes don't break the prompt JSON
        safe_desc = json.dumps(description, ensure_ascii=False)

        ppp_hint = list(PPP_ENUM_FULL.keys())
        npp_hint = list(NPP_ENUM_FULL.keys())

        messages = [
            {
                "role": "user",
                "content": f"""
你是一個房產偏好標籤分類器。從用戶輸入中同時識別「正面偏好（PPP）」與「負面偏好（NPP）」。

用戶輸入：{safe_desc}

# 極性判斷規則
1. 顯式信號：
   - 否定（→ negative）：「不要 / 沒有 / 避免 / 拒絕 / 不想 / no / without / avoid / dealbreaker」
   - 肯定（→ positive）：「要 / 必須 / 希望 / 需要 / want / need / must have / prefer」
2. 隱式信號：用戶輸入若為純名詞清單（如 "condo, east-facing, security"），
   且上下文無法判斷，**預設視為 negative（dealbreakers）**，因為此欄位即「要避開的事項」。
   一旦同一輸入中出現任一肯定關鍵詞，則改回逐項按語義判斷。
3. 同一概念若同時出現否定與肯定（如 "no west-facing, want east-facing"），各取對應極性。

# 標籤命名規則
- snake_case，全小寫，不含空格、連字符、引號。
- 例：east-facing → east_facing；need security → needs_security；no pool → no_pool。
- 屬性類型詞（condo / apartment / landed / terrace / bungalow / studio）**不是偏好**，
  忽略，不要輸出。
- 不確定的詞寧可丟掉，**禁止編造**。

# 命名提示（非強制白名單，僅供風格對齊；遇到等價概念請優先用這些 key）
常見 positive key 示例：{ppp_hint}
常見 negative key 示例：{npp_hint}
若用戶語義與上述任一 key 等價（不論大小寫/空格/連字符差異），輸出該 key。
若用戶提出列表外的合理偏好，自行用 snake_case 命名輸出即可。

# 輸出格式
僅輸出 JSON，不要任何說明文字或 markdown 圍欄：
{{"positive": ["needs_security"], "negative": ["east_facing"]}}
若該極性無命中：對應陣列為 []。
                """,
            }
        ]

        try:
            payload = {
                "model": "deepseek-ai/DeepSeek-V3-0324",
                "messages": messages,
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
            }

            response = await self._call_api(payload)
            content = response["choices"][0]["message"]["content"]
            print(f"[semantic_alignment] raw LLM content: {content!r}")
            parsed = json.loads(content)

            def _normalize(raw) -> list[str]:
                if not isinstance(raw, list):
                    return []
                out: list[str] = []
                seen: set[str] = set()
                for item in raw:
                    if not isinstance(item, str):
                        continue
                    key = item.strip().lower().replace("-", "_").replace(" ", "_")
                    if not key or key in seen:
                        continue
                    seen.add(key)
                    out.append(key)
                return out

            pos = _normalize(parsed.get("positive", []))
            neg = _normalize(parsed.get("negative", []))
            print(f"[semantic_alignment] normalized → positive={pos} negative={neg}")
            return {"positive": pos, "negative": neg}

        except Exception as e:
            print(f"[semantic_alignment] failed: {e}")
            return {"positive": [], "negative": []}


    async def generate_remarks(
        self,
        properties: list,
        agent_style: str = "professional",
    ) -> RemarksResponse:
        """
        Generate AI remarks for Top 10 properties in single LLM call.
        Returns validated RemarksResponse.
        """
        # FIX B6: original f-string had the tier ternary INSIDE the string literal,
        # so the LLM received the literal source text. Evaluate it outside the f-string.
        def _tier_label(p) -> str:
            return "tier_1" if getattr(p, "tier", None) == "tier_1" else "tier_2"

        props_summary = "\n".join([
            f"ID: {p.property_id}, Title: {p.title}, Price: {p.price}, "
            f"Tier: {_tier_label(p)}, "
            f"Features: {', '.join(p.feature_tags)}"
            for p in properties
        ])

        messages = [
            {
                "role": "user",
                "content": f"""
為以下房源生成 AI 評論。

代理風格：{agent_style}

房源列表：
{props_summary}

要求：
- Tier 1 房源：正向推薦，missing_features 為空列表，remedy 為 null
- Tier 2 房源：防禦性敘述，坦誠說明瑕疵，提供 remedy
- 洪水高風險必須主動披露

輸出格式：
{{
  "results": [
    {{
      "property_id": "JB001",
      "tier": "tier_1",
      "remarks": "...",
      "missing_features": [],
      "remedy": null
    }},
    ...
  ]
}}
            """,
            }
        ]

        try:
            payload = {
                "model": "deepseek-ai/DeepSeek-V3-0324",
                "messages": messages,
                "max_tokens": 2000,
                "response_format": {"type": "json_object"},
            }

            response = await self._call_api(payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            # Validate with Pydantic
            remarks_response = RemarksResponse(**parsed)
            return remarks_response

        except ValidationError as e:
            print(f"Remarks validation failed: {e}")
            raise
        except Exception as e:
            print(f"Remarks generation failed: {e}")
            raise

    async def map_rejection_to_npp(self, rejection_reasons: list[str]) -> list[str]:
        """
        Map rejection reasons to NPP_ENUM tags.
        Used in reject_all flow.
        """
        reasons_text = "\n".join([f"- {r}" for r in rejection_reasons])

        messages = [
            {
                "role": "user",
                "content": f"""
用戶拒絕了多個房源，提供的原因如下：

{reasons_text}

任務：將上述原因映射至以下 NPP 標籤集中的合適項目（內部 key）。
合法標籤集：{list(NPP_ENUM_FULL.keys())}

輸出格式：JSON 物件，例如 {{"tags": ["high_floor", "west_facing"]}}
若無明確映射，返回 {{"tags": []}}
                """,
            }
        ]

        try:
            payload = {
                "model": "deepseek-ai/DeepSeek-V3-0324",
                "messages": messages,
                "max_tokens": 500,
                "response_format": {"type": "json_object"},
            }

            response = await self._call_api(payload)
            content = response["choices"][0]["message"]["content"]
            parsed = json.loads(content)

            tags = parsed.get("tags", [])
            valid_tags = [t for t in tags if t in NPP_ENUM_FULL]
            return valid_tags

        except Exception as e:
            print(f"NPP mapping failed: {e}")
            return []


# Global LLM client instance
llm_client = LLMClient()

