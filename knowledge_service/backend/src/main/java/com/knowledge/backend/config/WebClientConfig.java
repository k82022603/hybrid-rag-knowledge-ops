package com.knowledge.backend.config;

import io.netty.channel.ChannelOption;
import io.netty.handler.timeout.ReadTimeoutHandler;
import io.netty.handler.timeout.WriteTimeoutHandler;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.client.reactive.ReactorClientHttpConnector;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.netty.http.client.HttpClient;

import java.time.Duration;
import java.util.concurrent.TimeUnit;

/**
 * WebClient Configuration for external service communication
 *
 * <p>Provides WebClient beans for:
 * <ul>
 *   <li>AI Service (FastAPI) - search, embedding, etc.</li>
 *   <li>Elasticsearch - health check</li>
 * </ul>
 */
@Configuration
public class WebClientConfig {

    @Value("${ai-service.url}")
    private String aiServiceUrl;

    @Value("${ai-service.timeout:60s}")
    private Duration aiServiceTimeout;

    @Value("${elasticsearch.url:http://localhost:9200}")
    private String elasticsearchUrl;

    @Value("${elasticsearch.timeout:10s}")
    private Duration elasticsearchTimeout;

    /**
     * WebClient for AI Service communication
     *
     * @return configured WebClient for AI Service
     */
    @Bean
    public WebClient aiServiceWebClient() {
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, (int) aiServiceTimeout.toMillis())
            .responseTimeout(aiServiceTimeout)
            .doOnConnected(conn -> conn
                .addHandlerLast(new ReadTimeoutHandler(aiServiceTimeout.toSeconds(), TimeUnit.SECONDS))
                .addHandlerLast(new WriteTimeoutHandler(aiServiceTimeout.toSeconds(), TimeUnit.SECONDS))
            );

        return WebClient.builder()
            .baseUrl(aiServiceUrl)
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
    }

    /**
     * WebClient for Elasticsearch health check
     *
     * @return configured WebClient for Elasticsearch
     */
    @Bean
    public WebClient elasticsearchWebClient() {
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, (int) elasticsearchTimeout.toMillis())
            .responseTimeout(elasticsearchTimeout)
            .doOnConnected(conn -> conn
                .addHandlerLast(new ReadTimeoutHandler(elasticsearchTimeout.toSeconds(), TimeUnit.SECONDS))
                .addHandlerLast(new WriteTimeoutHandler(elasticsearchTimeout.toSeconds(), TimeUnit.SECONDS))
            );

        return WebClient.builder()
            .baseUrl(elasticsearchUrl)
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
    }
}
