package com.neuroforge.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.Customizer;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.web.SecurityFilterChain;

@Configuration
public class SecurityConfig {
    @Bean
    SecurityFilterChain api(HttpSecurity http, @org.springframework.beans.factory.annotation.Value("${spring.security.oauth2.resourceserver.jwt.issuer-uri:}") String issuer) throws Exception {
        var chain = http.sessionManagement(s -> s.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
            .authorizeHttpRequests(a -> a
                .requestMatchers(HttpMethod.GET, "/", "/index.html", "/assets/**").permitAll()
                .requestMatchers(HttpMethod.GET, "/api/employees", "/api/employees/*", "/api/roles", "/api/roles/*/permissions")
                .hasAuthority("SCOPE_iam.plan")
                .anyRequest().denyAll());
        if (!issuer.isBlank()) chain.oauth2ResourceServer(s -> s.jwt(Customizer.withDefaults()));
        return chain.build();
    }
}
