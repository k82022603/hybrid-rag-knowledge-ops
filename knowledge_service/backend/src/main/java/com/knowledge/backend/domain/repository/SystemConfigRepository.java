package com.knowledge.backend.domain.repository;

import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.SystemConfig;

import reactor.core.publisher.Flux;

/**
 * System Config Repository
 *
 * <p>R2DBC repository for SystemConfig entity (system_config table).
 */
@Repository
public interface SystemConfigRepository extends R2dbcRepository<SystemConfig, String> {

    /**
     * Find all system configuration entries
     *
     * @return Flux of all config entries
     */
    Flux<SystemConfig> findAll();
}
