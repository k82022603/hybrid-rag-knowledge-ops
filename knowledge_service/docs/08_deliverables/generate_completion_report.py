#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
프로젝트 완료 보고서 PPT 생성기
Hybrid RAG Knowledge Operations (2026-01-12 ~ 02-18)
Theme: Tech Innovation (테크 이노베이션)
"""

import sys
import os

# template.py 위치 추가
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '.claude', 'skills', 'enterprise-ppt-generator'))
from template import EnterprisePPTGenerator, FONT, FONT_NAME, PP_ALIGN, MSO_ANCHOR, RGBColor, Inches, Pt, MSO_SHAPE


class ProjectCompletionReport(EnterprisePPTGenerator):
    """프로젝트 완료 보고서 전용 생성기"""

    def create_content_slide(self, title, section, items, start_y=1.5):
        """텍스트 콘텐츠 슬라이드"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, title, section)
        y = start_y
        for item in items:
            if item.startswith("##"):
                # 소제목
                self.add_subtitle_box(slide, item.replace("## ", ""), y)
                y += 0.5
            elif item.startswith("- "):
                box = self.add_text_box(slide, 1.0, y, 11.3, 0.35, item, 11, self.theme['dark'])
                y += 0.35
            else:
                box = self.add_text_box(slide, 0.5, y, 12.3, 0.4, item, 12, self.theme['dark'], bold=True)
                y += 0.45
        return slide

    def create_kpi_slide(self, title, section, kpis):
        """KPI 카드 슬라이드"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, title, section)

        cols = min(len(kpis), 4)
        card_w = 2.8
        gap = 0.3
        start_x = (13.333 - (cols * card_w + (cols - 1) * gap)) / 2

        for i, (label, value, color_key) in enumerate(kpis[:4]):
            row = 0
            x = start_x + i * (card_w + gap)
            y = 1.5 + row * 2.8
            color = self.theme.get(color_key, self.theme['primary'])

            # 카드 배경
            card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                Inches(x), Inches(y), Inches(card_w), Inches(2.2))
            card.fill.solid()
            card.fill.fore_color.rgb = color
            card.line.fill.background()

            # 값
            val_box = slide.shapes.add_textbox(Inches(x + 0.1), Inches(y + 0.3), Inches(card_w - 0.2), Inches(1.0))
            p = val_box.text_frame.paragraphs[0]
            p.text = value
            p.font.size = Pt(36)
            p.font.bold = True
            p.font.color.rgb = RGBColor(255, 255, 255)
            p.font.name = FONT_NAME
            p.alignment = PP_ALIGN.CENTER

            # 라벨
            lbl_box = slide.shapes.add_textbox(Inches(x + 0.1), Inches(y + 1.4), Inches(card_w - 0.2), Inches(0.5))
            p2 = lbl_box.text_frame.paragraphs[0]
            p2.text = label
            p2.font.size = Pt(12)
            p2.font.color.rgb = RGBColor(255, 255, 255)
            p2.font.name = FONT_NAME
            p2.alignment = PP_ALIGN.CENTER

        # 두 번째 줄
        if len(kpis) > 4:
            for i, (label, value, color_key) in enumerate(kpis[4:8]):
                x = start_x + i * (card_w + gap)
                y = 4.2
                color = self.theme.get(color_key, self.theme['primary'])

                card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE,
                    Inches(x), Inches(y), Inches(card_w), Inches(2.2))
                card.fill.solid()
                card.fill.fore_color.rgb = color
                card.line.fill.background()

                val_box = slide.shapes.add_textbox(Inches(x + 0.1), Inches(y + 0.3), Inches(card_w - 0.2), Inches(1.0))
                p = val_box.text_frame.paragraphs[0]
                p.text = value
                p.font.size = Pt(36)
                p.font.bold = True
                p.font.color.rgb = RGBColor(255, 255, 255)
                p.font.name = FONT_NAME
                p.alignment = PP_ALIGN.CENTER

                lbl_box = slide.shapes.add_textbox(Inches(x + 0.1), Inches(y + 1.4), Inches(card_w - 0.2), Inches(0.5))
                p2 = lbl_box.text_frame.paragraphs[0]
                p2.text = label
                p2.font.size = Pt(12)
                p2.font.color.rgb = RGBColor(255, 255, 255)
                p2.font.name = FONT_NAME
                p2.alignment = PP_ALIGN.CENTER

        return slide

    def create_architecture_overview(self):
        """시스템 아키텍처 도식화"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "시스템 아키텍처", "III. 기술 구현")
        self.add_subtitle_box(slide, "Triple-Store + 4-Way Hybrid Search 아키텍처")

        # Frontend
        self.add_rounded_box(slide, 0.5, 1.6, 2.5, 0.7, "Frontend\nReact 18 + Tailwind", self.theme['box_fill2'], self.theme['dark'], 9)

        # API Gateway
        self.add_rounded_box(slide, 0.5, 2.5, 2.5, 0.7, "API Gateway\nSpring Cloud Gateway", self.theme['box_fill'], None, 9)

        # AI Service
        self.add_rounded_box(slide, 0.5, 3.4, 2.5, 0.7, "AI Service\nFastAPI + LangGraph", self.theme['box_fill3'], None, 9)

        # 화살표
        self.add_arrow(slide, 1.75, 2.3, 1.75, 2.5, self.theme['arrow'], 2)
        self.add_arrow(slide, 1.75, 3.2, 1.75, 3.4, self.theme['arrow'], 2)

        # Triple Store
        self.add_text_box(slide, 3.5, 1.5, 5.5, 0.35, "Triple-Store Architecture", 13, self.theme['accent'], True, PP_ALIGN.CENTER)

        # PostgreSQL
        self.add_rounded_box(slide, 3.5, 2.0, 1.7, 1.2, "PostgreSQL\n(SSOT)\n\nDocuments\nChunks\nUsers", RGBColor(51, 103, 145), None, 8, False)

        # Elasticsearch
        self.add_rounded_box(slide, 5.4, 2.0, 1.7, 1.2, "Elasticsearch\n(Vector+BM25)\n\nDense Vector\nSparse Vector\nNori", RGBColor(0, 169, 165), None, 8, False)

        # Neo4j
        self.add_rounded_box(slide, 7.3, 2.0, 1.7, 1.2, "Neo4j\n(Graph)\n\n92K Entities\n775K Relations", RGBColor(0, 131, 63), None, 8, False)

        # 4-Way Search
        self.add_text_box(slide, 3.5, 3.5, 5.5, 0.35, "4-Way Hybrid Search + RRF Fusion", 13, self.theme['accent'], True, PP_ALIGN.CENTER)

        searches = [("Dense", 3.5), ("Sparse", 5.0), ("BM25", 6.5), ("Graph", 8.0)]
        for name, x in searches:
            self.add_rounded_box(slide, x, 3.95, 1.3, 0.55, name, self.theme['box_fill'], None, 9)

        # RRF + Reranker
        self.add_rounded_box(slide, 4.5, 4.7, 3.5, 0.55, "RRF Fusion + BGE-Reranker", self.theme['box_fill3'], None, 10)

        # 화살표 from AI Service to stores
        self.add_arrow(slide, 3.0, 3.75, 3.5, 3.75, self.theme['arrow'], 2)

        # 설명 패널
        self.add_explanation_panel(slide, 9.3, 1.5, 3.7, 4.5, [
            "PostgreSQL이 문서 메타데이터의 Single Source of Truth",
            "ES가 벡터 + 전문검색 동시 지원 (Nori 한국어 분석기)",
            "Neo4j가 엔티티 관계 그래프 저장 및 서브그래프 질의",
            "4가지 검색을 RRF로 통합, Reranker로 최종 정렬",
            "DeepSeek V3.2로 LLM 비용 95% 절감 (GPT-4o 대비)",
        ], title="핵심 설계 포인트")

        return slide

    def create_etl_pipeline_slide(self):
        """3-Phase ETL 파이프라인"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "3-Phase ETL 파이프라인", "III. 기술 구현")
        self.add_subtitle_box(slide, "CPU/GPU 분리 전략으로 108K 청크 처리")

        # Phase 1
        self.add_text_box(slide, 0.5, 1.5, 3.5, 0.3, "Phase 1 (CPU)", 12, self.theme['primary'], True)
        self.add_rounded_box(slide, 0.5, 1.9, 1.5, 0.6, "문서 파싱\nDocling", self.theme['box_fill'], None, 9)
        self.add_arrow(slide, 2.0, 2.2, 2.2, 2.2, self.theme['arrow'], 2)
        self.add_rounded_box(slide, 2.2, 1.9, 1.5, 0.6, "청킹\n1000자 단위", self.theme['box_fill'], None, 9)
        self.add_arrow(slide, 3.0, 2.5, 3.0, 2.8, self.theme['arrow'], 2)
        self.add_rounded_box(slide, 0.5, 2.8, 3.2, 0.5, "ES + PG + Neo4j 저장", self.theme['box_fill3'], None, 9)

        # Phase 2
        self.add_text_box(slide, 4.5, 1.5, 3.5, 0.3, "Phase 2 (GPU/Colab)", 12, self.theme['primary'], True)
        self.add_rounded_box(slide, 4.5, 1.9, 1.5, 0.6, "Dense 임베딩\nko-sroberta", self.theme['box_fill2'], self.theme['dark'], 9)
        self.add_arrow(slide, 6.0, 2.2, 6.2, 2.2, self.theme['arrow'], 2)
        self.add_rounded_box(slide, 6.2, 1.9, 1.5, 0.6, "Sparse 임베딩\nBGE-M3", self.theme['box_fill2'], self.theme['dark'], 9)
        self.add_arrow(slide, 6.5, 2.5, 6.5, 2.8, self.theme['arrow'], 2)
        self.add_rounded_box(slide, 4.5, 2.8, 3.2, 0.5, "ES 임포트 (bulk)", self.theme['box_fill3'], None, 9)

        # Phase 3
        self.add_text_box(slide, 8.5, 1.5, 3.5, 0.3, "Phase 3 (CPU)", 12, self.theme['primary'], True)
        self.add_rounded_box(slide, 8.5, 1.9, 1.7, 0.6, "엔티티 추출\nDeepSeek V3.2", self.theme['box_fill'], None, 9)
        self.add_arrow(slide, 10.2, 2.2, 10.5, 2.2, self.theme['arrow'], 2)
        self.add_rounded_box(slide, 10.5, 1.9, 1.7, 0.6, "관계 구축\nNeo4j", self.theme['box_fill'], None, 9)
        self.add_arrow(slide, 10.5, 2.5, 10.5, 2.8, self.theme['arrow'], 2)
        self.add_rounded_box(slide, 8.5, 2.8, 3.7, 0.5, "92K 엔티티, 775K 관계", self.theme['box_fill3'], None, 9)

        # 실적 테이블
        self.add_table(slide,
            ["구분", "처리량", "소요시간", "비용"],
            [
                ["Phase 1 (파싱+청킹)", "597 문서 → 108K 청크", "~8시간 (CPU)", "$0"],
                ["Phase 2 (임베딩)", "108K 청크 × 768d + Sparse", "~2시간 (GPU)", "$0 (Colab)"],
                ["Phase 3 (엔티티)", "92K 엔티티, 775K 관계", "~40시간 (3워커)", "$52 (DeepSeek)"],
            ],
            start_y=3.8,
            col_widths=[2.5, 3.5, 3.0, 3.3]
        )

        return slide

    def create_agent_team_slide(self):
        """AI 에이전트 팀 구성"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "AI 에이전트 팀 협업", "IV. 프로젝트 운영")
        self.add_subtitle_box(slide, "1인 개발자 + 13개 AI 에이전트 = 가상 개발팀")

        # 사용자
        self.add_rounded_box(slide, 5.5, 1.5, 2.3, 0.6, "사용자 (PO)\n요구사항 + 의사결정", RGBColor(211, 47, 47), None, 9)
        self.add_arrow(slide, 6.65, 2.1, 6.65, 2.4, self.theme['arrow'], 2)

        # Claude (Main)
        self.add_rounded_box(slide, 5.0, 2.4, 3.3, 0.6, "Claude Code (Main)\nOpus 4.6 — 소통 + spawn/shutdown", self.theme['box_fill3'], None, 9)
        self.add_arrow(slide, 6.65, 3.0, 6.65, 3.3, self.theme['arrow'], 2)

        # 에이전트 그룹
        # 관리
        self.add_text_box(slide, 0.3, 3.3, 2.0, 0.25, "관리", 10, self.theme['primary'], True)
        self.add_rounded_box(slide, 0.3, 3.6, 1.4, 0.5, "PM\nSonnet 4.6", self.theme['box_fill2'], self.theme['dark'], 8)
        self.add_rounded_box(slide, 1.8, 3.6, 1.4, 0.5, "TechLead\nOpus 4.6", self.theme['box_fill'], None, 8)

        # 개발
        self.add_text_box(slide, 3.5, 3.3, 4.0, 0.25, "개발", 10, self.theme['primary'], True)
        devs = [("Backend", 3.5), ("Frontend", 4.85), ("RAG", 6.2), ("ETL", 7.55)]
        for name, x in devs:
            self.add_rounded_box(slide, x, 3.6, 1.25, 0.5, f"{name}\nSonnet 4.6", self.theme['box_fill2'], self.theme['dark'], 8)

        # 인프라/품질
        self.add_text_box(slide, 9.2, 3.3, 4.0, 0.25, "인프라 / 품질", 10, self.theme['primary'], True)
        infra = [("DB", 9.2), ("Infra", 10.25), ("DevOps", 11.3)]
        for name, x in infra:
            self.add_rounded_box(slide, x, 3.6, 0.95, 0.5, f"{name}\nSonnet 4.6", self.theme['box_fill2'], self.theme['dark'], 8)

        # 설계/문서/품질
        self.add_text_box(slide, 0.3, 4.4, 12.0, 0.25, "설계 / 문서 / 품질 / 디자인", 10, self.theme['primary'], True)
        others = [("Architect\nOpus 4.6", 0.3, self.theme['box_fill']),
                  ("QA\nSonnet 4.6", 2.3, self.theme['box_fill2']),
                  ("Doc\nSonnet 4.6", 4.3, self.theme['box_fill2']),
                  ("WebDesigner\nSonnet 4.6", 6.3, self.theme['box_fill2'])]
        for name, x, color in others:
            tc = None if color == self.theme['box_fill'] else self.theme['dark']
            self.add_rounded_box(slide, x, 4.7, 1.7, 0.5, name, color, tc, 8)

        # 설명 패널
        self.add_explanation_panel(slide, 9.0, 4.4, 4.0, 2.5, [
            "Opus 4.6: TechLead, Architect (심층 추론)",
            "Sonnet 4.6: 나머지 11개 (73% 비용 절감)",
            "PM은 조율만, 코딩 금지 (역할 분리)",
            "Slack/Jira 자동 연동 (MCP + Shell)",
        ], title="모델 티어링 전략")

        return slide

    def create_sprint_timeline_slide(self):
        """스프린트 타임라인"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "스프린트 타임라인", "IV. 프로젝트 운영")
        self.add_subtitle_box(slide, "38일간 12 스프린트 — 3일 단위 애자일")

        self.add_table(slide,
            ["Sprint", "기간", "주요 산출물", "상태"],
            [
                ["Sprint 01", "01/12~14", "프로젝트 셋업, Docker Compose 18컨테이너, ETL 기본 파이프라인", "완료"],
                ["Sprint 02", "01/15~17", "AI Service 핵심 API, Hybrid Search v1, 설계 문서 체계화", "완료"],
                ["Sprint 03", "01/18~22", "4-Way Hybrid Search, RRF Fusion, 프론트엔드 기본 UI", "완료"],
                ["Sprint 04", "01/23~25", "Tailwind 전환, Antigravity 도입, API Gateway 라우팅", "완료"],
                ["Sprint 05", "01/26~28", "PM 워크플로우, Agent Teams v1, 백로그 체계화", "완료"],
                ["Sprint 06", "01/29~31", "E2E 테스트, 기술부채 해소, Production-Ready 95.75%", "완료"],
                ["Sprint 07", "02/01~03", "Frontend 고도화, Graph Panel, 문서 업로드 UI", "완료"],
                ["Sprint 08", "02/04~07", "Unit Test 97%, Docker 최적화, Agent Teams v2", "완료"],
                ["Sprint 09", "02/08~10", "ETL v2 Full Re-Processing, 임베딩 108K 청크", "완료"],
                ["Sprint 10", "02/11~13", "RAGAS v7~v9, Nori 적용, Sparse Vector 복구", "완료"],
                ["Sprint 11", "02/14~16", "ETL 3-Phase 확립, Entity Extraction 92K, Graph Search", "완료"],
                ["Sprint 12", "02/17~18", "사용자 테스트, 산출물 9종 v1.1, 모델 티어링", "완료"],
            ],
            start_y=1.5,
            col_widths=[1.5, 1.5, 6.5, 0.8]
        )

        return slide

    def create_deliverables_slide(self):
        """산출물 목록"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "프로젝트 산출물", "V. 산출물")
        self.add_subtitle_box(slide, "9종 핵심 산출물 + 14종 프로젝트 가이드 문서")

        self.add_table(slide,
            ["No", "산출물", "버전", "경로", "비고"],
            [
                ["1", "상세 설계서", "v2.4", "docs/02_design/01_*.md", "Gleaning 포함"],
                ["2", "API 통합 설계서", "v1.2", "docs/02_design/04_*.md", "FastAPI + Gateway"],
                ["3", "인프라 설계서", "v1.1", "docs/02_design/10_*.md", "18개 컨테이너"],
                ["4", "테스트 계획서", "v1.0", "docs/04_testing/01_*.md", "TDD/Test-Along"],
                ["5", "RAGAS 평가 보고서", "v11", "docs/04_testing/12_*.md", "A- 등급"],
                ["6", "운영 매뉴얼", "v1.2", "docs/08_deliverables/03_*.md", "ETL 상세"],
                ["7", "사용자 매뉴얼", "v1.1", "docs/08_deliverables/02_*.md", ""],
                ["8", "소스코드 리뷰", "v1.0", "docs/08_deliverables/01_*.md", "B+ (72.5/100)"],
                ["9", "프로젝트 계획서", "v5.2", "PLAN.md", "Final"],
            ],
            start_y=1.5,
            col_widths=[0.5, 2.5, 0.8, 4.5, 2.0]
        )

        # 프로젝트 가이드 문서
        self.add_text_box(slide, 0.5, 5.5, 12.3, 0.35, "프로젝트 가이드 문서 (14종): docs/01_~12_ + 13_사업방법론 + 14_개발방법론", 10, self.theme['dark'])

        return slide

    def create_cost_slide(self):
        """비용 분석"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "비용 분석", "VI. 성과")
        self.add_subtitle_box(slide, "전체 운영 비용 $52 — DeepSeek V3.2 기반 95% 절감")

        self.add_table(slide,
            ["항목", "세부", "비용", "비고"],
            [
                ["LLM (DeepSeek V3.2)", "엔티티 추출 40시간", "$52", "GPT-4o 대비 95% 절감"],
                ["임베딩 (Colab GPU)", "BGE-M3 + ko-sroberta", "$0", "Google Colab 무료 GPU"],
                ["인프라 (Docker)", "18개 컨테이너 로컬", "$0", "개발 환경"],
                ["AI 에이전트 (Claude)", "Opus 4.6 + Sonnet 4.6", "별도", "Claude Code 구독"],
                ["Jira / Slack / GitHub", "SaaS 도구", "$0", "무료 티어"],
                ["합계", "", "$52+", ""],
            ],
            start_y=1.5,
            col_widths=[3.0, 3.0, 1.5, 4.8]
        )

        # GPT-4o 대비 비교
        self.add_explanation_panel(slide, 0.5, 5.0, 5.5, 2.0, [
            "GPT-4o로 동일 작업 시 추정 비용: ~$1,040",
            "DeepSeek V3.2 실제 비용: $52 (95% 절감)",
            "품질 차이: 무시할 수준 (RAGAS A- 등급)",
        ], title="비용 절감 효과")

        self.add_explanation_panel(slide, 6.5, 5.0, 6.5, 2.0, [
            "Claude Code: 개발 생산성 극대화 (38일 완주)",
            "Agent Teams: 13개 에이전트 병렬 작업",
            "Sonnet 4.6 전환: 에이전트 비용 73% 추가 절감",
        ], title="AI 도구 ROI")

        return slide

    def create_lessons_slide(self):
        """교훈 및 개선점"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "교훈 및 개선점", "VII. 회고")
        self.add_subtitle_box(slide, "38일간의 실전 경험에서 도출된 핵심 교훈")

        self.add_table(slide,
            ["사건", "기간", "원인", "교훈"],
            [
                ["Mock 테스트 사고", "02/05", "Mock 모드로 테스트 → 실제 품질 미검증", "반드시 Docker 환경에서 실제 테스트"],
                ["Nori 미적용 사고", "01/12~02/13\n(32일)", "ES Dockerfile 누락 → Nori 미설치", "설계서 ≠ 구현, E2E 검증 필수"],
                ["RAGAS NaN 27%", "02/13", "ragas 0.4.3 + DeepSeek n>1 미지원", "LLM API 제약사항 사전 확인"],
                ["능동적 대처 부족", "02/10", "사용자에게 불필요한 확인 질문", "실측 데이터 기반 즉시 실행"],
                ["우회 대신 근본 해결", "02/14", "docker cp 임시 대응, .dockerignore 미확인", "근본 원인 파악 후 올바른 해결"],
            ],
            start_y=1.5,
            col_widths=[2.2, 1.5, 4.0, 4.6]
        )

        # 핵심 원칙
        self.add_explanation_panel(slide, 0.5, 5.2, 12.3, 1.8, [
            '"설계서에 적혀 있다고 구현된 것이 아니다" — 반드시 실동작 E2E 검증',
            '"PM은 조율하고, 개발자가 구현한다" — 역할 분리 원칙 엄수',
            '"물어보지 말고 실행하라" — 실측 데이터로 판단 가능하면 즉시 실행 후 보고',
            '"귀찮은 것 빼먹지 마라" — 빠른 방법보다 올바른 방법 선택',
        ], title="핵심 원칙 (4가지)")

        return slide

    def create_conclusion_slide(self):
        """결론"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        self.add_header(slide, "결론", "VIII. 결론")

        # 성과 요약 박스
        self.add_rounded_box(slide, 0.5, 1.3, 12.3, 1.2,
            "1인 개발자 + Claude Code AI 에이전트 팀으로\n"
            "38일간 엔터프라이즈급 RAG 시스템을 설계/구현/테스트/문서화까지 완수",
            self.theme['box_fill3'], None, 16)

        # 4개 성과 카드
        achievements = [
            ("기술 성과", "4-Way Hybrid Search\nTriple-Store\n3-Phase ETL\nRAGAS A- 등급"),
            ("생산성 성과", "38일 12스프린트\n120+ 스토리\n97% 테스트 커버리지\n산출물 9종"),
            ("비용 성과", "LLM 비용 $52\n95% 절감 (vs GPT-4o)\nColab GPU 무료\n에이전트 73% 절감"),
            ("방법론 성과", "Agent Teams v3.1\n13개 AI 에이전트\n역할 분리 원칙\n자동화 워크플로우"),
        ]

        for i, (title, content) in enumerate(achievements):
            x = 0.5 + i * 3.15
            self.add_rounded_box(slide, x, 2.8, 2.95, 0.5, title, self.theme['box_fill'], None, 12)
            self.add_rounded_box(slide, x, 3.4, 2.95, 1.8, content, self.theme['light'], self.theme['dark'], 10, False)

        # 향후 과제
        self.add_text_box(slide, 0.5, 5.6, 12.3, 0.35, "향후 과제", 14, self.theme['accent'], True)
        self.add_table(slide,
            ["과제", "상태", "비고"],
            [
                ["K8s 배포", "미구현", "Docker Compose → K8s 전환 참조 설계 완료"],
                ["TLS/HTTPS", "미구현", "운영 환경 배포 시 적용"],
                ["Gleaning (반복 추출)", "미구현", "설계 검토 완료, 품질 대비 비용 판단 필요"],
                ["RBAC 세분화", "미구현", "Keycloak 기본 설정만 완료"],
            ],
            start_y=6.0,
            col_widths=[3.0, 1.5, 7.8]
        )

        return slide

    def create_thankyou_slide(self):
        """감사 슬라이드"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])

        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE,
            Inches(0), Inches(0), Inches(13.333), Inches(7.5))
        bg.fill.solid()
        bg.fill.fore_color.rgb = self.theme['cover_bg']
        bg.line.fill.background()

        deco = slide.shapes.add_shape(MSO_SHAPE.OVAL,
            Inches(9), Inches(4.5), Inches(5), Inches(4))
        deco.fill.solid()
        deco.fill.fore_color.rgb = self.theme['cover_deco']
        deco.line.fill.background()

        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(2.5), Inches(11), Inches(1.5))
        p = title_box.text_frame.paragraphs[0]
        p.text = "Thank You"
        p.font.size = Pt(52)
        p.font.bold = True
        p.font.color.rgb = self.theme['cover_title']
        p.font.name = FONT_NAME
        p.alignment = PP_ALIGN.CENTER

        sub_box = slide.shapes.add_textbox(Inches(0.8), Inches(4.2), Inches(11), Inches(0.8))
        sp = sub_box.text_frame.paragraphs[0]
        sp.text = "Hybrid RAG Knowledge Operations\n2026-01-12 ~ 2026-02-18"
        sp.font.size = Pt(18)
        sp.font.color.rgb = self.theme['light']
        sp.font.name = FONT_NAME
        sp.alignment = PP_ALIGN.CENTER

        return slide


def main():
    output_dir = os.path.dirname(os.path.abspath(__file__))
    output_path = os.path.join(output_dir, "00_project_completion_report.pptx")

    gen = ProjectCompletionReport(theme_id=3)  # Tech Innovation

    # 1. 표지
    gen.create_cover_slide(
        title="프로젝트 완료 보고서",
        subtitle="Hybrid RAG Knowledge Operations — Graph RAG 기반 지능형 지식 검색 시스템",
        date="2026-01-12 ~ 2026-02-18 (38일, 12 스프린트)"
    )

    # 2. 목차
    gen.create_toc_slide([
        "I.   프로젝트 개요",
        "II.  핵심 성과 지표 (KPI)",
        "III. 기술 구현 — 시스템 아키텍처",
        "IV.  기술 구현 — 3-Phase ETL 파이프라인",
        "V.   프로젝트 운영 — AI 에이전트 팀",
        "VI.  프로젝트 운영 — 스프린트 타임라인",
        "VII. 산출물",
        "VIII.비용 분석",
        "IX.  교훈 및 개선점",
        "X.   결론",
    ])

    # 3. 프로젝트 개요
    gen.create_comparison_slide(
        title="프로젝트 개요",
        section_title="I. 프로젝트 개요",
        subtitle="Graph RAG 기반 지능형 지식 검색 시스템",
        headers=["항목", "내용"],
        rows=[
            ["프로젝트명", "Hybrid RAG Knowledge Operations"],
            ["목적", "기업 내부 문서를 자동 처리하여 4-Way Hybrid Search + Knowledge Graph로 최적 검색 제공"],
            ["기간", "2026-01-12 ~ 2026-02-18 (38일, 12 스프린트)"],
            ["개발 체계", "1인 개발자 + Claude Code AI 에이전트 팀 (13개 에이전트)"],
            ["기술 스택", "Python 3.11 (FastAPI) + React 18 + SpringBoot 3.x + Docker Compose"],
            ["데이터베이스", "PostgreSQL (SSOT) + Elasticsearch 8.15 (Nori) + Neo4j (Graph)"],
            ["LLM", "DeepSeek V3.2 (런타임) + Claude Opus/Sonnet 4.6 (개발)"],
            ["인프라", "Docker Compose 18개 컨테이너 + Prometheus/Grafana/Kibana/Jaeger"],
            ["최종 상태", "사용자 테스트 완료, RAGAS A- 등급, 산출물 9종 v1.1 납품"],
        ]
    )

    # 4. KPI
    gen.create_kpi_slide("핵심 성과 지표", "II. KPI", [
        ("스프린트 완주", "12/12", "success"),
        ("테스트 커버리지", "97%", "primary"),
        ("RAGAS 등급", "A-", "accent"),
        ("비용 절감", "95%", "success"),
        ("처리 청크 수", "108K", "primary"),
        ("엔티티 수", "92K", "accent"),
        ("관계 수", "775K", "box_fill3"),
        ("ETL 비용", "$52", "success"),
    ])

    # 5. 시스템 아키텍처
    gen.create_architecture_overview()

    # 6. ETL 파이프라인
    gen.create_etl_pipeline_slide()

    # 7. AI 에이전트 팀
    gen.create_agent_team_slide()

    # 8. 스프린트 타임라인
    gen.create_sprint_timeline_slide()

    # 9. 산출물
    gen.create_deliverables_slide()

    # 10. 비용 분석
    gen.create_cost_slide()

    # 11. 교훈
    gen.create_lessons_slide()

    # 12. 결론
    gen.create_conclusion_slide()

    # 13. Thank You
    gen.create_thankyou_slide()

    gen.save(output_path)
    print(f"\n프로젝트 완료 보고서 생성 완료: {output_path}")


if __name__ == "__main__":
    main()
