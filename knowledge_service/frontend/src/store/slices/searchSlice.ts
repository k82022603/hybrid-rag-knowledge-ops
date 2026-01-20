import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface SearchResult {
  chunkId: string;
  documentId: string;
  content: string;
  score: number;
  metadata: {
    documentType?: string;
    projectName?: string;
    category?: {
      level1: string;
      level2: string;
      level3: string;
    };
    summary?: string;
  };
}

interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: string;
  sources?: SearchResult[];
}

interface SearchState {
  query: string;
  results: SearchResult[];
  chatMessages: ChatMessage[];
  isLoading: boolean;
  isStreaming: boolean;
  streamingMessage: string;
  error: string | null;
  filters: {
    documentType?: string;
    projectName?: string;
    dateFrom?: string;
    dateTo?: string;
  };
  pagination: {
    page: number;
    pageSize: number;
    totalCount: number;
  };
}

const initialState: SearchState = {
  query: '',
  results: [],
  chatMessages: [],
  isLoading: false,
  isStreaming: false,
  streamingMessage: '',
  error: null,
  filters: {},
  pagination: {
    page: 1,
    pageSize: 10,
    totalCount: 0,
  },
};

const searchSlice = createSlice({
  name: 'search',
  initialState,
  reducers: {
    setQuery: (state, action: PayloadAction<string>) => {
      state.query = action.payload;
    },
    searchStart: (state) => {
      state.isLoading = true;
      state.error = null;
    },
    searchSuccess: (
      state,
      action: PayloadAction<{ results: SearchResult[]; totalCount: number }>
    ) => {
      state.isLoading = false;
      state.results = action.payload.results;
      state.pagination.totalCount = action.payload.totalCount;
    },
    searchFailure: (state, action: PayloadAction<string>) => {
      state.isLoading = false;
      state.error = action.payload;
    },
    addChatMessage: (state, action: PayloadAction<ChatMessage>) => {
      state.chatMessages.push(action.payload);
    },
    setStreamingMessage: (state, action: PayloadAction<string>) => {
      state.streamingMessage = action.payload;
      state.isStreaming = true;
    },
    appendStreamingMessage: (state, action: PayloadAction<string>) => {
      state.streamingMessage += action.payload;
    },
    endStreaming: (state) => {
      state.isStreaming = false;
      state.streamingMessage = '';
    },
    setFilters: (
      state,
      action: PayloadAction<Partial<SearchState['filters']>>
    ) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearFilters: (state) => {
      state.filters = {};
    },
    setPage: (state, action: PayloadAction<number>) => {
      state.pagination.page = action.payload;
    },
    clearSearch: (state) => {
      state.query = '';
      state.results = [];
      state.error = null;
      state.pagination.page = 1;
      state.pagination.totalCount = 0;
    },
    clearChat: (state) => {
      state.chatMessages = [];
    },
  },
});

export const {
  setQuery,
  searchStart,
  searchSuccess,
  searchFailure,
  addChatMessage,
  setStreamingMessage,
  appendStreamingMessage,
  endStreaming,
  setFilters,
  clearFilters,
  setPage,
  clearSearch,
  clearChat,
} = searchSlice.actions;

export default searchSlice.reducer;
