package com.knowledge.backend.domain.repository;

import java.util.UUID;

import org.springframework.data.r2dbc.repository.R2dbcRepository;
import org.springframework.stereotype.Repository;

import com.knowledge.backend.domain.entity.Project;

import reactor.core.publisher.Flux;
import reactor.core.publisher.Mono;

/**
 * Project Repository
 *
 * <p>R2DBC repository for Project entity (projects table).
 */
@Repository
public interface ProjectRepository extends R2dbcRepository<Project, UUID> {

    /**
     * Find project by code
     *
     * @param code the project code
     * @return Mono of project
     */
    Mono<Project> findByCode(String code);

    /**
     * Find projects by status
     *
     * @param status the project status
     * @return Flux of projects
     */
    Flux<Project> findByStatus(String status);
}
