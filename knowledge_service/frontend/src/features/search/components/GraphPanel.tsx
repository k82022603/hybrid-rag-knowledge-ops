/**
 * GraphPanel - Knowledge Graph visualization panel
 *
 * Renders an interactive force-directed graph using react-force-graph-2d.
 * Fetches subgraph data from /api/v1/graph/subgraph for given entity names.
 *
 * Features:
 * - Node click: shows detail tooltip (name, type, connected edges count)
 * - Zoom/pan controls: zoom in/out buttons + fit-all reset
 * - Responsive layout with ResizeObserver
 */
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  XMarkIcon,
  ArrowPathIcon,
  PlusIcon,
  MinusIcon,
  ArrowsPointingOutIcon,
} from '@heroicons/react/24/outline';
import ForceGraph2D from 'react-force-graph-2d';
import api from '@/services/api';
import type { SubgraphData } from '../types';

export interface GraphPanelProps {
  /** Entity names to visualize */
  entityNames: string[];
  /** Called when the panel close button is clicked */
  onClose: () => void;
}

/** Internal node type used in the force graph */
interface ForceNode {
  id: string;
  name: string;
  type: string;
  isCenter: boolean;
  x?: number;
  y?: number;
}

/** Selected node detail for the tooltip */
interface SelectedNodeInfo {
  node: ForceNode;
  edgeCount: number;
  connectedTypes: string[];
}

/** Color mapping by node type */
const NODE_COLORS: Record<string, string> = {
  Person: '#2563eb',
  Technology: '#0d9488',
  Topic: '#d97706',
  Knowledge: '#16a34a',
  Keyword: '#64748b',
  Organization: '#7c3aed',
  Process: '#dc2626',
};
const DEFAULT_NODE_COLOR = '#94a3b8';

const ZOOM_STEP = 1.5;

const GraphPanel: React.FC<GraphPanelProps> = ({ entityNames, onClose }) => {
  const [graphData, setGraphData] = useState<SubgraphData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<SelectedNodeInfo | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const graphRef = useRef<{ zoomToFit: (ms?: number) => void; zoom: (k: number, ms?: number) => void } | null>(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 400 });

  // Fetch subgraph data when entityNames change
  useEffect(() => {
    if (entityNames.length === 0) return;

    const fetchSubgraph = async () => {
      setIsLoading(true);
      setError(null);
      setSelectedNode(null);
      try {
        const response = await api.post('/graph/subgraph', {
          entity_name: entityNames[0],
          depth: 2,
          limit: 50,
        });
        setGraphData(response.data);
      } catch {
        setError('그래프 데이터를 불러올 수 없습니다');
      } finally {
        setIsLoading(false);
      }
    };

    fetchSubgraph();
  }, [entityNames]);

  // Observe container size for responsive rendering
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      const { width, height } = entries[0].contentRect;
      setDimensions({ width: Math.floor(width), height: Math.floor(height) });
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Transform SubgraphData to react-force-graph format
  const forceGraphData = useMemo(() => {
    if (!graphData) return { nodes: [], links: [] };
    return {
      nodes: graphData.nodes.map((n) => ({
        id: n.id,
        name: n.name || n.label || n.id,
        type: n.type,
        isCenter:
          n.name === graphData.center || n.label === graphData.center || n.id === graphData.center,
      })),
      links: graphData.edges.map((e) => ({
        source: e.source,
        target: e.target,
        label: e.type,
      })),
    };
  }, [graphData]);

  // Count edges connected to a given node
  const getNodeEdgeInfo = useCallback(
    (nodeId: string) => {
      if (!graphData) return { count: 0, types: [] as string[] };
      const connected = graphData.edges.filter(
        (e) => e.source === nodeId || e.target === nodeId,
      );
      const types = [...new Set(connected.map((e) => e.type))];
      return { count: connected.length, types };
    },
    [graphData],
  );

  // Handle node click - show detail tooltip
  const handleNodeClick = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any) => {
      const edgeInfo = getNodeEdgeInfo(node.id);
      setSelectedNode({
        node: {
          id: node.id,
          name: node.name || node.id,
          type: node.type,
          isCenter: node.isCenter,
        },
        edgeCount: edgeInfo.count,
        connectedTypes: edgeInfo.types,
      });
    },
    [getNodeEdgeInfo],
  );

  // Handle background click - dismiss tooltip
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
    graphRef.current?.zoomToFit(400);
  }, []);

  // Node paint callback - highlight selected node
  const paintNode = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name || node.id;
      const fontSize = node.isCenter ? 14 / globalScale : 11 / globalScale;
      const nodeRadius = node.isCenter ? 8 : 5;
      const color = NODE_COLORS[node.type] || DEFAULT_NODE_COLOR;
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
      if (node.isCenter) {
        ctx.strokeStyle = '#1e40af';
        ctx.lineWidth = 2 / globalScale;
        ctx.stroke();
      }

      // Label
      ctx.font = `${fontSize}px Pretendard, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'top';
      ctx.fillStyle = '#334155';
      ctx.fillText(label, node.x, node.y + nodeRadius + 2);
    },
    [selectedNode],
  );

  return (
    <div
      className="flex flex-col h-full bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700"
      data-testid="graph-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div className="min-w-0">
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Knowledge Graph
          </h3>
          {graphData && (
            <p className="text-2xs text-gray-500 dark:text-gray-400 truncate">
              {graphData.node_count} nodes &middot; {graphData.center}
            </p>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors flex-shrink-0"
          aria-label="Close graph panel"
        >
          <XMarkIcon className="h-4 w-4" />
        </button>
      </div>

      {/* Content */}
      <div ref={containerRef} className="flex-1 min-h-0 relative">
        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-gray-800/50 z-10">
            <ArrowPathIcon className="h-6 w-6 text-primary-500 animate-spin" />
          </div>
        )}

        {error && !isLoading && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-red-500">{error}</p>
          </div>
        )}

        {graphData && !isLoading && forceGraphData.nodes.length > 0 && (
          <>
            <ForceGraph2D
              ref={graphRef as React.Ref<never>}
              graphData={forceGraphData}
              width={dimensions.width}
              height={dimensions.height}
              nodeCanvasObject={paintNode}
              nodePointerAreaPaint={(
                // eslint-disable-next-line @typescript-eslint/no-explicit-any
                node: any,
                color: string,
                ctx: CanvasRenderingContext2D,
              ) => {
                ctx.beginPath();
                ctx.arc(node.x, node.y, 8, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
              }}
              onNodeClick={handleNodeClick}
              onBackgroundClick={handleBackgroundClick}
              linkLabel="label"
              linkColor={() => '#cbd5e1'}
              linkDirectionalArrowLength={4}
              linkDirectionalArrowRelPos={1}
              cooldownTicks={100}
            />

            {/* Zoom Controls */}
            <div
              className="absolute bottom-3 right-3 flex flex-col gap-1 z-10"
              role="toolbar"
              aria-label="Graph zoom controls"
            >
              <button
                onClick={handleZoomIn}
                className="p-1.5 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                aria-label="Zoom in"
                title="Zoom in"
              >
                <PlusIcon className="h-4 w-4 text-gray-600 dark:text-gray-300" />
              </button>
              <button
                onClick={handleZoomOut}
                className="p-1.5 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                aria-label="Zoom out"
                title="Zoom out"
              >
                <MinusIcon className="h-4 w-4 text-gray-600 dark:text-gray-300" />
              </button>
              <button
                onClick={handleZoomReset}
                className="p-1.5 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-sm hover:bg-gray-50 dark:hover:bg-gray-600 transition-colors"
                aria-label="Fit all nodes"
                title="Fit all"
              >
                <ArrowsPointingOutIcon className="h-4 w-4 text-gray-600 dark:text-gray-300" />
              </button>
            </div>

            {/* Node Detail Tooltip */}
            {selectedNode && (
              <div
                className="absolute top-3 left-3 z-10 w-52 bg-white dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg shadow-lg p-3 animate-fade-in"
                data-testid="node-detail-tooltip"
                role="status"
                aria-label={`Selected node: ${selectedNode.node.name}`}
              >
                <div className="flex items-start justify-between gap-2">
                  <h4 className="text-xs font-semibold text-gray-900 dark:text-white break-words min-w-0">
                    {selectedNode.node.name}
                  </h4>
                  <button
                    onClick={() => setSelectedNode(null)}
                    className="p-0.5 rounded text-gray-400 hover:text-gray-600 dark:hover:text-gray-200 flex-shrink-0"
                    aria-label="Close node detail"
                  >
                    <XMarkIcon className="h-3 w-3" />
                  </button>
                </div>
                <div className="mt-1.5 space-y-1">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                      style={{
                        backgroundColor:
                          NODE_COLORS[selectedNode.node.type] || DEFAULT_NODE_COLOR,
                      }}
                    />
                    <span className="text-2xs text-gray-600 dark:text-gray-300">
                      {selectedNode.node.type}
                    </span>
                    {selectedNode.node.isCenter && (
                      <span className="text-2xs font-medium text-primary-600 dark:text-primary-400">
                        (center)
                      </span>
                    )}
                  </div>
                  <p className="text-2xs text-gray-500 dark:text-gray-400">
                    {selectedNode.edgeCount} connection{selectedNode.edgeCount !== 1 ? 's' : ''}
                  </p>
                  {selectedNode.connectedTypes.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1">
                      {selectedNode.connectedTypes.map((t) => (
                        <span
                          key={t}
                          className="px-1.5 py-0.5 bg-gray-100 dark:bg-gray-600 text-2xs text-gray-600 dark:text-gray-300 rounded"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {!graphData && !isLoading && !error && (
          <div className="absolute inset-0 flex items-center justify-center">
            <p className="text-sm text-gray-400 dark:text-gray-500">
              출처에서 Graph 버튼을 클릭하세요
            </p>
          </div>
        )}
      </div>
    </div>
  );
};

export default GraphPanel;
