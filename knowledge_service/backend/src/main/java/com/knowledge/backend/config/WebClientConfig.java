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
 * WebClient Configuration for AI Service communication
 */
@Configuration
public class WebClientConfig {

    @Value("${ai-service.url}")
    private String aiServiceUrl;

    @Value("${ai-service.timeout:60s}")
    private Duration timeout;

    @Bean
    public WebClient aiServiceWebClient() {
        HttpClient httpClient = HttpClient.create()
            .option(ChannelOption.CONNECT_TIMEOUT_MILLIS, (int) timeout.toMillis())
            .responseTimeout(timeout)
            .doOnConnected(conn -> conn
                .addHandlerLast(new ReadTimeoutHandler(timeout.toSeconds(), TimeUnit.SECONDS))
                .addHandlerLast(new WriteTimeoutHandler(timeout.toSeconds(), TimeUnit.SECONDS))
            );

        return WebClient.builder()
            .baseUrl(aiServiceUrl)
            .clientConnector(new ReactorClientHttpConnector(httpClient))
            .build();
    }
}
