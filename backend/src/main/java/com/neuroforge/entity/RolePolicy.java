package com.neuroforge.entity;

import jakarta.persistence.*;
import java.util.Set;
import java.util.HashSet;
import com.neuroforge.repository.DirectoryRepository;

@Entity
@Table(name = "role_policy")
public class RolePolicy {
    @Id
    @Column(name = "role")
    private String code;
    private long version;

    @ElementCollection
    @CollectionTable(name = "role_permission", joinColumns = @JoinColumn(name = "role"))
    @Column(name = "permission_code")
    private Set<String> permissions = new HashSet<>();

    public DirectoryRepository.Policy view() {
        return new DirectoryRepository.Policy(code, permissions.stream().sorted().toList(), version);
    }
}
