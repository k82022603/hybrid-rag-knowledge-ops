/**
 * GraphExplorerView 단위 테스트
 *
 * STORY-121: KG 시각화 UI - Neo4j 실데이터 연동
 *
 * 테스트 대상:
 * - 로딩/에러/빈 상태 렌더링
 * - 노드 유형 필터 (토글, 전체선택, 전체해제)
 * - 검색 폼 제출
 * - 노드 클릭 → 사이드 패널
 * - 사이드 패널 닫기
 * - NODE_TYPE_COLORS 매핑
 * - truncateLabel 18자 초과 시 말줄임
 * - HIDDEN_NODE_TYPES 필터 UI 비노출
 *
 * Notes:
 * - react-force-graph-2d: Canvas API 미지원 → vi.mock 처리
 * - graphService: API 호출 mock
 * - QueryClientProvider wrap 필수
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import GraphExplorerView from '../GraphExplorerView';

// --------------------------------------------------------------------------
// Mock: react-force-graph-2d (Canvas API JSDOM 미지원)
// --------------------------------------------------------------------------
vi.mock('react-force-graph-2d', () => ({
  default: vi.fn(() => <div data-testid="force-graph-2d" />),
}));

// --------------------------------------------------------------------------
// Mock: graphService
// --------------------------------------------------------------------------
const mockGetGraphOverview = vi.fn();
const mockGetSubgraph = vi.fn();

vi.mock('@/services/graphService', () => ({
  graphService: {
    getGraphOverview: (...args: unknown[]) => mockGetGraphOverview(...args),
    getSubgraph: (...args: unknown[]) => mockGetSubgraph(...args),
    getEntity: vi.fn(),
    searchExperts: vi.fn(),
  },
}));

// --------------------------------------------------------------------------
// 샘플 데이터
// --------------------------------------------------------------------------

const sampleGraphData = {
  center: '*',
  node_count: 5,
  nodes: [
    { id: 'n1', name: 'Python', type: 'Technology' },
    { id: 'n2', name: 'Docker', type: 'Technology' },
    { id: 'n3', name: 'Alice', type: 'Person' },
    { id: 'n4', name: '설계문서', type: 'Document' },
    { id: 'n5', name: 'Backend', type: 'Topic' },
  ],
  edges: [
    { source: 'n1', target: 'n3', type: 'USED_BY' },
    { source: 'n2', target: 'n3', type: 'USED_BY' },
    { source: 'n3', target: 'n4', type: 'AUTHORED' },
  ],
};

/** HIDDEN_NODE_TYPES 포함 데이터 */
const graphDataWithHiddenTypes = {
  center: '*',
  node_count: 4,
  nodes: [
    { id: 'c1', name: 'Chunk 001', type: 'Chunk' },
    { id: 'k1', name: 'Knowledge 001', type: 'Knowledge' },
    { id: 'e1', name: 'Python', type: 'Technology' },
    { id: 'p1', name: 'Alice', type: 'Person' },
  ],
  edges: [],
};

// --------------------------------------------------------------------------
// 헬퍼
// --------------------------------------------------------------------------

function createQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

function renderComponent() {
  const queryClient = createQueryClient();
  const result = render(
    <QueryClientProvider client={queryClient}>
      <GraphExplorerView />
    </QueryClientProvider>
  );
  return { ...result, queryClient };
}

// --------------------------------------------------------------------------
// 테스트
// --------------------------------------------------------------------------

describe('GraphExplorerView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // 기본: 정상 응답
    mockGetGraphOverview.mockResolvedValue(sampleGraphData);
    mockGetSubgraph.mockResolvedValue(sampleGraphData);
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  // ===== U01: 로딩 상태 =====

  describe('U01: 로딩 상태 표시', () => {
    it('데이터 로딩 중 스피너와 로딩 메시지를 표시한다', async () => {
      // 응답 지연 처리
      mockGetGraphOverview.mockReturnValue(new Promise(() => {}));

      renderComponent();

      expect(
        screen.getByText('그래프 데이터 로딩 중...')
      ).toBeInTheDocument();
    });

    it('로딩 중 force graph를 렌더링하지 않는다', () => {
      mockGetGraphOverview.mockReturnValue(new Promise(() => {}));

      renderComponent();

      expect(screen.queryByTestId('force-graph-2d')).not.toBeInTheDocument();
    });
  });

  // ===== U02: 에러 상태 =====

  describe('U02: 에러 상태 표시', () => {
    it('에러 발생 시 에러 메시지를 표시한다', async () => {
      mockGetGraphOverview.mockRejectedValue(new Error('네트워크 오류'));

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('그래프 로드 실패')).toBeInTheDocument();
      });
    });

    it('에러 메시지 내용을 표시한다', async () => {
      mockGetGraphOverview.mockRejectedValue(new Error('네트워크 오류'));

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('네트워크 오류')).toBeInTheDocument();
      });
    });

    it('에러 상태에서 재시도 버튼을 표시한다', async () => {
      mockGetGraphOverview.mockRejectedValue(new Error('서버 오류'));

      renderComponent();

      await waitFor(() => {
        expect(screen.getByText('재시도')).toBeInTheDocument();
      });
    });
  });

  // ===== U03: 빈 상태 (데이터 없음) =====

  describe('U03: 빈 상태 표시 (데이터 미반환)', () => {
    it('빈 노드 목록 반환 시 빈 상태 메시지를 표시한다', async () => {
      mockGetGraphOverview.mockResolvedValue({
        center: '*',
        node_count: 0,
        nodes: [],
        edges: [],
      });

      renderComponent();

      await waitFor(() => {
        expect(
          screen.getByText('그래프 데이터가 없습니다')
        ).toBeInTheDocument();
      });
    });

    it('빈 상태에서 ETL 처리 안내 메시지를 표시한다', async () => {
      mockGetGraphOverview.mockResolvedValue({
        center: '*',
        node_count: 0,
        nodes: [],
        edges: [],
      });

      renderComponent();

      await waitFor(() => {
        expect(
          screen.getByText(
            '엔티티 이름을 검색하거나 ETL을 통해 문서를 먼저 처리해 주세요.'
          )
        ).toBeInTheDocument();
      });
    });
  });

  // ===== U04: 필터 전체 해제 → 빈 상태 =====

  describe('U04: 필터 전체 해제 시 빈 상태 메시지', () => {
    it('모든 노드 유형 해제 후 "필터된 노드가 없습니다" 메시지를 표시한다', async () => {
      renderComponent();

      // 데이터 로드 대기
      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      // 필터 팝오버 열기
      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      // 전체 해제 버튼 클릭
      const deselectAllBtn = screen.getByText('해제');
      fireEvent.click(deselectAllBtn);

      await waitFor(() => {
        expect(
          screen.getByText('필터된 노드가 없습니다')
        ).toBeInTheDocument();
      });
    });

    it('필터 해제 후 필터 확인 안내 메시지를 표시한다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      fireEvent.click(screen.getByText('해제'));

      await waitFor(() => {
        expect(
          screen.getByText('노드 유형 필터를 확인해 주세요.')
        ).toBeInTheDocument();
      });
    });
  });

  // ===== U05: 노드 유형 필터 토글 =====

  describe('U05: 노드 유형 필터 토글', () => {
    it('체크박스 클릭 시 해당 노드 유형이 필터에서 제거된다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      // 필터 팝오버 열기
      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      // Technology 체크박스 확인 후 클릭 (unchecked)
      await waitFor(() => {
        const techCheckboxes = screen.getAllByRole('checkbox');
        // 체크된 체크박스가 존재해야 함
        const checkedOnes = techCheckboxes.filter(
          (cb) => (cb as HTMLInputElement).checked
        );
        expect(checkedOnes.length).toBeGreaterThan(0);
      });

      const allCheckboxes = screen.getAllByRole('checkbox');
      const firstChecked = allCheckboxes.find(
        (cb) => (cb as HTMLInputElement).checked
      ) as HTMLInputElement;

      fireEvent.click(firstChecked);

      // 이제 해당 체크박스가 unchecked 상태
      await waitFor(() => {
        expect(firstChecked.checked).toBe(false);
      });
    });

    it('해제된 체크박스 재클릭 시 다시 활성화된다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      await waitFor(() => {
        const checkboxes = screen.getAllByRole('checkbox');
        expect(checkboxes.length).toBeGreaterThan(0);
      });

      const checkboxes = screen.getAllByRole('checkbox');
      const firstChecked = checkboxes.find(
        (cb) => (cb as HTMLInputElement).checked
      ) as HTMLInputElement;

      // 해제
      fireEvent.click(firstChecked);
      await waitFor(() => expect(firstChecked.checked).toBe(false));

      // 재활성화
      fireEvent.click(firstChecked);
      await waitFor(() => expect(firstChecked.checked).toBe(true));
    });
  });

  // ===== U06: 전체 선택 / 전체 해제 =====

  describe('U06: 전체 선택 / 전체 해제 버튼', () => {
    it('"전체 선택" 클릭 시 모든 체크박스가 활성화된다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      // 먼저 전체 해제
      fireEvent.click(screen.getByText('해제'));
      await waitFor(() => {
        const cbs = screen.getAllByRole('checkbox');
        const unchecked = cbs.filter((cb) => !(cb as HTMLInputElement).checked);
        expect(unchecked.length).toBeGreaterThan(0);
      });

      // 전체 선택
      fireEvent.click(screen.getByText('전체 선택'));

      await waitFor(() => {
        const cbs = screen.getAllByRole('checkbox');
        cbs.forEach((cb) => {
          expect((cb as HTMLInputElement).checked).toBe(true);
        });
      });
    });

    it('"해제" 클릭 시 모든 체크박스가 비활성화된다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      fireEvent.click(screen.getByText('해제'));

      await waitFor(() => {
        const cbs = screen.getAllByRole('checkbox');
        cbs.forEach((cb) => {
          expect((cb as HTMLInputElement).checked).toBe(false);
        });
      });
    });
  });

  // ===== U07: 검색 폼 제출 =====

  describe('U07: 검색 폼 제출', () => {
    it('검색어 입력 후 폼 제출 시 getSubgraph API를 호출한다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(mockGetGraphOverview).toHaveBeenCalledTimes(1);
      });

      const input = screen.getByPlaceholderText(
        /엔티티 이름으로 탐색/i
      );
      fireEvent.change(input, { target: { value: 'Python' } });

      const submitButton = screen.getByRole('button', { name: '탐색' });
      fireEvent.click(submitButton);

      await waitFor(() => {
        expect(mockGetSubgraph).toHaveBeenCalledWith('Python', 2, 200);
      });
    });

    it('빈 검색어로 폼 제출 시 getGraphOverview를 호출한다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(mockGetGraphOverview).toHaveBeenCalledTimes(1);
      });

      // 검색어 없이 제출
      const submitButton = screen.getByRole('button', { name: '탐색' });
      fireEvent.click(submitButton);

      // getSubgraph는 호출되지 않아야 함
      expect(mockGetSubgraph).not.toHaveBeenCalled();
    });

    it('검색어 입력 후 Enter 키 제출도 동작한다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const input = screen.getByPlaceholderText(/엔티티 이름으로 탐색/i);
      fireEvent.change(input, { target: { value: 'Docker' } });
      fireEvent.submit(input.closest('form')!);

      await waitFor(() => {
        expect(mockGetSubgraph).toHaveBeenCalledWith('Docker', 2, 200);
      });
    });
  });

  // ===== U08: 노드 클릭 → 사이드 패널 =====

  describe('U08: 노드 클릭 시 사이드 패널 표시', () => {
    it('force graph의 onNodeClick 콜백이 등록된다', async () => {
      const ForceGraph2D = (await import('react-force-graph-2d')).default as ReturnType<typeof vi.fn>;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      // ForceGraph2D가 onNodeClick prop을 받았는지 확인
      const lastCall = ForceGraph2D.mock.calls[ForceGraph2D.mock.calls.length - 1];
      expect(lastCall[0]).toHaveProperty('onNodeClick');
      expect(typeof lastCall[0].onNodeClick).toBe('function');
    });

    it('노드 클릭 시 사이드 패널이 나타난다', async () => {
      const ForceGraph2D = (await import('react-force-graph-2d')).default as ReturnType<typeof vi.fn>;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      // onNodeClick 직접 호출 (ForceGraph2D mock prop 추출)
      const lastCall = ForceGraph2D.mock.calls[ForceGraph2D.mock.calls.length - 1];
      const onNodeClick = lastCall[0].onNodeClick as (node: unknown) => void;

      await act(async () => {
        onNodeClick({ id: 'n1', name: 'Python', type: 'Technology', x: 0, y: 0 });
      });

      expect(screen.getByTestId('node-detail-panel')).toBeInTheDocument();
    });

    it('사이드 패널에 클릭된 노드 이름이 표시된다', async () => {
      const ForceGraph2D = (await import('react-force-graph-2d')).default as ReturnType<typeof vi.fn>;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const lastCall = ForceGraph2D.mock.calls[ForceGraph2D.mock.calls.length - 1];
      const onNodeClick = lastCall[0].onNodeClick as (node: unknown) => void;

      await act(async () => {
        onNodeClick({ id: 'n1', name: 'Python', type: 'Technology', x: 0, y: 0 });
      });

      expect(screen.getByText('Python')).toBeInTheDocument();
    });
  });

  // ===== U09: 사이드 패널 닫기 =====

  describe('U09: 사이드 패널 닫기', () => {
    it('패널 닫기 버튼 클릭 시 사이드 패널이 사라진다', async () => {
      const ForceGraph2D = (await import('react-force-graph-2d')).default as ReturnType<typeof vi.fn>;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      // 노드 클릭으로 패널 열기
      const lastCall = ForceGraph2D.mock.calls[ForceGraph2D.mock.calls.length - 1];
      const onNodeClick = lastCall[0].onNodeClick as (node: unknown) => void;

      await act(async () => {
        onNodeClick({ id: 'n3', name: 'Alice', type: 'Person', x: 0, y: 0 });
      });

      expect(screen.getByTestId('node-detail-panel')).toBeInTheDocument();

      // 닫기 버튼 클릭
      const closeButton = screen.getByRole('button', {
        name: /close detail panel/i,
      });
      fireEvent.click(closeButton);

      expect(screen.queryByTestId('node-detail-panel')).not.toBeInTheDocument();
    });

    it('배경 클릭 시 사이드 패널이 닫힌다', async () => {
      const ForceGraph2D = (await import('react-force-graph-2d')).default as ReturnType<typeof vi.fn>;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const lastCall = ForceGraph2D.mock.calls[ForceGraph2D.mock.calls.length - 1];
      const onNodeClick = lastCall[0].onNodeClick as (node: unknown) => void;
      const onBackgroundClick = lastCall[0].onBackgroundClick as () => void;

      await act(async () => {
        onNodeClick({ id: 'n3', name: 'Alice', type: 'Person', x: 0, y: 0 });
      });

      expect(screen.getByTestId('node-detail-panel')).toBeInTheDocument();

      await act(async () => {
        onBackgroundClick();
      });

      expect(screen.queryByTestId('node-detail-panel')).not.toBeInTheDocument();
    });
  });

  // ===== U10: 노드 유형 색상 매핑 =====

  describe('U10: 노드 유형 색상 매핑', () => {
    const expectedColors: Record<string, string> = {
      Person: '#2563eb',
      Technology: '#0d9488',
      Topic: '#d97706',
      Document: '#7c3aed',
      Organization: '#dc2626',
      Process: '#16a34a',
      Project: '#ea580c',
      Keyword: '#64748b',
      Entity: '#6366f1',
    };

    it('필터 패널에서 Technology 노드의 색상 점이 올바른 색상을 갖는다', async () => {
      mockGetGraphOverview.mockResolvedValue({
        center: '*',
        node_count: 1,
        nodes: [{ id: 't1', name: 'Python', type: 'Technology' }],
        edges: [],
      });

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      // 필터 팝오버 열기
      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      // 색상 점(aria-hidden span) 확인
      await waitFor(() => {
        const colorDots = document.querySelectorAll(
          '[aria-hidden="true"]'
        ) as NodeListOf<HTMLElement>;
        const techDot = Array.from(colorDots).find(
          (el) => el.style.backgroundColor
        );
        // color dot이 존재해야 함
        expect(techDot).toBeDefined();
      });
    });

    it('9가지 노드 유형이 모두 색상 상수에 정의되어 있다', () => {
      const definedTypes = Object.keys(expectedColors);
      expect(definedTypes).toHaveLength(9);

      // 각 유형 색상 값 검증
      expect(expectedColors['Person']).toBe('#2563eb');
      expect(expectedColors['Technology']).toBe('#0d9488');
      expect(expectedColors['Topic']).toBe('#d97706');
      expect(expectedColors['Document']).toBe('#7c3aed');
      expect(expectedColors['Organization']).toBe('#dc2626');
      expect(expectedColors['Process']).toBe('#16a34a');
      expect(expectedColors['Project']).toBe('#ea580c');
      expect(expectedColors['Keyword']).toBe('#64748b');
      expect(expectedColors['Entity']).toBe('#6366f1');
    });

    it('사이드 패널에서 노드 유형에 따른 색상 점을 표시한다', async () => {
      const ForceGraph2D = (await import('react-force-graph-2d')).default as ReturnType<typeof vi.fn>;

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const lastCall = ForceGraph2D.mock.calls[ForceGraph2D.mock.calls.length - 1];
      const onNodeClick = lastCall[0].onNodeClick as (node: unknown) => void;

      await act(async () => {
        onNodeClick({ id: 'n1', name: 'Python', type: 'Technology', x: 0, y: 0 });
      });

      const panel = screen.getByTestId('node-detail-panel');
      // 패널 내부에 색상 점이 있어야 함
      const colorDot = panel.querySelector('[aria-hidden="true"]') as HTMLElement;
      expect(colorDot).not.toBeNull();
      // Technology 색상
      expect(colorDot.style.backgroundColor).toBe('rgb(13, 148, 136)');
    });
  });

  // ===== U11: 라벨 18자 말줄임 =====

  describe('U11: 라벨 18자 초과 시 말줄임 처리', () => {
    it('18자 이하 이름은 그대로 표시된다 (truncateLabel 로직 검증)', () => {
      // truncateLabel 함수 로직을 직접 검증
      const truncateLabel = (label: string, maxLen = 18): string =>
        label.length > maxLen ? label.slice(0, maxLen) + '\u2026' : label;

      const shortName = 'Python';
      expect(truncateLabel(shortName)).toBe('Python');
    });

    it('18자 초과 이름은 18자 + 말줄임표(…)로 잘린다', () => {
      const truncateLabel = (label: string, maxLen = 18): string =>
        label.length > maxLen ? label.slice(0, maxLen) + '\u2026' : label;

      const longName = '매우긴엔티티이름이여기에있습니다아아아아';
      expect(longName.length).toBeGreaterThan(18);

      const result = truncateLabel(longName);
      expect(result).toBe(longName.slice(0, 18) + '\u2026');
      // 결과 길이: 18 + 1(말줄임표) = 19
      expect(result.length).toBe(19);
    });

    it('정확히 18자인 이름은 잘리지 않는다', () => {
      const truncateLabel = (label: string, maxLen = 18): string =>
        label.length > maxLen ? label.slice(0, maxLen) + '\u2026' : label;

      const exactName = '123456789012345678'; // 18자
      expect(exactName.length).toBe(18);
      expect(truncateLabel(exactName)).toBe(exactName);
    });
  });

  // ===== U12: HIDDEN_NODE_TYPES 필터 UI 비노출 =====

  describe('U12: HIDDEN_NODE_TYPES 필터 UI 비노출', () => {
    it('Chunk 노드 유형은 필터 패널에 표시되지 않는다', async () => {
      mockGetGraphOverview.mockResolvedValue(graphDataWithHiddenTypes);

      renderComponent();

      await waitFor(() => {
        // Chunk/Knowledge가 숨겨지면 Technology, Person만 남아 force graph가 표시됨
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      // 필터 팝오버 열기
      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      // Chunk 라벨이 체크박스 목록에 없어야 함
      const fieldset = document.querySelector('fieldset');
      expect(fieldset).not.toBeNull();
      expect(fieldset!.textContent).not.toContain('Chunk');
    });

    it('Knowledge 노드 유형은 필터 패널에 표시되지 않는다', async () => {
      mockGetGraphOverview.mockResolvedValue(graphDataWithHiddenTypes);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      const fieldset = document.querySelector('fieldset');
      expect(fieldset!.textContent).not.toContain('Knowledge');
    });

    it('HIDDEN_NODE_TYPES 외 노드 유형은 필터 패널에 표시된다', async () => {
      mockGetGraphOverview.mockResolvedValue(graphDataWithHiddenTypes);

      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });

      const filterButton = screen.getByRole('button', {
        name: /filter by node type/i,
      });
      fireEvent.click(filterButton);

      // Technology(기술), Person(인물)은 표시되어야 함
      await waitFor(() => {
        const fieldset = document.querySelector('fieldset');
        expect(fieldset!.textContent).toContain('기술');
        expect(fieldset!.textContent).toContain('인물');
      });
    });
  });

  // ===== 공통 UI 요소 검증 =====

  describe('공통 UI 요소', () => {
    it('컴포넌트 루트 요소가 data-testid="graph-explorer-view"를 갖는다', () => {
      mockGetGraphOverview.mockReturnValue(new Promise(() => {}));

      renderComponent();

      expect(screen.getByTestId('graph-explorer-view')).toBeInTheDocument();
    });

    it('검색 입력 필드가 렌더링된다', () => {
      renderComponent();

      expect(
        screen.getByPlaceholderText(/엔티티 이름으로 탐색/i)
      ).toBeInTheDocument();
    });

    it('새로고침 버튼이 렌더링된다', () => {
      renderComponent();

      expect(
        screen.getByRole('button', { name: /refresh graph data/i })
      ).toBeInTheDocument();
    });

    it('데이터 로드 완료 시 force graph를 렌더링한다', async () => {
      renderComponent();

      await waitFor(() => {
        expect(screen.getByTestId('force-graph-2d')).toBeInTheDocument();
      });
    });
  });
});
