# LLM 기반 장외파생상품 Term Sheet 자동 분석 시스템

> 연세대학교 금융공학 대학원 | 머신러닝 기말과제 | 2025

## 개요

해외 IB로부터 수신한 장외파생상품 Term Sheet를 LLM(Claude)으로 자동 분석하여
전문투자자 및 일반투자자용 제안서를 생성하는 파이프라인입니다.

## 분석 대상 상품

| 상품 | 딜러 | 고객사 |
|------|------|--------|
| ELS형 OTC Swap | Nomura | BNK증권 |
| EUA Forward Swap | Citigroup | 신한증권 |
| KTB Bond Forward | Goldman Sachs | BNK증권 |

## 파이프라인 구조

```
Term Sheet (영문 PDF/DOCX)
    │
    ▼
[Step 1] 핵심 조건 추출  ← EXTRACTION_PROMPT
    │   상품유형, 기초자산, 만기, 수익구조, 리스크 등
    │
    ├──▶ [Step 2A] 전문투자자용 제안서  ← PRO_PROMPT
    │                (기술적·간결·ISDA 용어)
    │
    └──▶ [Step 2B] 일반투자자용 제안서  ← RETAIL_PROMPT
                     (쉬운 한국어·금소법 준수 경고)
```

## 실행 방법

```bash
# 의존성 설치
pip install anthropic

# API 키 설정
export ANTHROPIC_API_KEY="your-api-key"

# 실행
python analyzer.py
```

## 파일 구조

```
termsheet_analyzer/
├── analyzer.py          # 메인 파이프라인
├── analysis_results.json  # 분석 결과 (실행 후 생성)
└── README.md
```

## 프롬프트 설계 원칙

- **Step 1 (추출)**: JSON 형식 강제, 필드 명시, 할루시네이션 방지를 위해 원문 기반 추출만 허용
- **Step 2A (전문)**: 기술적 정확성 우선, ISDA/파생상품 용어 허용
- **Step 2B (일반)**: 중학생 수준 언어, 원금손실 경고 의무화, 금소법 준수 톤

## LLM 활용 도구

- **Model**: Claude claude-sonnet-4-6 (Anthropic)
- **API**: Anthropic Messages API
- **기술**: Zero-shot prompting + System prompt 분리 설계

## 한계 및 시사점

- 정량적 검증 부재 (추출 정확도 수동 확인 필요)
- 실제 Term Sheet의 법적 조항 전체 커버 어려움 (청크 크기 제한)
- 금소법 준수 여부는 전문가 검토 필요
