/**
 * useChatSearch - Non-streaming chat search hook
 *
 * Uses synchronous POST /search/chat instead of SSE streaming.
 * Returns answer + sources in a single JSON response.
 */
import { useState, useCallback, useRef, useEffect } from 'react';
import { searchService } from '@/services/searchService';
import type { Message, Source } from '../types';

export interface UseChatSearchReturn {
  query: string;
  setQuery: (value: string) => void;
  messages: Message[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (queryOverride?: string) => void;
  clearMessages: () => void;
  dismissError: () => void;
}

function createMessageId(role: 'user' | 'assistant'): string {
  return `${role}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

function mapSources(rawSources: Array<Record<string, unknown>>): Source[] {
  return rawSources.map((s) => ({
    chunkId: (s.chunk_id ?? s.chunkId ?? '') as string,
    documentId: (s.document_id ?? s.documentId ?? '') as string,
    content: (s.content ?? s.snippet ?? '') as string,
    score: (s.score ?? 0) as number,
    title: (s.title ?? '') as string,
    index: (s.index ?? 0) as number,
    sourceType: (s.source_type ?? s.sourceType ?? '') as string,
    metadata: s.metadata as Source['metadata'],
    graphContext: (s.graphContext ?? (s.graph_context ? {
      relatedEntities: (s.graph_context as Record<string, unknown>).related_entities ?? [],
      community: (s.graph_context as Record<string, unknown>).community ?? '',
    } : undefined)) as Source['graphContext'],
    hasEmbedding: (s.has_embedding ?? s.hasEmbedding) as boolean | undefined,
  }));
}

export const useChatSearch = (initialQuery?: string): UseChatSearchReturn => {
  const [query, setQuery] = useState('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const conversationIdRef = useRef<string | undefined>(undefined);
  const initialQueryHandledRef = useRef(false);

  const sendMessage = useCallback(async (queryOverride?: string) => {
    const trimmed = (queryOverride ?? query).trim();
    if (!trimmed || isLoading) return;

    // Add user message
    const userMsg: Message = {
      id: createMessageId('user'),
      role: 'user',
      content: trimmed,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setQuery('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await searchService.chatSearch({
        query: trimmed,
        conversationId: conversationIdRef.current,
        topK: 5,
      });

      // Store conversation ID for multi-turn
      if (response.conversationId) {
        conversationIdRef.current = response.conversationId;
      }

      // Map sources
      const sources = mapSources(response.sources ?? []);

      // Add assistant message
      const assistantMsg: Message = {
        id: createMessageId('assistant'),
        role: 'assistant',
        content: response.answer,
        timestamp: new Date(),
        sources: sources.length > 0 ? sources : undefined,
      };
      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err) {
      const errMsg = err instanceof Error ? err.message : '검색 중 오류가 발생했습니다';
      setError(errMsg);
    } finally {
      setIsLoading(false);
    }
  }, [query, isLoading]);

  // Auto-send initial query from URL params (dashboard quick search)
  useEffect(() => {
    if (initialQuery && !initialQueryHandledRef.current) {
      initialQueryHandledRef.current = true;
      sendMessage(initialQuery);
    }
  }, [initialQuery]); // eslint-disable-line react-hooks/exhaustive-deps

  const clearMessages = useCallback(() => {
    setMessages([]);
    conversationIdRef.current = undefined;
    setError(null);
  }, []);

  const dismissError = useCallback(() => {
    setError(null);
  }, []);

  return {
    query,
    setQuery,
    messages,
    isLoading,
    error,
    sendMessage,
    clearMessages,
    dismissError,
  };
};

export default useChatSearch;
