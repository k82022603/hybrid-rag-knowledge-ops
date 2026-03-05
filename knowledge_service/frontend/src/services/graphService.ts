/**
 * GraphService - Knowledge Graph API service
 *
 * Provides endpoints for graph exploration:
 * - Full graph overview (node types + counts)
 * - Subgraph exploration by entity
 * - Entity detail with related documents
 *
 * Backend API: /api/v1/graph/
 */
import api from './api';

/** Graph node from Neo4j */
export interface GraphNode {
  id: string;
  name?: string;
  label?: string;
  type: string;
  [key: string]: unknown;
}

/** Graph edge from Neo4j */
export interface GraphEdge {
  source: string;
  target: string;
  type: string;
  [key: string]: unknown;
}

/** Subgraph API response */
export interface SubgraphData {
  center: string;
  nodes: GraphNode[];
  edges: GraphEdge[];
  node_count: number;
}

/** Entity detail response */
export interface EntityDetail {
  name: string;
  type: string;
  description?: string;
  labels: string[];
  properties: Record<string, unknown>;
}

/**
 * GraphService - Graph exploration API
 */
export const graphService = {
  /**
   * Explore subgraph from a center entity
   *
   * POST /api/v1/graph/subgraph
   */
  async getSubgraph(
    entityName: string,
    depth = 2,
    limit = 200
  ): Promise<SubgraphData> {
    const response = await api.post<SubgraphData>('/graph/subgraph', {
      entity_name: entityName,
      depth,
      limit,
    });
    return response.data;
  },

  /**
   * Get full graph overview - fetches a broad subgraph from a generic root
   *
   * Uses the subgraph endpoint with a high limit to get an overview.
   * The backend explores from the given entity outward.
   *
   * POST /api/v1/graph/subgraph
   */
  async getGraphOverview(limit = 200): Promise<SubgraphData> {
    const response = await api.post<SubgraphData>('/graph/subgraph', {
      entity_name: '*',
      depth: 3,
      limit,
    });
    return response.data;
  },

  /**
   * Get entity detail
   *
   * GET /api/v1/graph/entities/{name}
   */
  async getEntity(name: string): Promise<EntityDetail> {
    const response = await api.get<EntityDetail>(
      `/graph/entities/${encodeURIComponent(name)}`
    );
    return response.data;
  },

  /**
   * Search experts by topic
   *
   * POST /api/v1/graph/experts
   */
  async searchExperts(
    topic: string,
    limit = 10
  ): Promise<{
    topic: string;
    experts: Array<{
      name: string;
      expertise: string[];
      score: number;
      description?: string;
      related_projects: string[];
    }>;
    total: number;
  }> {
    const response = await api.post('/graph/experts', { topic, limit });
    return response.data;
  },
};

export default graphService;
