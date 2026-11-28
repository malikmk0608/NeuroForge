package com.neuroforge.controller;

import java.util.List;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.neuroforge.repository.DirectoryRepository;
import com.neuroforge.repository.DirectoryRepository.Employee;
import com.neuroforge.repository.DirectoryRepository.Policy;

@RestController
@RequestMapping("/api")
public class DirectoryController {
    private final DirectoryRepository directory;

    public DirectoryController(DirectoryRepository directory) {
        this.directory = directory;
    }

    @GetMapping("/employees")
    public List<Employee> employees() { return directory.employees(null); }

    @GetMapping("/employees/{code}")
    public ResponseEntity<Employee> employee(@PathVariable String code) {
        return ResponseEntity.of(directory.employees(code).stream().findFirst());
    }

    @GetMapping("/roles")
    public List<Policy> roles() { return directory.policies(null); }

    @GetMapping("/roles/{role}/permissions")
    public ResponseEntity<Policy> policy(@PathVariable String role) {
        return ResponseEntity.of(directory.policies(role).stream().findFirst());
    }
}
