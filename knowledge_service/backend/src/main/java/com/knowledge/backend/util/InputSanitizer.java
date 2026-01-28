package com.knowledge.backend.util;

import java.util.regex.Pattern;

/**
 * Input Sanitizer Utility
 *
 * <p>Provides XSS prevention by sanitizing user input.
 * Strips HTML tags, script injections, and other potentially dangerous patterns.
 *
 * <p>Usage:
 * <pre>
 * String safe = InputSanitizer.sanitize(userInput);
 * </pre>
 *
 * @since 1.0.0 (Sprint 04 - STORY-053 Security Hardening)
 */
public final class InputSanitizer {

    private InputSanitizer() {
        // Utility class - prevent instantiation
    }

    /** Pattern to match HTML/XML tags including script, style, iframe, object, embed */
    private static final Pattern HTML_TAG_PATTERN = Pattern.compile(
        "<[^>]*>", Pattern.CASE_INSENSITIVE
    );

    /** Pattern to match script content: <script>...</script> */
    private static final Pattern SCRIPT_PATTERN = Pattern.compile(
        "<script[^>]*>.*?</script>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL
    );

    /** Pattern to match style content: <style>...</style> */
    private static final Pattern STYLE_PATTERN = Pattern.compile(
        "<style[^>]*>.*?</style>", Pattern.CASE_INSENSITIVE | Pattern.DOTALL
    );

    /** Pattern to match javascript: protocol in URLs */
    private static final Pattern JAVASCRIPT_PROTOCOL_PATTERN = Pattern.compile(
        "javascript\\s*:", Pattern.CASE_INSENSITIVE
    );

    /** Pattern to match on* event handlers (onclick, onerror, onload, etc.) */
    private static final Pattern EVENT_HANDLER_PATTERN = Pattern.compile(
        "\\bon\\w+\\s*=", Pattern.CASE_INSENSITIVE
    );

    /** Pattern to match data: protocol URIs that could contain executable content */
    private static final Pattern DATA_PROTOCOL_PATTERN = Pattern.compile(
        "data\\s*:[^,]*;base64", Pattern.CASE_INSENSITIVE
    );

    /** Pattern to match vbscript: protocol */
    private static final Pattern VBSCRIPT_PROTOCOL_PATTERN = Pattern.compile(
        "vbscript\\s*:", Pattern.CASE_INSENSITIVE
    );

    /**
     * Sanitize user input by removing potentially dangerous content.
     *
     * <p>Removes:
     * <ul>
     *   <li>HTML/XML tags (including script, style, iframe, etc.)</li>
     *   <li>JavaScript protocol references</li>
     *   <li>Event handler attributes (onclick, onerror, etc.)</li>
     *   <li>Data URI schemes with base64 content</li>
     *   <li>VBScript protocol references</li>
     * </ul>
     *
     * @param input raw user input (may be null)
     * @return sanitized string, or null if input is null
     */
    public static String sanitize(String input) {
        if (input == null) {
            return null;
        }

        String sanitized = input;

        // Remove script blocks first (before stripping tags to handle nested content)
        sanitized = SCRIPT_PATTERN.matcher(sanitized).replaceAll("");

        // Remove style blocks
        sanitized = STYLE_PATTERN.matcher(sanitized).replaceAll("");

        // Remove all HTML tags
        sanitized = HTML_TAG_PATTERN.matcher(sanitized).replaceAll("");

        // Remove javascript: protocol
        sanitized = JAVASCRIPT_PROTOCOL_PATTERN.matcher(sanitized).replaceAll("");

        // Remove event handlers (onclick=, onerror=, etc.)
        sanitized = EVENT_HANDLER_PATTERN.matcher(sanitized).replaceAll("");

        // Remove data: URIs with base64 content
        sanitized = DATA_PROTOCOL_PATTERN.matcher(sanitized).replaceAll("");

        // Remove vbscript: protocol
        sanitized = VBSCRIPT_PROTOCOL_PATTERN.matcher(sanitized).replaceAll("");

        // Trim and collapse multiple whitespace
        sanitized = sanitized.trim();

        return sanitized;
    }

    /**
     * Check if the input contains potentially dangerous XSS patterns.
     *
     * @param input raw user input
     * @return true if suspicious patterns are detected
     */
    public static boolean containsXssPatterns(String input) {
        if (input == null || input.isEmpty()) {
            return false;
        }
        return HTML_TAG_PATTERN.matcher(input).find()
            || SCRIPT_PATTERN.matcher(input).find()
            || JAVASCRIPT_PROTOCOL_PATTERN.matcher(input).find()
            || EVENT_HANDLER_PATTERN.matcher(input).find();
    }
}
