package com.neuroforge.config;

import org.springframework.context.annotation.*;
import org.springframework.core.annotation.Order;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.core.userdetails.*;
import org.springframework.security.crypto.password.Pbkdf2PasswordEncoder;
import org.springframework.security.authentication.dao.DaoAuthenticationProvider;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.csrf.HttpSessionCsrfTokenRepository;

@Configuration
public class PortalSecurity {
    @Bean @Order(1)
    SecurityFilterChain portal(HttpSecurity http, JdbcTemplate db) throws Exception {
        UserDetailsService users = name -> db.query("""
            SELECT u.username,u.password_hash,u.authority FROM app_user u
            LEFT JOIN employee e ON e.employee_code=u.employee_code
            WHERE u.username=? AND u.password_hash IS NOT NULL AND (u.employee_code IS NULL OR e.active)
            """, (rs,i) -> User.withUsername(rs.getString(1)).password(rs.getString(2))
                .roles(rs.getString(3)).build(), name).stream().findFirst()
                .orElseThrow(() -> new UsernameNotFoundException("Account unavailable"));
        var provider = new DaoAuthenticationProvider(users);
        provider.setPasswordEncoder(Pbkdf2PasswordEncoder.defaultsForSpringSecurity_v5_8());
        return http.securityMatcher("/portal/**").authenticationProvider(provider)
            .csrf(c -> c.csrfTokenRepository(new HttpSessionCsrfTokenRepository()))
            .authorizeHttpRequests(a -> a.requestMatchers("/portal/session","/portal/login").permitAll()
                .requestMatchers("/portal/directory","/portal/planner/**","/portal/requests/*/apply").hasRole("HR")
                .requestMatchers("/portal/requests/*/decisions").hasRole("APPROVER")
                .requestMatchers("/portal/profile").hasRole("EMPLOYEE")
                .requestMatchers("/portal/requests","/portal/requests/*").hasAnyRole("HR","APPROVER")
                .anyRequest().denyAll())
            .requestCache(c -> c.disable())
            .exceptionHandling(e -> e.authenticationEntryPoint((q,r,x) -> r.setStatus(401)))
            .formLogin(f -> f.loginProcessingUrl("/portal/login")
                .successHandler((q,r,a) -> r.setStatus(204))
                .failureHandler((q,r,e) -> r.setStatus(401)))
            .logout(l -> l.logoutUrl("/portal/logout").logoutSuccessHandler((q,r,a) -> r.setStatus(204)))
            .build();
    }
}

