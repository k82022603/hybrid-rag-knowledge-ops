package com.knowledge.backend.util;

import static org.junit.jupiter.api.Assertions.*;

import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;

/**
 * Unit tests for InputSanitizer
 *
 * <p>Tests XSS prevention, HTML tag removal, and input sanitization.
 * Part of STORY-053 Security Hardening.
 */
class InputSanitizerTest {

    @Nested
    @DisplayName("Basic Sanitization Tests")
    class BasicSanitizationTests {

        @Test
        @DisplayName("Should return null for null input")
        void shouldReturnNullForNullInput() {
            assertNull(InputSanitizer.sanitize(null));
        }

        @Test
        @DisplayName("Should return empty string for empty input")
        void shouldReturnEmptyForEmptyInput() {
            assertEquals("", InputSanitizer.sanitize(""));
        }

        @Test
        @DisplayName("Should pass through safe text unchanged")
        void shouldPassThroughSafeText() {
            String input = "How to configure Spring Boot security?";
            assertEquals(input, InputSanitizer.sanitize(input));
        }

        @Test
        @DisplayName("Should preserve Korean text")
        void shouldPreserveKoreanText() {
            String input = "스프링 부트 보안 설정 방법은?";
            assertEquals(input, InputSanitizer.sanitize(input));
        }

        @Test
        @DisplayName("Should preserve special characters that are not XSS")
        void shouldPreserveNonXssSpecialCharacters() {
            String input = "query with (parentheses) and [brackets] and {braces}";
            assertEquals(input, InputSanitizer.sanitize(input));
        }
    }

    @Nested
    @DisplayName("XSS Prevention Tests")
    class XssPreventionTests {

        @Test
        @DisplayName("Should remove script tags")
        void shouldRemoveScriptTags() {
            String input = "<script>alert('xss')</script>normal text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("<script>"));
            assertFalse(result.contains("</script>"));
            assertTrue(result.contains("normal text"));
        }

        @Test
        @DisplayName("Should remove script tags case-insensitive")
        void shouldRemoveScriptTagsCaseInsensitive() {
            String input = "<SCRIPT>alert('xss')</SCRIPT>text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.toLowerCase().contains("<script>"));
            assertTrue(result.contains("text"));
        }

        @Test
        @DisplayName("Should remove inline event handlers")
        void shouldRemoveInlineEventHandlers() {
            String input = "text onclick=alert(1) more text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("onclick="));
        }

        @Test
        @DisplayName("Should remove onerror handler")
        void shouldRemoveOnerrorHandler() {
            String input = "text onerror=alert('xss') more text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("onerror="));
        }

        @Test
        @DisplayName("Should remove javascript protocol")
        void shouldRemoveJavascriptProtocol() {
            String input = "javascript:alert(document.cookie)";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.toLowerCase().contains("javascript:"));
        }

        @Test
        @DisplayName("Should remove HTML tags")
        void shouldRemoveHtmlTags() {
            String input = "<b>bold</b> and <i>italic</i> text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("<b>"));
            assertFalse(result.contains("</b>"));
            assertFalse(result.contains("<i>"));
            assertTrue(result.contains("bold"));
            assertTrue(result.contains("italic"));
        }

        @Test
        @DisplayName("Should remove img tag with onerror")
        void shouldRemoveImgTagWithOnerror() {
            String input = "<img src=x onerror=alert(1)>text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("<img"));
            assertFalse(result.contains("onerror="));
        }

        @Test
        @DisplayName("Should remove iframe tags")
        void shouldRemoveIframeTags() {
            String input = "<iframe src='evil.com'></iframe>safe text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("<iframe"));
            assertTrue(result.contains("safe text"));
        }

        @Test
        @DisplayName("Should remove style tags with content")
        void shouldRemoveStyleTags() {
            String input = "<style>body{display:none}</style>visible text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("<style>"));
            assertFalse(result.contains("display:none"));
            assertTrue(result.contains("visible text"));
        }

        @Test
        @DisplayName("Should remove data URI with base64")
        void shouldRemoveDataUri() {
            String input = "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg==";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("base64"));
        }

        @Test
        @DisplayName("Should remove vbscript protocol")
        void shouldRemoveVbscriptProtocol() {
            String input = "vbscript:MsgBox('xss')";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.toLowerCase().contains("vbscript:"));
        }
    }

    @Nested
    @DisplayName("XSS Detection Tests")
    class XssDetectionTests {

        @Test
        @DisplayName("Should detect script tag pattern")
        void shouldDetectScriptTag() {
            assertTrue(InputSanitizer.containsXssPatterns("<script>alert(1)</script>"));
        }

        @Test
        @DisplayName("Should detect event handler pattern")
        void shouldDetectEventHandler() {
            assertTrue(InputSanitizer.containsXssPatterns("onclick=alert(1)"));
        }

        @Test
        @DisplayName("Should detect javascript protocol")
        void shouldDetectJavascriptProtocol() {
            assertTrue(InputSanitizer.containsXssPatterns("javascript:void(0)"));
        }

        @Test
        @DisplayName("Should detect HTML tags")
        void shouldDetectHtmlTags() {
            assertTrue(InputSanitizer.containsXssPatterns("<img src=x>"));
        }

        @Test
        @DisplayName("Should not detect false positives in normal text")
        void shouldNotDetectFalsePositives() {
            assertFalse(InputSanitizer.containsXssPatterns("How to configure Spring Security?"));
            assertFalse(InputSanitizer.containsXssPatterns("검색어 입력"));
            assertFalse(InputSanitizer.containsXssPatterns("normal query with numbers 123"));
        }

        @Test
        @DisplayName("Should return false for null input")
        void shouldReturnFalseForNull() {
            assertFalse(InputSanitizer.containsXssPatterns(null));
        }

        @Test
        @DisplayName("Should return false for empty input")
        void shouldReturnFalseForEmpty() {
            assertFalse(InputSanitizer.containsXssPatterns(""));
        }
    }

    @Nested
    @DisplayName("Edge Case Tests")
    class EdgeCaseTests {

        @Test
        @DisplayName("Should handle mixed safe and unsafe content")
        void shouldHandleMixedContent() {
            String input = "Search for <script>alert('xss')</script> Spring Boot configuration";
            String result = InputSanitizer.sanitize(input);
            assertTrue(result.contains("Search for"));
            assertTrue(result.contains("Spring Boot configuration"));
            assertFalse(result.contains("<script>"));
        }

        @Test
        @DisplayName("Should handle nested tags")
        void shouldHandleNestedTags() {
            String input = "<div><script>alert(1)</script></div>text";
            String result = InputSanitizer.sanitize(input);
            assertFalse(result.contains("<"));
            assertFalse(result.contains(">"));
            assertTrue(result.contains("text"));
        }

        @Test
        @DisplayName("Should trim whitespace")
        void shouldTrimWhitespace() {
            String input = "   query text   ";
            assertEquals("query text", InputSanitizer.sanitize(input));
        }

        @Test
        @DisplayName("Should handle long input without issues")
        void shouldHandleLongInput() {
            String input = "a".repeat(5000);
            String result = InputSanitizer.sanitize(input);
            assertEquals(5000, result.length());
        }
    }
}
