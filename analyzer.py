"""
Term Sheet Auto-Analyzer using Claude API
과제: LLM 기반 장외파생상품 Term Sheet 자동 분석 및 제안서 생성 시스템

파이프라인:
  1. Term Sheet 텍스트 입력
  2. Step 1: 핵심 조건 추출 (상품유형, 만기, 쿠폰/수익구조, 기초자산, 주요 리스크)
  3. Step 2A: 전문투자자용 제안서 생성
  4. Step 2B: 일반투자자용 제안서 생성 (금소법 준수 톤)
  5. 결과 출력 및 비교
"""

import anthropic
import json

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

# ─────────────────────────────────────────────
# PROMPT 1: 핵심 조건 추출
# ─────────────────────────────────────────────
EXTRACTION_SYSTEM = """You are an expert OTC derivatives analyst at a Korean securities firm.
Your task is to extract the key terms from a given term sheet and return them as structured JSON.
Return ONLY valid JSON — no markdown, no explanation, no preamble."""

EXTRACTION_USER_TEMPLATE = """Extract the key terms from the following term sheet.
Return a JSON object with EXACTLY these fields:

{{
  "product_type": "상품 유형 (예: ELS형 OTC Swap, EUA Forward Swap, KTB Bond Forward 등)",
  "parties": {{
    "party_a": "딜러/판매사",
    "party_b": "거래상대방/매수인"
  }},
  "underlying": "기초자산 (예: Samsung Electronics + KOSPI200)",
  "notional": "명목원금 (통화 포함)",
  "trade_date": "거래일",
  "maturity": "만기일",
  "coupon_or_return": "쿠폰/수익구조 요약",
  "knock_out_or_early_term": "조기상환/KO 조건 (없으면 null)",
  "key_risks": ["리스크1", "리스크2", "리스크3"],
  "governing_law": "준거법",
  "settlement": "결제 방식"
}}

TERM SHEET TEXT:
---
{text}
---"""

# ─────────────────────────────────────────────
# PROMPT 2A: 전문투자자용 제안서
# ─────────────────────────────────────────────
PRO_SYSTEM = """You are a derivatives structurer writing a concise product proposal
for a professional investor (기관투자자, 전문투자자) at a Korean securities firm.
Write in Korean. Be precise, technical, and concise. Max 300 words."""

PRO_USER_TEMPLATE = """아래 장외파생상품 핵심 조건을 바탕으로 전문투자자용 상품 제안서를 작성하세요.

[작성 지침]
- 투자 목적 및 구조 요약 (2~3문장)
- 주요 조건 표 (상품유형, 기초자산, 명목원금, 만기, 수익구조)
- 리스크 요인 (3가지, 간결하게)
- 투자 포인트 (1~2문장)
- 전문적 금융 용어 사용 가능
- 분량: 250~300자 이내 (표 제외)

[핵심 조건]
{extracted_json}"""

# ─────────────────────────────────────────────
# PROMPT 2B: 일반투자자용 제안서
# ─────────────────────────────────────────────
RETAIL_SYSTEM = """You are a compliance-aware financial advisor writing a product explanation
for a retail investor (일반투자자) in Korea.
Write in Korean. Use plain language (중학생도 이해할 수 있는 수준).
Always include a clear risk warning. Follow 금융소비자보호법 tone. Max 300 words."""

RETAIL_USER_TEMPLATE = """아래 장외파생상품 핵심 조건을 바탕으로 일반투자자용 상품 안내문을 작성하세요.

[작성 지침]
- 이 상품이 무엇인지 쉬운 말로 설명 (비유 활용 권장)
- 어떤 경우에 수익이 나는지 설명
- 어떤 경우에 손실이 나는지 명확히 경고
- ⚠️ 원금손실 가능성 및 투자 전 주의사항 포함 (금소법 준수)
- 전문 용어 최소화, 쉬운 한국어 사용
- 분량: 250~300자 이내

[핵심 조건]
{extracted_json}"""


def extract_terms(text: str) -> dict:
    """Step 1: Term Sheet에서 핵심 조건 추출"""
    print("  [Step 1] 핵심 조건 추출 중...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=EXTRACTION_SYSTEM,
        messages=[{
            "role": "user",
            "content": EXTRACTION_USER_TEMPLATE.format(text=text[:6000])
        }]
    )
    raw = response.content[0].text.strip()
    # JSON 파싱 (```json 블록 제거)
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    return json.loads(raw)


def generate_pro_proposal(extracted: dict) -> str:
    """Step 2A: 전문투자자용 제안서 생성"""
    print("  [Step 2A] 전문투자자용 제안서 생성 중...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=PRO_SYSTEM,
        messages=[{
            "role": "user",
            "content": PRO_USER_TEMPLATE.format(
                extracted_json=json.dumps(extracted, ensure_ascii=False, indent=2)
            )
        }]
    )
    return response.content[0].text.strip()


def generate_retail_proposal(extracted: dict) -> str:
    """Step 2B: 일반투자자용 제안서 생성"""
    print("  [Step 2B] 일반투자자용 제안서 생성 중...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1000,
        system=RETAIL_SYSTEM,
        messages=[{
            "role": "user",
            "content": RETAIL_USER_TEMPLATE.format(
                extracted_json=json.dumps(extracted, ensure_ascii=False, indent=2)
            )
        }]
    )
    return response.content[0].text.strip()


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
    print(f"  ✓ 일반투자자 제안서 완료 ({len(retail)}자)")

    return {
        "name": name,
        "extracted": extracted,
        "pro_proposal": pro,
        "retail_proposal": retail
    }


def save_results(results: list, output_path: str = "analysis_results.json"):
    """결과를 JSON으로 저장"""
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n결과 저장: {output_path}")


def print_comparison(results: list):
    """전문 vs 일반 투자자 제안서 비교 출력"""
    print("\n" + "="*60)
    print("전문투자자 vs 일반투자자 제안서 비교")
    print("="*60)
    for r in results:
        print(f"\n[{r['name']}]")
        print(f"\n--- 전문투자자용 ---\n{r['pro_proposal']}")
        print(f"\n--- 일반투자자용 ---\n{r['retail_proposal']}")
        print("\n" + "-"*60)


# ─────────────────────────────────────────────
# 샘플 Term Sheet 텍스트 (실제 파일 대신 핵심 발췌)
# ─────────────────────────────────────────────
SAMPLE_TERMSHEETS = {
    "ELS형 OTC Swap (Nomura/BNK)": """
Product: [005930 KS Equity, KOSPI2 Index] Linked OTC Swap Transaction
Party A: Nomura Financial Investment (Korea) Co., Ltd.
Party B: BNK Securities Co., Ltd.
Trade Date: 20-Feb-2025
Effective Date: 26-Feb-2025
Termination Date: 25-Feb-2028 (3년)
Basket: Samsung Electronics Co Ltd (005930 KS) + KOSPI2 Index
Equity Notional Amount: KRW 800,000,000
Floating Rate: KRW-CD 91D + 0.20% spread
Periodic Coupon: 0.3500% per observation (월별 관찰)
  - Coupon Strike: 85% of Initial Price (각 기초자산)
Knock-out Event: Closing Price >= Trigger Level on any Knock-out Day
Equity Amount at Maturity: 0% (원금 미보장)
Settlement: Cash, KRW
Governing Law: English law / ISDA Master Agreement
Risk: 기초자산 하락시 원금손실, Knock-in 미발동시 쿠폰 미수령
""",

    "EUA Forward Swap (Citi/신한)": """
Product: EU Allowances (EUA) Forward Starting Swap
Party A: Citigroup Global Markets Limited (CGML)
Party B: Shinhan Securities
Trade Date: [TBD]
Notional Amount: EUR [TBD]
Commodity: EU Allowances (EUAs) - EU ETS Phase 4
Futures Contract A: ICE EUA Futures Dec 2024
Futures Contract B: ICE EUA Futures Dec 2025
Interim Expiry Date: 16 December 2024
Scheduled Termination Date: 15 December 2025
Floating Amount Formula: Notional * [(CRPB_Initial - CRPA_Initial) - (CRPB - CRPA)]
Settlement: Cash or Physical (EUA delivery)
Exchange: ICE Endex
Governing Law: English law
Risk: EUA 가격 변동성, EU ETS 규제 변경, Hedging Disruption
""",

    "KTB Bond Forward (Goldman/BNK)": """
Product: Cash-Settled Maturity Matched Bond Forward
Buyer: BNK Securities Co., Ltd.
Seller: Goldman Sachs International (GSI)
Trade Date: March 27, 2026
Reference Securities: 3% 2-Year Korea Treasury Bonds (KR103502GG38)
Maturity of Reference Securities: March 10, 2028
Notional Amount: KRW 100,000,000,000 (1,000억원)
Forward Dirty Price: 99.90%
Settlement Date: March 10, 2028
Cash Settlement Amount: Redemption Amount - Notional * Forward Clean Price
Payment Conversion: KRW → USD (USDKRW Reuters KFTC18 at 3:30pm Seoul)
Independent Amount (Margin): 1.0% of Notional
Early Termination: Korean sovereign default / law change / moratorium
Governing Law: ISDA Master Agreement
Risk: 금리 변동, 환율 변동(KRW/USD), 한국 국가신용리스크
"""
}


if __name__ == "__main__":
    print("장외파생상품 Term Sheet 자동 분석 시스템")
    print("LLM: Claude claude-sonnet-4-6 (Anthropic)")
    print("="*60)

    all_results = []
    for name, text in SAMPLE_TERMSHEETS.items():
        result = analyze_termsheet(name, text)
        all_results.append(result)

    save_results(all_results)
    print_comparison(all_results)
    print("\n분석 완료.")
