/**
 * GraphPanel - Knowledge Graph visualization panel
 *
 * Renders an interactive force-directed graph using react-force-graph-2d.
 * Fetches subgraph data from /api/v1/graph/subgraph for given entity names.
 */
import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import { XMarkIcon, ArrowPathIcon } from '@heroicons/react/24/outline';
import ForceGraph2D from 'react-force-graph-2d';
import api from '@/services/api';
import type { SubgraphData } from '../types';

export interface GraphPanelProps {
  /** Entity names to visualize */
  entityNames: string[];
  /** Called when the panel close button is clicked */
  onClose: () => void;
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

const GraphPanel: React.FC<GraphPanelProps> = ({ entityNames, onClose }) => {
  const [graphData, setGraphData] = useState<SubgraphData | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [dimensions, setDimensions] = useState({ width: 400, height: 400 });

  // Fetch subgraph data when entityNames change
  useEffect(() => {
    if (entityNames.length === 0) return;

    const fetchSubgraph = async () => {
      setIsLoading(true);
      setError(null);
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

  // Node paint callback
  const paintNode = useCallback(
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    (node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
      const label = node.name || node.id;
      const fontSize = node.isCenter ? 14 / globalScale : 11 / globalScale;
      const nodeRadius = node.isCenter ? 8 : 5;
      const color = NODE_COLORS[node.type] || DEFAULT_NODE_COLOR;

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
    [],
  );

  return (
    <div
      className="flex flex-col h-full bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700"
      data-testid="graph-panel"
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
        <div>
          <h3 className="text-sm font-semibold text-gray-900 dark:text-white">
            Knowledge Graph
          </h3>
          {graphData && (
            <p className="text-2xs text-gray-500 dark:text-gray-400">
              {graphData.node_count} nodes &middot; {graphData.center}
            </p>
          )}
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg text-gray-400 hover:text-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
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
          <ForceGraph2D
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
            linkLabel="label"
            linkColor={() => '#cbd5e1'}
            linkDirectionalArrowLength={4}
            linkDirectionalArrowRelPos={1}
            cooldownTicks={100}
          />
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
