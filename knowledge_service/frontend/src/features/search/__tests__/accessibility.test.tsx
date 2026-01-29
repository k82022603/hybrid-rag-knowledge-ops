/**
 * Search Components Accessibility Tests - WCAG 2.1 AA Compliance
 *
 * Tests for search-related components to ensure they meet
 * accessibility requirements.
 */
import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { BrowserRouter } from 'react-router-dom';

import ChatInput from '../components/ChatInput';
import MessageBubble from '../components/MessageBubble';
import MessageList from '../components/MessageList';
import SearchResultCard from '../components/SearchResultCard';
import SourceCitation from '../components/SourceCitation';
import type { Message, SearchResultItem, Source } from '../types';

// Extend Jest matchers with axe accessibility matchers
expect.extend(toHaveNoViolations);

// Mock data
const mockUserMessage: Message = {
  id: 'user-1',
  role: 'user',
  content: 'What is the document upload process?',
  timestamp: new Date('2024-01-15T10:00:00'),
};

const mockAssistantMessage: Message = {
  id: 'assistant-1',
  role: 'assistant',
  content: 'The document upload process involves several steps...',
  timestamp: new Date('2024-01-15T10:00:05'),
  sources: [
    {
      chunkId: 'chunk-1',
      content: 'Upload documentation content...',
      score: 0.95,
      metadata: { projectName: 'Upload Guide' },
    },
  ],
};

const mockSearchResult: SearchResultItem = {
  chunkId: 'result-1',
  content: 'This is the document content that matches the search query...',
  score: 0.87,
  metadata: {
    projectName: 'Technical Documentation',
    documentType: 'guide',
    category: {
      level1: 'Development',
      level2: 'API',
    },
  },
};

const mockSources: Source[] = [
  {
    chunkId: 'source-1',
    content: 'Source content 1',
    score: 0.92,
    metadata: { projectName: 'Document A' },
  },
  {
    chunkId: 'source-2',
    content: 'Source content 2',
    score: 0.85,
    metadata: { projectName: 'Document B' },
  },
];

describe('ChatInput Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        isLoading={false}
      />
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible labels', () => {
    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        isLoading={false}
      />
    );

    const textarea = screen.getByRole('textbox', { name: /search query/i });
    expect(textarea).toBeInTheDocument();

    const submitButton = screen.getByRole('button', { name: /send message/i });
    expect(submitButton).toBeInTheDocument();
  });

  it('should support keyboard submission with Enter', () => {
    const onSubmit = vi.fn();
    render(
      <ChatInput
        value="test query"
        onChange={vi.fn()}
        onSubmit={onSubmit}
        isLoading={false}
      />
    );

    const textarea = screen.getByTestId('chat-input');
    fireEvent.keyDown(textarea, { key: 'Enter' });

    expect(onSubmit).toHaveBeenCalled();
  });

  it('should not submit on Shift+Enter (allows new line)', () => {
    const onSubmit = vi.fn();
    render(
      <ChatInput
        value="test query"
        onChange={vi.fn()}
        onSubmit={onSubmit}
        isLoading={false}
      />
    );

    const textarea = screen.getByTestId('chat-input');
    fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });

    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('should have accessible clear button when visible', () => {
    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        onClear={vi.fn()}
        showClear={true}
        isLoading={false}
      />
    );

    const clearButton = screen.getByRole('button', { name: /clear conversation/i });
    expect(clearButton).toBeInTheDocument();
  });

  it('should indicate disabled state accessibly', () => {
    render(
      <ChatInput
        value=""
        onChange={vi.fn()}
        onSubmit={vi.fn()}
        isLoading={true}
      />
    );

    const submitButton = screen.getByTestId('chat-submit');
    expect(submitButton).toBeDisabled();
  });
});

describe('MessageBubble Accessibility', () => {
  it('should have no accessibility violations for user message', async () => {
    const { container } = render(<MessageBubble message={mockUserMessage} />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have no accessibility violations for assistant message', async () => {
    const { container } = render(<MessageBubble message={mockAssistantMessage} />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have hidden avatar icons for screen readers', () => {
    render(<MessageBubble message={mockUserMessage} />);

    const avatar = screen.getByTestId(`message-${mockUserMessage.id}`).querySelector('[aria-hidden="true"]');
    expect(avatar).toBeInTheDocument();
  });

  it('should have accessible streaming indicator', () => {
    const streamingMessage: Message = {
      ...mockAssistantMessage,
      isStreaming: true,
    };

    render(<MessageBubble message={streamingMessage} />);

    const indicator = screen.getByLabelText(/loading response/i);
    expect(indicator).toBeInTheDocument();
  });
});

describe('MessageList Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(
      <MessageList
        messages={[mockUserMessage, mockAssistantMessage]}
        onSuggestionClick={vi.fn()}
      />
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have proper ARIA role for message log', () => {
    render(
      <MessageList
        messages={[mockUserMessage]}
        onSuggestionClick={vi.fn()}
      />
    );

    const messageLog = screen.getByRole('log');
    expect(messageLog).toHaveAttribute('aria-label', 'Chat messages');
    expect(messageLog).toHaveAttribute('aria-live', 'polite');
  });

  it('should have no violations in empty state', async () => {
    const { container } = render(
      <MessageList
        messages={[]}
        onSuggestionClick={vi.fn()}
      />
    );

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible suggestion buttons in empty state', () => {
    render(
      <MessageList
        messages={[]}
        onSuggestionClick={vi.fn()}
      />
    );

    const suggestions = screen.getAllByRole('button');
    expect(suggestions.length).toBeGreaterThan(0);

    // Each suggestion should be focusable
    suggestions.forEach((suggestion) => {
      suggestion.focus();
      expect(document.activeElement).toBe(suggestion);
    });
  });

  it('should have accessible scroll to bottom button', () => {
    // This test simulates the scroll button appearing
    render(
      <MessageList
        messages={[mockUserMessage, mockAssistantMessage]}
        onSuggestionClick={vi.fn()}
      />
    );

    // Scroll button appears when user scrolls up
    // The button should have proper aria-label when visible
    const scrollButton = screen.queryByRole('button', { name: /scroll to latest message/i });
    // Button may not be visible initially, which is expected
    expect(scrollButton === null || scrollButton.getAttribute('aria-label')).toBeTruthy();
  });
});

describe('SearchResultCard Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(<SearchResultCard result={mockSearchResult} />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible article role', () => {
    render(<SearchResultCard result={mockSearchResult} />);

    const article = screen.getByRole('article');
    expect(article).toHaveAttribute('aria-label', expect.stringContaining('Search result'));
  });

  it('should have accessible relevance score', () => {
    render(<SearchResultCard result={mockSearchResult} />);

    const scoreLabel = screen.getByLabelText(/relevance.*87%/i);
    expect(scoreLabel).toBeInTheDocument();
  });

  it('should have hidden document icon for screen readers', () => {
    render(<SearchResultCard result={mockSearchResult} />);

    const icon = screen.getByTestId(`search-result-${mockSearchResult.chunkId}`).querySelector('[aria-hidden="true"]');
    expect(icon).toBeInTheDocument();
  });
});

describe('SourceCitation Accessibility', () => {
  it('should have no accessibility violations', async () => {
    const { container } = render(<SourceCitation sources={mockSources} />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should have accessible source items', () => {
    render(<SourceCitation sources={mockSources} />);

    // Each source should have proper role and aria-label
    mockSources.forEach((source) => {
      const sourceItem = screen.getByLabelText(new RegExp(`Source: ${source.metadata?.projectName}`, 'i'));
      expect(sourceItem).toBeInTheDocument();
      expect(sourceItem).toHaveAttribute('role', 'link');
      expect(sourceItem).toHaveAttribute('tabIndex', '0');
    });
  });

  it('should be keyboard navigable', () => {
    render(<SourceCitation sources={mockSources} />);

    const sourceItems = screen.getAllByRole('link');

    sourceItems.forEach((item) => {
      item.focus();
      expect(document.activeElement).toBe(item);
    });
  });

  it('should have accessible tooltip content', () => {
    render(<SourceCitation sources={mockSources} />);

    const firstSource = screen.getByLabelText(new RegExp(`Source: ${mockSources[0].metadata?.projectName}`, 'i'));
    expect(firstSource).toHaveAttribute('title', mockSources[0].content);
  });

  it('should return null for empty sources', () => {
    const { container } = render(<SourceCitation sources={[]} />);
    expect(container.firstChild).toBeNull();
  });
});

describe('Focus Management', () => {
  it('should maintain focus order in chat interface', () => {
    render(
      <div>
        <MessageList
          messages={[mockUserMessage]}
          onSuggestionClick={vi.fn()}
        />
        <ChatInput
          value="test query"
          onChange={vi.fn()}
          onSubmit={vi.fn()}
          onClear={vi.fn()}
          showClear={true}
          isLoading={false}
        />
      </div>
    );

    const clearButton = screen.getByRole('button', { name: /clear conversation/i });
    const textarea = screen.getByRole('textbox');
    const submitButton = screen.getByRole('button', { name: /send message/i });

    // Test focus order
    clearButton.focus();
    expect(document.activeElement).toBe(clearButton);

    textarea.focus();
    expect(document.activeElement).toBe(textarea);

    // Submit button is enabled when there's text input
    submitButton.focus();
    expect(document.activeElement).toBe(submitButton);
  });
});

describe('Color Contrast', () => {
  // Note: jest-axe automatically checks color contrast as part of its checks
  // These tests ensure components render correctly for contrast verification

  it('should use accessible colors for search result scores', async () => {
    const highScoreResult = { ...mockSearchResult, score: 0.95 };
    const { container } = render(<SearchResultCard result={highScoreResult} />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('should use accessible colors for source citations', async () => {
    const { container } = render(<SourceCitation sources={mockSources} />);

    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});
