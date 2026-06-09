"""
Term Sheet Auto-Analyzer using Google Gemini API
과제: LLM 기반 장외파생상품 Term Sheet 자동 분석 및 제안서 생성 시스템

무료 API: https://aistudio.google.com → Get API Key
설치: pip install google-generativeai
실행: python analyzer_gemini.py
"""

import google.generativeai as genai
import json, re, os

# ── API 키 설정 ──────────────────────────────
# aistudio.google.com 에서 발급한 키를 아래에 입력
GEMINI_API_KEY = "여기에_Gemini_API_키_입력"
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

# ─────────────────────────────────────────────
# PROMPT 1: 핵심 조건 추출
# ─────────────────────────────────────────────
EXTRACTION_PROMPT = """You are an expert OTC derivatives analyst at a Korean securities firm.
Extract the key terms from the term sheet below and return ONLY valid JSON with these fields:
{{
  "product_type": "상품 유형",
  "parties": {{"party_a": "딜러/판매사", "party_b": "거래상대방"}},
  "underlying": "기초자산",
  "notional": "명목원금 (통화 포함)",
  "trade_date": "거래일",
  "maturity": "만기일",
  "coupon_or_return": "쿠폰/수익구조 요약",
  "knock_out_or_early_term": "조기상환/KO 조건 (없으면 null)",
  "key_risks": ["리스크1", "리스크2", "리스크3"],
  "governing_law": "준거법",
  "settlement": "결제 방식"
}}
Return ONLY the JSON object. No markdown, no explanation.

TERM SHEET:
{text}"""

# ─────────────────────────────────────────────
# PROMPT 2A: 전문투자자용 제안서
# ─────────────────────────────────────────────
PRO_PROMPT = """당신은 한국 증권사의 장외파생상품 구조화 전문가입니다.
아래 장외파생상품 핵심 조건을 바탕으로 전문투자자(기관/전문투자자)용 상품 제안서를 작성하세요.

[작성 지침]
- 투자 목적 및 구조 요약 (2~3문장)
- 주요 조건 표 (상품유형, 기초자산, 명목원금, 만기, 수익구조)
- 리스크 요인 3가지 (간결하게)
- 투자 포인트 1~2문장
- 전문 금융 용어(ISDA, KO, Barrier 등) 사용 가능
- 한국어로 작성

[핵심 조건]
{extracted_json}"""

# ─────────────────────────────────────────────
# PROMPT 2B: 일반투자자용 안내문
# ─────────────────────────────────────────────
RETAIL_PROMPT = """당신은 금융소비자보호법을 준수하는 금융 상담사입니다.
아래 장외파생상품 조건을 일반투자자가 이해할 수 있도록 쉽게 설명하세요.

[작성 지침]
- 이 상품이 무엇인지 쉬운 말로 설명 (비유 활용 권장)
- 어떤 경우에 수익이 나는지 설명
- 어떤 경우에 손실이 나는지 명확히 경고
- ⚠️ 원금손실 가능성 및 투자 전 주의사항 반드시 포함 (금소법 준수)
- 중학생도 이해할 수 있는 쉬운 한국어 사용
- 전문 용어 최소화

[핵심 조건]
{extracted_json}"""


def call_gemini(prompt: str) -> str:
    """Gemini API 호출"""
    response = model.generate_content(prompt)
    return response.text.strip()


def extract_terms(text: str) -> dict:
    """Step 1: Term Sheet에서 핵심 조건 추출"""
    print("  [Step 1] 핵심 조건 추출 중...")
    raw = call_gemini(EXTRACTION_PROMPT.format(text=text[:6000]))
    # JSON 파싱 (```json 블록 제거)
    raw = re.sub(r"```json\s*", "", raw)
    raw = re.sub(r"```\s*", "", raw)
    m = re.search(r"\{[\s\S]*\}", raw)
    return json.loads(m.group()) if m else {"raw": raw}


def generate_pro_proposal(extracted: dict) -> str:
    """Step 2A: 전문투자자용 제안서 생성"""
    print("  [Step 2A] 전문투자자용 제안서 생성 중...")
    return call_gemini(PRO_PROMPT.format(
        extracted_json=json.dumps(extracted, ensure_ascii=False, indent=2)
    ))


def generate_retail_proposal(extracted: dict) -> str:
    """Step 2B: 일반투자자용 안내문 생성"""
    print("  [Step 2B] 일반투자자용 안내문 생성 중...")
    return call_gemini(RETAIL_PROMPT.format(
        extracted_json=json.dumps(extracted, ensure_ascii=False, indent=2)
    ))


def analyze_termsheet(name: str, text: str) -> dict:
    """단일 Term Sheet 전체 파이프라인 실행"""
    print(f"\n{'='*60}")
    print(f"분석 대상: {name}")
    print('='*60)
    extracted = extract_terms(text)
    print(f"  ✓ 추출 완료: {extracted.get('product_type', 'N/A')}")
    pro = generate_pro_proposal(extracted)
    print(f"  ✓ 전문투자자 제안서 완료 ({len(pro)}자)")
    retail = generate_retail_proposal(extracted)
    print(f"  ✓ 일반투자자 안내문 완료 ({len(retail)}자)")
    return {"name": name, "extracted": extracted,
            "pro_proposal": pro, "retail_proposal": retail}


def print_results(results: list):
    """결과 출력"""
    for r in results:
        print(f"\n{'='*60}")
        print(f"[{r['name']}]")
        print(f"\n[추출 조건]\n{json.dumps(r['extracted'], ensure_ascii=False, indent=2)}")
        print(f"\n[전문투자자용 제안서]\n{r['pro_proposal']}")
        print(f"\n[일반투자자용 안내문]\n{r['retail_proposal']}")

    # JSON 저장
    with open("analysis_results.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print("\n\n결과 저장 완료: analysis_results.json")


# ─────────────────────────────────────────────
# 분석 대상 Term Sheet 샘플
# ─────────────────────────────────────────────
SAMPLE_TERMSHEETS = {
    "ELS형 OTC Swap (Nomura/BNK)": """
Product: [005930 KS Equity, KOSPI2 Index] Linked OTC Swap Transaction
Party A: Nomura Financial Investment (Korea) Co., Ltd.
Party B: BNK Securities Co., Ltd.
Trade Date: 20-Feb-2025 / Maturity: 25-Feb-2028 (3년)
Basket: Samsung Electronics (005930 KS) + KOSPI2 Index
Equity Notional Amount: KRW 800,000,000
Floating Rate: KRW-CD 91D + 0.20%
Periodic Coupon: 0.35% per observation (Coupon Strike: 85% of Initial Price)
Knock-out Event: Closing Price >= Trigger Level on any Knock-out Day
Equity Amount at Maturity: 0% (원금 미보장)
Settlement: Cash KRW / Governing Law: English law / ISDA Master Agreement
""",
    "EUA Forward Swap (Citi/신한)": """
Product: EU Allowances (EUA) Forward Starting Swap
Party A: Citigroup Global Markets Limited / Party B: Shinhan Securities
Commodity: EU Allowances (EUAs) - EU ETS Phase 4
Futures Contract A: ICE EUA Futures Dec 2024
Futures Contract B: ICE EUA Futures Dec 2025
Interim Expiry: 16 December 2024 / Termination: 15 December 2025
Settlement: Cash or Physical (EUA delivery)
Governing Law: English law / Exchange: ICE Endex
Risk: EUA 가격 변동성, EU ETS 규제 변경, Hedging Disruption
""",
    "KTB Bond Forward (Goldman/BNK)": """
Product: Cash-Settled Maturity Matched Bond Forward
Buyer: BNK Securities / Seller: Goldman Sachs International (GSI)
Trade Date: March 27, 2026
Reference Securities: 3% 2-Year Korea Treasury Bonds (KR103502GG38)
Maturity: March 10, 2028
Notional Amount: KRW 100,000,000,000 (1,000억원)
Forward Dirty Price: 99.90%
Payment Conversion: KRW → USD (USDKRW Reuters KFTC18 at 3:30pm Seoul)
Independent Amount (Margin): 1.0% of Notional
Governing Law: ISDA Master Agreement
"""
}


if __name__ == "__main__":
    print("장외파생상품 Term Sheet 자동 분석 시스템")
    print("LLM: Gemini 2.0 Flash (Google)")
    print("="*60)

    all_results = []
    for name, text in SAMPLE_TERMSHEETS.items():
        result = analyze_termsheet(name, text)
        all_results.append(result)

    print_results(all_results)
    print("\n분석 완료.")
