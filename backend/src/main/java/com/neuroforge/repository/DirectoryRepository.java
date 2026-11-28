package com.neuroforge.repository;

import java.util.List;
import jakarta.persistence.EntityManager;
import org.springframework.stereotype.Repository;
import org.springframework.transaction.annotation.Transactional;

@Repository
@Transactional(readOnly = true)
public class DirectoryRepository {
    public record Employee(String employee_code, String name, String department, String role,
                           List<String> permissions, long version) {}
    public record Policy(String role, List<String> permissions, long version) {}

    private final EntityManager db;

    public DirectoryRepository(EntityManager db) {
        this.db = db;
    }

    public List<Employee> employees(String code) {
        String hql = "select distinct e from Employee e left join fetch e.permissions where e.active = true";
        if (code != null) hql += " and e.code = :code";
        var query = db.createQuery(hql + " order by e.code", com.neuroforge.entity.Employee.class);
        if (code != null) query.setParameter("code", code);
        return query.getResultList().stream().map(com.neuroforge.entity.Employee::view).toList();
    }

    public List<Policy> policies(String role) {
        String hql = "select distinct r from RolePolicy r left join fetch r.permissions";
        if (role != null) hql += " where r.code = :role";
        var query = db.createQuery(hql + " order by r.code", com.neuroforge.entity.RolePolicy.class);
        if (role != null) query.setParameter("role", role);
        return query.getResultList().stream().map(com.neuroforge.entity.RolePolicy::view).toList();
    }
}
