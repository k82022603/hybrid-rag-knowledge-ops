package com.knowledge.backend.config;

import java.time.LocalDateTime;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

import com.knowledge.backend.domain.entity.User;
import com.knowledge.backend.domain.repository.UserRepository;

import lombok.RequiredArgsConstructor;

/**
 * Data Initializer for Test Accounts
 *
 * <p>Seeds test user accounts on application startup for E2E testing.
 * <p>Only active in 'local', 'test', and 'docker' profiles.
 *
 * <p>Test accounts:
 * <ul>
 *   <li>test@example.com / password123 - USER role</li>
 *   <li>admin@example.com / admin123! - ADMIN role</li>
 * </ul>
 */
@Component
@Profile({"local", "test", "docker"})
@RequiredArgsConstructor
public class DataInitializer implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Override
    public void run(ApplicationArguments args) {
        log.info("Starting test data initialization...");

        initializeTestUser()
            .then(initializeAdminUser())
            .doOnSuccess(v -> log.info("Test data initialization completed successfully"))
            .doOnError(e -> log.error("Test data initialization failed", e))
            .subscribe();
    }

    /**
     * Initialize test user account (USER role)
     */
    private reactor.core.publisher.Mono<Void> initializeTestUser() {
        String email = "test@example.com";
        String rawPassword = "password123";

        return userRepository.existsByEmail(email)
            .flatMap(exists -> {
                if (exists) {
                    log.info("Test user already exists: {}", email);
                    return reactor.core.publisher.Mono.empty();
                }

                User testUser = User.builder()
                    .email(email)
                    .username("testuser")
                    .passwordHash(passwordEncoder.encode(rawPassword))
                    .firstName("Test")
                    .lastName("User")
                    .roles("USER")
                    .isActive(true)
                    .isLocked(false)
                    .failedLoginAttempts(0)
                    .createdAt(LocalDateTime.now())
                    .updatedAt(LocalDateTime.now())
                    .build();

                return userRepository.save(testUser)
                    .doOnSuccess(user -> log.info("Created test user: {} (id={})", email, user.getId()))
                    .then();
            });
    }

    /**
     * Initialize admin user account (ADMIN role)
     */
    private reactor.core.publisher.Mono<Void> initializeAdminUser() {
        String email = "admin@example.com";
        String rawPassword = "admin123!";

        return userRepository.existsByEmail(email)
            .flatMap(exists -> {
                if (exists) {
                    log.info("Admin user already exists: {}", email);
                    return reactor.core.publisher.Mono.empty();
                }

                User adminUser = User.builder()
                    .email(email)
                    .username("adminuser")
                    .passwordHash(passwordEncoder.encode(rawPassword))
                    .firstName("Admin")
                    .lastName("User")
                    .roles("ADMIN,USER")
                    .isActive(true)
                    .isLocked(false)
                    .failedLoginAttempts(0)
                    .createdAt(LocalDateTime.now())
                    .updatedAt(LocalDateTime.now())
                    .build();

                return userRepository.save(adminUser)
                    .doOnSuccess(user -> log.info("Created admin user: {} (id={})", email, user.getId()))
                    .then();
            });
    }
}
