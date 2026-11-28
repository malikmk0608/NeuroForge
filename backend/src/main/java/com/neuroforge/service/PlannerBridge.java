package com.neuroforge.service;

import java.net.URI;
import java.net.http.*;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.ResponseEntity;
import org.springframework.stereotype.Service;

@Service
public class PlannerBridge {
    public record Caller(String username, boolean canSubmit) {}
    private final Map<String,Caller> callers = new ConcurrentHashMap<>();
    private final HttpClient client = HttpClient.newBuilder().connectTimeout(Duration.ofSeconds(3)).build();
    private final String base;
    public PlannerBridge(@Value("${portal.planner-url:http://127.0.0.1:8002}") String base) { this.base=base; }
    public Caller caller(String token) { return callers.get(token); }

    public ResponseEntity<String> forward(String actor, String route, String body, String key) {
        String token = "nf_" + UUID.randomUUID();
        callers.put(token, new Caller(actor, route.equals("submit")));
        try {
            var request = HttpRequest.newBuilder(URI.create(base + "/agent/" + route))
                .header("Authorization", "Bearer " + token).timeout(Duration.ofSeconds(40));
            if (key != null) request.header("Idempotency-Key", key);
            if (body != null) request.header("Content-Type","application/json").POST(HttpRequest.BodyPublishers.ofString(body));
            var response = client.send(request.build(), HttpResponse.BodyHandlers.ofString());
            return ResponseEntity.status(response.statusCode()).header("Content-Type","application/json").body(response.body());
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
            throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE,"Planner interrupted");
        } catch (java.io.IOException e) {
            throw new org.springframework.web.server.ResponseStatusException(org.springframework.http.HttpStatus.SERVICE_UNAVAILABLE,"Start the HTTP-mode planner on port 8002");
        } finally { callers.remove(token); }
    }
}

