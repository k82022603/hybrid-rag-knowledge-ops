package com.knowledge.backend.config;

import java.time.LocalDateTime;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.context.annotation.Profile;
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;
import org.springframework.stereotype.Component;

import com.knowledge.backend.domain.entity.User;
import com.knowledge.backend.domain.repository.UserRepository;

import lombok.RequiredArgsConstructor;

/**
 * Data Initializer for Test/Development Accounts
 *
 * <p>Seeds initial user accounts on application startup.
 * <p>SECURITY: Only active in 'local' and 'test' profiles (NOT docker/production).
 *
 * <p>Credentials are loaded from environment variables:
 * <ul>
 *   <li>INIT_TEST_USER_PASSWORD - password for test user (default in test profile only)</li>
 *   <li>INIT_ADMIN_PASSWORD - password for admin user (default in test profile only)</li>
 * </ul>
 *
 * <p>In local profile, if passwords are not set via env vars, initialization is skipped
 * with a warning log message.
 */
@Component
@Profile({"local", "test"})
@RequiredArgsConstructor
public class DataInitializer implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DataInitializer.class);

    private final UserRepository userRepository;
    private final BCryptPasswordEncoder passwordEncoder = new BCryptPasswordEncoder();

    @Value("${init.test-user.password:#{null}}")
    private String testUserPassword;

    @Value("${init.admin.password:#{null}}")
    private String adminPassword;

    @Override
    public void run(ApplicationArguments args) {
        log.info("Starting test data initialization...");

        if (testUserPassword == null || testUserPassword.isBlank()) {
            log.warn("INIT_TEST_USER_PASSWORD not set. Skipping test user creation. "
                + "Set environment variable to create test user.");
        }
        if (adminPassword == null || adminPassword.isBlank()) {
            log.warn("INIT_ADMIN_PASSWORD not set. Skipping admin user creation. "
                + "Set environment variable to create admin user.");
        }

        initializeTestUser()
            .then(initializeAdminUser())
            .doOnSuccess(v -> log.info("Test data initialization completed successfully"))
            .doOnError(e -> log.error("Test data initialization failed", e))
            .subscribe();
    }

    /**
     * Initialize test user account (USER role)
     *
     * <p>Only creates the user if INIT_TEST_USER_PASSWORD environment variable is set.
     */
    private reactor.core.publisher.Mono<Void> initializeTestUser() {
        if (testUserPassword == null || testUserPassword.isBlank()) {
            return reactor.core.publisher.Mono.empty();
        }

        String email = "test@example.com";

        return userRepository.existsByEmail(email)
            .flatMap(exists -> {
                if (exists) {
                    log.info("Test user already exists: {}", email);
                    return reactor.core.publisher.Mono.empty();
                }

                User testUser = User.builder()
                    .email(email)
                    .username("testuser")
                    .passwordHash(passwordEncoder.encode(testUserPassword))
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
     *
     * <p>Only creates the user if INIT_ADMIN_PASSWORD environment variable is set.
     */
    private reactor.core.publisher.Mono<Void> initializeAdminUser() {
        if (adminPassword == null || adminPassword.isBlank()) {
            return reactor.core.publisher.Mono.empty();
        }

        String email = "admin@example.com";

        return userRepository.existsByEmail(email)
            .flatMap(exists -> {
                if (exists) {
                    log.info("Admin user already exists: {}", email);
                    return reactor.core.publisher.Mono.empty();
                }

                User adminUser = User.builder()
                    .email(email)
                    .username("adminuser")
                    .passwordHash(passwordEncoder.encode(adminPassword))
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
