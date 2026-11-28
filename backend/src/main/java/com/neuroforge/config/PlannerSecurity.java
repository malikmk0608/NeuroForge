package com.neuroforge.config;

import java.util.List;
import com.neuroforge.service.PlannerBridge;
import org.springframework.context.annotation.*;
import org.springframework.core.annotation.Order;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.oauth2.core.*;
import org.springframework.security.oauth2.server.resource.introspection.BadOpaqueTokenException;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class PlannerSecurity {
    @Bean @Order(2)
    SecurityFilterChain delegated(HttpSecurity http, PlannerBridge bridge) throws Exception {
        return http.securityMatcher(r -> r.getRequestURI().startsWith("/api/") &&
                String.valueOf(r.getHeader("Authorization")).startsWith("Bearer nf_"))
            .sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(a -> a.requestMatchers(HttpMethod.GET, "/api/employees","/api/employees/*","/api/roles","/api/roles/*/permissions").authenticated()
                .requestMatchers(HttpMethod.POST,"/api/access-requests").hasAuthority("SUBMIT_REVIEWED_PLAN").anyRequest().denyAll())
            .oauth2ResourceServer(o -> o.opaqueToken(t -> t.introspector(token -> {
                var actor = bridge.caller(token);
                if (actor == null) throw new BadOpaqueTokenException("Expired planner call");
                return new DefaultOAuth2AuthenticatedPrincipal(actor.username(), java.util.Map.of("sub",actor.username()),
                    List.of(new SimpleGrantedAuthority(actor.canSubmit() ? "SUBMIT_REVIEWED_PLAN" : "READ_DIRECTORY")));
            }))).build();
    }
}

