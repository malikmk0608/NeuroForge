package com.neuroforge.entity;

import jakarta.persistence.*;
import java.util.Set;
import java.util.HashSet;
import com.neuroforge.repository.DirectoryRepository;

@Entity
@Table(name = "employee")
public class Employee {
    @Id
    @Column(name = "employee_code")
    private String code;
    private String name;
    private String department;
    private String role;
    private boolean active;
    private long version;

    @ElementCollection
    @CollectionTable(name = "employee_permission", joinColumns = @JoinColumn(name = "employee_code"))
    @Column(name = "permission_code")
    private Set<String> permissions = new HashSet<>();

    public DirectoryRepository.Employee view() {
        return new DirectoryRepository.Employee(code, name, department, role, permissions.stream().sorted().toList(), version);
    }
}
