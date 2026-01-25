package com.knowledge.backend.exception;

import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.ResponseStatus;

/**
 * User Not Found Exception
 *
 * <p>Thrown when user is not found in the system
 */
@ResponseStatus(HttpStatus.NOT_FOUND)
public class UserNotFoundException extends RuntimeException {

    public UserNotFoundException(String message) {
        super(message);
    }

    public static UserNotFoundException byId(Long userId) {
        return new UserNotFoundException("User not found with id: " + userId);
    }
}
