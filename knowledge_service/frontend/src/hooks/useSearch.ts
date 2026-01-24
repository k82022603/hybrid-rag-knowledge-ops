import { useState, useCallback } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { searchService, type SearchQuery } from '@/services/searchService';

/**
 * useSearch - 검색 기능 커스텀 훅
 */
export const useSearch = () => {
  const [query, setQuery] = useState('');
  const [streamingContent, setStreamingContent] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);

  // 키워드 검색 Mutation
  const searchMutation = useMutation({
    mutationFn: (params: SearchQuery) => searchService.search(params),
  });

  // 스트리밍 검색
  const startStreamingSearch = useCallback((searchQuery: string) => {
    setIsStreaming(true);
    setStreamingContent('');

    const eventSource = searchService.streamSearch(
      searchQuery,
      (data) => {
        setStreamingContent((prev) => prev + data);
      },
      (_error) => {
        setIsStreaming(false);
      },
      () => {
        setIsStreaming(false);
      }
    );

    return eventSource;
  }, []);

  return {
    query,
    setQuery,
    searchMutation,
    streamingContent,
    isStreaming,
    startStreamingSearch,
    search: (params: SearchQuery) => searchMutation.mutate(params),
    searchAsync: (params: SearchQuery) => searchMutation.mutateAsync(params),
    isLoading: searchMutation.isPending,
    error: searchMutation.error,
    data: searchMutation.data,
  };
};

/**
 * useExpertSearch - 전문가 검색 훅
 */
export const useExpertSearch = (topic: string, enabled = false) => {
  return useQuery({
    queryKey: ['experts', topic],
    queryFn: () => searchService.findExperts(topic),
    enabled: enabled && !!topic,
  });
};

export default useSearch;
