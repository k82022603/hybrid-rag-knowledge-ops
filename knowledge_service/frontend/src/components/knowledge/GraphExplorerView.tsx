/**
 * GraphExplorerView - Full Knowledge Graph exploration view
 *
 * Interactive force-directed graph for browsing Neo4j knowledge graph data.
 * Supports node type filtering, node click for related documents, and
 * performance-limited rendering (max 500 nodes).
 *
 * Uses react-force-graph-2d for rendering, Headless UI for filters.
 *
 * STORY-121: KG 시각화 UI - Neo4j 실데이터 연동
 */
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import ForceGraph2D from 'react-force-graph-2d';
import type { ForceGraphMethods } from 'react-force-graph-2d';
import { Popover, PopoverButton, PopoverPanel } from '@headlessui/react';
import {
  ArrowPathIcon,
  FunnelIcon,
  MagnifyingGlassIcon,
  PlusIcon,
  MinusIcon,
  ArrowsPointingOutIcon,
  XMarkIcon,
  DocumentTextIcon,
  ExclamationTriangleIcon,
  AdjustmentsHorizontalIcon,
} from '@heroicons/react/24/outline';
import { graphService, type SubgraphData } from '@/services/graphService';

/** Node type color mapping */
const NODE_TYPE_COLORS: Record<string, string> = {
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
const DEFAULT_COLOR = '#94a3b8';

/** Node type display labels */
const NODE_TYPE_LABELS: Record<string, string> = {
  Person: '인물',
  Technology: '기술',
  Topic: '토픽',
  Document: '문서',
  Organization: '조직',
  Process: '프로세스',
  Project: '프로젝트',
  Keyword: '키워드',
  Entity: '엔티티',
};

/** Max node limits */
const DEFAULT_NODE_LIMIT = 200;
const MAX_NODE_LIMIT = 500;

/** Node types to hide from the graph for cleaner visualization */
const HIDDEN_NODE_TYPES = new Set(['Chunk', 'Knowledge']);

const ZOOM_STEP = 1.5;

/** Truncate label */
const truncateLabel = (label: string, maxLen = 18): string =>
  label.length > maxLen ? label.slice(0, maxLen) + '\u2026' : label;

/** Internal force node type */
interface ForceNode {
  id: string;
  name: string;
  type: string;
  x?: number;
  y?: number;
}

/** Selected node detail info */
interface NodeDetail {
  node: ForceNode;
  edgeCount: number;
  connectedNodes: Array<{ name: string; type: string; relation: string }>;
}

const GraphExplorerView: React.FC = () => {
  const [searchQuery, setSearchQuery] = useState('');
  const [submittedQuery, setSubmittedQuery] = useState('');
  const [nodeLimit, setNodeLimit] = useState(DEFAULT_NODE_LIMIT);
  const [enabledTypes, setEnabledTypes] = useState<Set<string>>(new Set());
  const [selectedNode, setSelectedNode] = useState<NodeDetail | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<ForceGraphMethods | undefined>(undefined);
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 });

  // Fetch graph data
  const {
    data: graphData,
    isLoading,
    isError,
    error,
    refetch,
  } = useQuery<SubgraphData>({
    queryKey: ['graph-explorer', submittedQuery, nodeLimit],
    queryFn: () => {
      if (submittedQuery.trim()) {
        return graphService.getSubgraph(submittedQuery.trim(), 2, nodeLimit);
      }
      return graphService.getGraphOverview(nodeLimit);
    },
  });

  // Initialize enabled types when data loads
  useEffect(() => {
    if (!graphData) return;
    const types = new Set(
      graphData.nodes
        .map((n) => n.type)
        .filter((t) => !HIDDEN_NODE_TYPES.has(t))
    );
    setEnabledTypes(types);
  }, [graphData]);

  // Observe container size
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      if (width > 0 && height > 0) {
        setDimensions({ width: Math.floor(width), height: Math.floor(height) });
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Transform data for force graph, applying type filter
  const forceGraphData = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };

    const visibleNodes = graphData.nodes.filter(
      (n) => !HIDDEN_NODE_TYPES.has(n.type) && enabledTypes.has(n.type)
    );
    const visibleIds = new Set(visibleNodes.map((n) => n.id));

    return {
      nodes: visibleNodes.map((n) => ({
        id: n.id,
        name: n.name || n.label || n.id,
        type: n.type,
      })),
      links: graphData.edges
        .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
        .map((e) => ({
          source: e.source,
          target: e.target,
          label: e.type,
        })),
    };
  }, [graphData, enabledTypes]);

  // Available node types from data
  const availableTypes = useMemo(() => {
    if (!graphData) return [];
    const typeCounts = new Map<string, number>();
    graphData.nodes.forEach((n) => {
      if (HIDDEN_NODE_TYPES.has(n.type)) return;
      typeCounts.set(n.type, (typeCounts.get(n.type) || 0) + 1);
    });
    return Array.from(typeCounts.entries())
      .sort((a, b) => b[1] - a[1])
      .map(([type, count]) => ({ type, count }));
  }, [graphData]);

  // Configure force physics
  useEffect(() => {
    const fg = graphRef.current;
    if (!fg || !graphData) return;
    fg.d3Force('charge')?.strength(-200);
    fg.d3Force('link')?.distance(60);
  }, [graphData]);

  // Handle search submit
  const handleSearch = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      setSubmittedQuery(searchQuery);
      setSelectedNode(null);
    },
    [searchQuery]
  );

  // Toggle node type filter
  const toggleType = useCallback((type: string) => {
    setEnabledTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) {
        next.delete(type);
      } else {
        next.add(type);
      }
      return next;
    });
  }, []);

  // Select/deselect all types
  const selectAllTypes = useCallback(() => {
    setEnabledTypes(new Set(availableTypes.map((t) => t.type)));
  }, [availableTypes]);

  const deselectAllTypes = useCallback(() => {
    setEnabledTypes(new Set());
  }, []);

  // Node click handler - compute connected nodes
  const handleNodeClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any) => {
      if (!graphData) return;

      const connectedEdges = graphData.edges.filter(
        (e) => e.source === node.id || e.target === node.id
      );

      const connectedNodes = connectedEdges.map((e) => {
        const otherId = e.source === node.id ? e.target : e.source;
        const otherNode = graphData.nodes.find((n) => n.id === otherId);
        return {
          name: otherNode?.name || otherNode?.label || otherId,
          type: otherNode?.type || 'Unknown',
          relation: e.type,
        };
      });

      setSelectedNode({
        node: {
          id: node.id,
          name: node.name || node.id,
          type: node.type,
        },
        edgeCount: connectedEdges.length,
        connectedNodes,
      });
    },
    [graphData]
  );

  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null);
  }, []);

  // Zoom controls
  const handleZoomIn = useCallback(() => {
    graphRef.current?.zoom(ZOOM_STEP, 300);
  }, []);

  const handleZoomOut = useCallback(() => {
    graphRef.current?.zoom(1 / ZOOM_STEP, 300);
  }, []);

  const handleZoomReset = useCallback(() => {
    graphRef.current?.zoomToFit(400, 40);
  }, []);

  // Node paint callback
  const paintNode = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = truncateLabel(node.name || node.id);
      const fontSize = 10 / globalScale;
      const nodeRadius = 6;
      const color = NODE_TYPE_COLORS[node.type] || DEFAULT_COLOR;
      const isSelected = selectedNode?.node.id === node.id;

      // Selection ring
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(node.x, node.y, nodeRadius + 4, 0, 2 * Math.PI);
        ctx.fillStyle = `${color}33`;
        ctx.fill();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      // Circle
      ctx.beginPath();
      ctx.arc(node.x, node.y, nodeRadius, 0, 2 * Math.PI);
      ctx.fillStyle = color;
      ctx.fill();

      // Label
      ctx.font = `${fontSize}px Pretendard, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#334155';
      ctx.fillText(label, node.x, node.y + nodeRadius + 2);
    },
    [selectedNode]
  );

  // Group connected nodes by type for the detail panel
  type ConnectedNode = { name: string; type: string; relation: string };

  const groupedConnections = useMemo(() => {
    if (!selectedNode) return new Map<string, ConnectedNode[]>();
    const groups = new Map<string, ConnectedNode[]>();
    selectedNode.connectedNodes.forEach((cn) => {
      const existing = groups.get(cn.type) || [];
      existing.push(cn);
      groups.set(cn.type, existing);
    });
    return groups;
  }, [selectedNode]);

  return (
    <div className="flex flex-col h-full" data-testid="graph-explorer-view">
      {/* Toolbar */}
      <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        {/* Search */}
        <form onSubmit={handleSearch} className="flex-1 flex gap-2">
          <div className="relative flex-1 group">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-gray-400 group-focus-within:text-primary-500 transition-colors" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="엔티티 이름으로 탐색 (예: Python, Docker)..."
              className="input pl-9 text-sm"
              aria-label="Search graph entities"
            />
          </div>
          <button type="submit" className="btn-primary btn-sm whitespace-nowrap">
            탐색
          </button>
        </form>

        {/* Filters */}
        <div className="flex items-center gap-2">
          {/* Node type filter popover */}
          <Popover className="relative">
            <PopoverButton
              className="btn btn-secondary btn-sm"
              aria-label="Filter by node type"
            >
              <FunnelIcon className="h-4 w-4" />
              <span className="hidden sm:inline">필터</span>
              {enabledTypes.size < availableTypes.length && (
                <span className="ml-1 inline-flex items-center justify-center w-5 h-5 text-[10px] font-bold bg-primary-600 text-white rounded-full">
                  {enabledTypes.size}
                </span>
              )}
            </PopoverButton>

            <PopoverPanel className="absolute right-0 z-20 mt-2 w-64 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <h4 className="text-sm font-semibold text-gray-900 dark:text-white">
                  노드 유형 필터
                </h4>
                <div className="flex gap-2">
                  <button
                    onClick={selectAllTypes}
                    className="text-xs text-primary-600 hover:text-primary-700 dark:text-primary-400"
                  >
                    전체 선택
                  </button>
                  <button
                    onClick={deselectAllTypes}
                    className="text-xs text-gray-500 hover:text-gray-700 dark:text-gray-400"
                  >
                    해제
                  </button>
                </div>
              </div>
              <fieldset>
                <legend className="sr-only">Node type filters</legend>
                <div className="space-y-2">
                  {availableTypes.map(({ type, count }) => (
                    <label
                      key={type}
                      className="flex items-center gap-2.5 cursor-pointer group"
                    >
                      <input
                        type="checkbox"
                        checked={enabledTypes.has(type)}
                        onChange={() => toggleType(type)}
                        className="h-4 w-4 rounded border-gray-300 text-primary-600 focus:ring-primary-500 dark:border-gray-600 dark:bg-gray-700"
                      />
                      <span
                        className="w-3 h-3 rounded-full flex-shrink-0"
                        style={{
                          backgroundColor: NODE_TYPE_COLORS[type] || DEFAULT_COLOR,
                        }}
                        aria-hidden="true"
                      />
                      <span className="text-sm text-gray-700 dark:text-gray-300 group-hover:text-gray-900 dark:group-hover:text-white">
                        {NODE_TYPE_LABELS[type] || type}
                      </span>
                      <span className="ml-auto text-xs text-gray-400 tabular-nums">
                        {count}
                      </span>
                    </label>
                  ))}
                </div>
              </fieldset>
            </PopoverPanel>
          </Popover>

          {/* Node limit selector */}
          <Popover className="relative">
            <PopoverButton
              className="btn btn-secondary btn-sm"
              aria-label="Adjust node limit"
            >
              <AdjustmentsHorizontalIcon className="h-4 w-4" />
              <span className="hidden sm:inline">{nodeLimit}</span>
            </PopoverButton>

            <PopoverPanel className="absolute right-0 z-20 mt-2 w-48 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-700 rounded-xl shadow-lg p-4">
              <label
                htmlFor="node-limit-slider"
                className="text-sm font-semibold text-gray-900 dark:text-white"
              >
                최대 노드 수: {nodeLimit}
              </label>
              <input
                id="node-limit-slider"
                type="range"
                min={50}
                max={MAX_NODE_LIMIT}
                step={50}
                value={nodeLimit}
                onChange={(e) => setNodeLimit(Number(e.target.value))}
                className="w-full mt-2 accent-primary-600"
              />
              <div className="flex justify-between text-xs text-gray-400 mt-1">
                <span>50</span>
                <span>{MAX_NODE_LIMIT}</span>
              </div>
            </PopoverPanel>
          </Popover>

          {/* Refresh */}
          <button
            onClick={() => refetch()}
            className="btn btn-secondary btn-sm"
            aria-label="Refresh graph data"
            title="새로고침"
          >
            <ArrowPathIcon className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Main content area */}
      <div className="flex-1 flex min-h-0">
        {/* Graph canvas */}
        <div
          ref={containerRef}
          className="flex-1 relative bg-gray-50/50 dark:bg-gray-900/30"
        >
          {/* Loading */}
          {isLoading && (
            <div className="absolute inset-0 flex items-center justify-center bg-white/60 dark:bg-gray-800/60 z-10">
              <div className="text-center">
                <ArrowPathIcon className="h-8 w-8 text-primary-500 animate-spin mx-auto mb-2" />
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  그래프 데이터 로딩 중...
                </p>
              </div>
            </div>
          )}

          {/* Error */}
          {isError && !isLoading && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center max-w-xs p-6">
                <ExclamationTriangleIcon className="h-10 w-10 text-error-500 mx-auto mb-3" />
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
                  그래프 로드 실패
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mb-4">
                  {error instanceof Error ? error.message : '알 수 없는 오류가 발생했습니다.'}
                </p>
                <button onClick={() => refetch()} className="btn-primary btn-sm">
                  <ArrowPathIcon className="h-4 w-4" />
                  재시도
                </button>
              </div>
            </div>
          )}

          {/* Empty state */}
          {!isLoading && !isError && forceGraphData.nodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center">
              <div className="text-center max-w-xs p-6">
                <div className="w-14 h-14 rounded-full bg-gray-100 dark:bg-gray-800 flex items-center justify-center mx-auto mb-3">
                  <MagnifyingGlassIcon className="h-7 w-7 text-gray-400" />
                </div>
                <h3 className="text-sm font-semibold text-gray-900 dark:text-white mb-1">
                  {graphData && graphData.nodes.length > 0
                    ? '필터된 노드가 없습니다'
                    : '그래프 데이터가 없습니다'}
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400">
                  {graphData && graphData.nodes.length > 0
                    ? '노드 유형 필터를 확인해 주세요.'
                    : '엔티티 이름을 검색하거나 ETL을 통해 문서를 먼저 처리해 주세요.'}
                </p>
              </div>
            </div>
          )}

          {/* Force graph */}
          {!isLoading && !isError && forceGraphData.nodes.length > 0 && (
            <>
              <ForceGraph2D
                ref={graphRef}
                graphData={forceGraphData}
                width={dimensions.width}
                height={dimensions.height}
                nodeCanvasObject={paintNode}
                nodePointerAreaPaint={(
                  // eslint-disable-next-line @typescript-eslint/no-explicit-any
                  node: any,
                  color: string,
                  ctx: CanvasRenderingContext2D
                ) => {
                  ctx.beginPath();
                  ctx.arc(node.x, node.y, 10, 0, 2 * Math.PI);
                  ctx.fillStyle = color;
                  ctx.fill();
                }}
                onNodeClick={handleNodeClick}
                onBackgroundClick={handleBackgroundClick}
                linkLabel="label"
                linkColor={() => '#cbd5e1'}
                linkDirectionalArrowLength={4}
                linkDirectionalArrowRelPos={1}
                linkWidth={0.8}
                cooldownTicks={100}
                onEngineStop={() => graphRef.current?.zoomToFit(300, 40)}
              />

              {/* Zoom controls */}
              <div
                className="absolute bottom-4 right-4 flex flex-col gap-1 z-10"
                role="toolbar"
                aria-label="Graph zoom controls"
              >
                <button
                  onClick={handleZoomIn}
                  className="p-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Zoom in"
                  title="확대"
                >
                  <PlusIcon className="h-4 w-4 text-gray-600 dark:text-gray-300" />
                </button>
                <button
                  onClick={handleZoomOut}
                  className="p-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Zoom out"
                  title="축소"
                >
                  <MinusIcon className="h-4 w-4 text-gray-600 dark:text-gray-300" />
                </button>
                <button
                  onClick={handleZoomReset}
                  className="p-2 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                  aria-label="Fit all nodes"
                  title="전체 보기"
                >
                  <ArrowsPointingOutIcon className="h-4 w-4 text-gray-600 dark:text-gray-300" />
                </button>
              </div>

              {/* Stats badge */}
              <div className="absolute top-3 left-3 z-10 px-3 py-1.5 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm">
                <p className="text-xs text-gray-600 dark:text-gray-300 tabular-nums">
                  <span className="font-semibold">{forceGraphData.nodes.length}</span> nodes
                  {' / '}
                  <span className="font-semibold">{forceGraphData.links.length}</span> edges
                </p>
              </div>

              {/* Legend */}
              <div className="absolute bottom-4 left-4 z-10 bg-white/90 dark:bg-gray-800/90 backdrop-blur-sm border border-gray-200 dark:border-gray-700 rounded-lg shadow-sm p-2.5">
                <div className="grid grid-cols-2 gap-x-4 gap-y-1">
                  {availableTypes
                    .filter(({ type }) => enabledTypes.has(type))
                    .slice(0, 8)
                    .map(({ type }) => (
                      <span key={type} className="flex items-center gap-1.5">
                        <span
                          className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                          style={{
                            backgroundColor: NODE_TYPE_COLORS[type] || DEFAULT_COLOR,
                          }}
                        />
                        <span className="text-[11px] text-gray-500 dark:text-gray-400">
                          {NODE_TYPE_LABELS[type] || type}
                        </span>
                      </span>
                    ))}
                </div>
              </div>
            </>
          )}
        </div>

        {/* Node detail side panel */}
        {selectedNode && (
          <aside
            className="w-72 xl:w-80 flex-shrink-0 border-l border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800 overflow-y-auto animate-slide-left"
            aria-label={`Details for ${selectedNode.node.name}`}
            data-testid="node-detail-panel"
          >
            {/* Panel header */}
            <div className="flex items-start justify-between gap-2 px-4 py-3 border-b border-gray-200 dark:border-gray-700">
              <div className="min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span
                    className="w-3 h-3 rounded-full flex-shrink-0"
                    style={{
                      backgroundColor:
                        NODE_TYPE_COLORS[selectedNode.node.type] || DEFAULT_COLOR,
                    }}
                    aria-hidden="true"
                  />
                  <span className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                    {NODE_TYPE_LABELS[selectedNode.node.type] || selectedNode.node.type}
                  </span>
                </div>
                <h3 className="text-sm font-bold text-gray-900 dark:text-white break-words">
                  {selectedNode.node.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
                aria-label="Close detail panel"
              >
                <XMarkIcon className="h-4 w-4" />
              </button>
            </div>

            {/* Stats */}
            <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-gray-50 dark:bg-gray-900/40 rounded-lg p-2.5 text-center">
                  <p className="text-lg font-bold text-gray-900 dark:text-white tabular-nums">
                    {selectedNode.edgeCount}
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">연결</p>
                </div>
                <div className="bg-gray-50 dark:bg-gray-900/40 rounded-lg p-2.5 text-center">
                  <p className="text-lg font-bold text-gray-900 dark:text-white tabular-nums">
                    {groupedConnections.size}
                  </p>
                  <p className="text-[11px] text-gray-500 dark:text-gray-400">유형</p>
                </div>
              </div>
            </div>

            {/* Explore deeper button */}
            <div className="px-4 py-3 border-b border-gray-100 dark:border-gray-700">
              <button
                onClick={() => {
                  setSearchQuery(selectedNode.node.name);
                  setSubmittedQuery(selectedNode.node.name);
                  setSelectedNode(null);
                }}
                className="btn-primary btn-sm w-full"
              >
                <MagnifyingGlassIcon className="h-4 w-4" />
                이 엔티티 중심으로 탐색
              </button>
            </div>

            {/* Connected nodes grouped by type */}
            <div className="px-4 py-3">
              <h4 className="text-xs font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider mb-3">
                연결된 노드
              </h4>
              {selectedNode.connectedNodes.length === 0 ? (
                <p className="text-xs text-gray-400">연결된 노드가 없습니다.</p>
              ) : (
                <div className="space-y-4">
                  {Array.from(groupedConnections.entries()).map(([type, nodes]) => (
                    <div key={type}>
                      <div className="flex items-center gap-1.5 mb-1.5">
                        <span
                          className="w-2 h-2 rounded-full flex-shrink-0"
                          style={{
                            backgroundColor: NODE_TYPE_COLORS[type] || DEFAULT_COLOR,
                          }}
                        />
                        <span className="text-xs font-medium text-gray-600 dark:text-gray-300">
                          {NODE_TYPE_LABELS[type] || type}{' '}
                          <span className="text-gray-400">({nodes.length})</span>
                        </span>
                      </div>
                      <ul className="space-y-1 ml-3.5">
                        {nodes.slice(0, 20).map((cn: ConnectedNode, idx: number) => (
                          <li
                            key={`${cn.name}-${idx}`}
                            className="flex items-start gap-2 text-xs group"
                          >
                            {type === 'Document' ? (
                              <DocumentTextIcon className="h-3.5 w-3.5 text-gray-400 flex-shrink-0 mt-0.5" />
                            ) : (
                              <span className="w-1 h-1 rounded-full bg-gray-300 dark:bg-gray-600 flex-shrink-0 mt-1.5" />
                            )}
                            <div className="min-w-0">
                              <p className="text-gray-700 dark:text-gray-300 break-words group-hover:text-primary-600 dark:group-hover:text-primary-400 transition-colors">
                                {cn.name}
                              </p>
                              <p className="text-[10px] text-gray-400">
                                {cn.relation}
                              </p>
                            </div>
                          </li>
                        ))}
                        {nodes.length > 20 && (
                          <li className="text-[10px] text-gray-400 italic ml-3">
                            + {nodes.length - 20}개 더...
                          </li>
                        )}
                      </ul>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </aside>
        )}
      </div>
    </div>
  );
};

export default GraphExplorerView;
