package com.neuroforge.service;

import com.fasterxml.jackson.databind.*;
import java.time.*;
import java.util.*;
import org.springframework.http.HttpStatus;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

@Service
public class AccessWorkflow {
    private final JdbcTemplate db;
    private final ObjectMapper json;
    public AccessWorkflow(JdbcTemplate db, ObjectMapper json) { this.db=db; this.json=json; }

    private static void check(boolean ok, String message) {
        if (!ok) throw new ResponseStatusException(HttpStatus.CONFLICT, message);
    }
    private JsonNode parse(Object value) {
        try { return json.readTree(value.toString()); }
        catch (java.io.IOException e) { throw new IllegalStateException("Invalid stored request",e); }
    }
    private Map<String,Object> one(String sql, Object... args) {
        return db.queryForList(sql,args).stream().findFirst().orElseThrow(() ->
            new ResponseStatusException(HttpStatus.NOT_FOUND,"Record unavailable"));
    }
    private void audit(long id,String actor,String event) {
        db.update("INSERT INTO audit_log(request_id,actor,event_type,details) VALUES(?,?,?,JSON_OBJECT())",id,actor,event);
    }

    private static LocalDate today() { return LocalDate.now(ZoneId.of("Asia/Kolkata")); }
    private LocalDate date(JsonNode plan) {
        try { return LocalDate.parse(plan.path("effective_date").asText()); }
        catch (java.time.DateTimeException e) { throw new ResponseStatusException(HttpStatus.BAD_REQUEST,"Enter a valid effective date"); }
    }
    private void validate(JsonNode p) {
        String code=p.path("employee_code").asText(), manager=p.path("manager").asText();
        var employee=one("SELECT role,version,active FROM employee WHERE employee_code=? FOR UPDATE",code);
        check(Boolean.TRUE.equals(employee.get("active")) && employee.get("role").equals(p.path("current_role").asText())
            && ((Number)employee.get("version")).longValue()==p.path("expected_employee_version").asLong(),
            "Employee access changed. Generate a fresh plan.");
        check(!code.equals(manager) && !db.queryForList("SELECT employee_code FROM employee WHERE employee_code=? AND active AND role='MANAGER' FOR SHARE",manager).isEmpty(),
            "Choose an active reporting manager with the Manager role.");
        String justification=p.path("justification").asText("").trim();
        check(!justification.isEmpty() && justification.length()<=1000,"Provide a business justification of up to 1000 characters.");
        var current=db.queryForList("SELECT permission_code FROM employee_permission WHERE employee_code=? ORDER BY permission_code FOR SHARE",String.class,code);
        List<String> target;
        if ("ROLE_CHANGE".equals(p.path("action").asText())) {
            String role=p.path("target_role").asText();
            check("PERMANENT".equals(p.path("assignment_type").asText()),"Only permanent role changes can be submitted.");
            var policy=one("SELECT version FROM role_policy WHERE role=? FOR SHARE",role);
            check(((Number)policy.get("version")).longValue()==p.path("expected_policy_version").asLong(),"Role policy changed. Generate a fresh plan.");
            target=db.queryForList("SELECT permission_code FROM role_permission WHERE role=? ORDER BY permission_code FOR SHARE",String.class,role);
            check(!role.equals(employee.get("role")) || !target.equals(current),"This request makes no changes.");
        } else {
            check("OFFBOARD".equals(p.path("action").asText()) && p.path("target_role").isNull(),"Unsupported access change.");
            target=List.of();
        }
        var delta=Map.of("grant",target.stream().filter(v -> !current.contains(v)).toList(),
            "revoke",current.stream().filter(v -> !target.contains(v)).toList(),
            "retain",current.stream().filter(target::contains).toList());
        check(json.valueToTree(delta).equals(p.path("proposed_permissions")),"Permissions changed. Review a fresh draft.");
    }
    @Transactional(isolation=org.springframework.transaction.annotation.Isolation.READ_COMMITTED)
    public Map<String,Object> create(String actor, UUID key, JsonNode plan) {
        one("SELECT username FROM app_user WHERE username=? AND authority='HR'",actor);
        var prior=db.queryForList("SELECT request_id,reviewed_snapshot FROM access_request WHERE requester=? AND idempotency_key=?",actor,key.toString());
        long id;
        if (!prior.isEmpty()) {
            check(parse(prior.getFirst().get("reviewed_snapshot")).equals(plan),"Submission key already used for a different plan.");
            id=((Number)prior.getFirst().get("request_id")).longValue();
        } else {
            validate(plan);
            LocalDate effective=date(plan);
            check(!effective.isBefore(today()),"Select today or a future effective date.");
            db.update("""
                INSERT INTO access_request(requester,idempotency_key,employee_code,action,target_role,expected_employee_version,
                expected_policy_version,effective_date,reviewed_snapshot) VALUES(?,?,?,?,?,?,?,?,?)
                ON DUPLICATE KEY UPDATE request_id=LAST_INSERT_ID(request_id)
                """, actor,key.toString(),plan.path("employee_code").asText(),plan.path("action").asText(),
                plan.path("target_role").asText(null),plan.path("expected_employee_version").asLong(),
                plan.hasNonNull("expected_policy_version")?plan.get("expected_policy_version").longValue():null,effective,plan.toString());
            id=db.queryForObject("SELECT LAST_INSERT_ID()",Long.class);
            check(parse(one("SELECT reviewed_snapshot FROM access_request WHERE request_id=? FOR UPDATE",id).get("reviewed_snapshot")).equals(plan),"Submission key already used for a different plan.");
            if (db.queryForList("SELECT audit_id FROM audit_log WHERE request_id=? AND event_type='SUBMITTED'",id).isEmpty()) audit(id,actor,"SUBMITTED");
        }
        // Receipt describes the original creation, including on an idempotent retry.
        return Map.of("request_id",Long.toString(id),"employee_code",plan.path("employee_code").asText(),
            "action",plan.path("action").asText(),"status","PENDING_APPROVAL","approved_count",0,"required_approvals",2);
    }

    private static final String SUMMARY="""
        SELECT r.request_id,r.requester,r.employee_code,e.name,r.action,r.target_role,r.status,r.effective_date,
        (SELECT COUNT(*) FROM request_approval a WHERE a.request_id=r.request_id AND a.decision='APPROVE') AS approved_count
        FROM access_request r JOIN employee e ON e.employee_code=r.employee_code
        """;
    public List<Map<String,Object>> list() { return db.queryForList(SUMMARY+" ORDER BY r.request_id DESC"); }
    public Map<String,Object> detail(long id) {
        var row=one(SUMMARY+" WHERE r.request_id=?",id);
        row.put("plan",parse(one("SELECT reviewed_snapshot FROM access_request WHERE request_id=?",id).get("reviewed_snapshot")));
        row.put("events",db.queryForList("SELECT actor,event_type,occurred_at FROM audit_log WHERE request_id=? ORDER BY audit_id",id));
        return row;
    }
    @Transactional
    public void decide(long id,String actor,String decision) {
        var row=one("SELECT status,requester FROM access_request WHERE request_id=? FOR UPDATE",id);
        check("PENDING_APPROVAL".equals(row.get("status")),"This request is no longer pending.");
        check(!actor.equals(row.get("requester")),"Requesters cannot approve their own change.");
        check(List.of("APPROVE","REJECT").contains(decision),"Choose approve or reject.");
        check(db.queryForList("SELECT approver FROM request_approval WHERE request_id=? AND approver=?",id,actor).isEmpty(),
            "You have already decided on this request.");
        db.update("INSERT INTO request_approval(request_id,approver,decision) VALUES(?,?,?)",id,actor,decision);
        if (decision.equals("REJECT")) db.update("UPDATE access_request SET status='REJECTED' WHERE request_id=?",id);
        else if (db.queryForObject("SELECT COUNT(*) FROM request_approval WHERE request_id=? AND decision='APPROVE'",Integer.class,id)==2)
            db.update("UPDATE access_request SET status='APPROVED' WHERE request_id=?",id);
        audit(id,actor,decision);
    }
    @Transactional
    public void apply(long id,String actor) {
        var row=one("SELECT status,reviewed_snapshot FROM access_request WHERE request_id=? FOR UPDATE",id);
        if ("APPLIED".equals(row.get("status"))) return;
        check("APPROVED".equals(row.get("status")),"Two distinct approvals are required.");
        var p=parse(row.get("reviewed_snapshot"));
        check(!date(p).isAfter(today()),"The effective date has not arrived.");
        validate(p);
        String code=p.get("employee_code").asText();
        for (var permission:p.at("/proposed_permissions/revoke"))
            db.update("DELETE FROM employee_permission WHERE employee_code=? AND permission_code=?",code,permission.asText());
        for (var permission:p.at("/proposed_permissions/grant"))
            db.update("INSERT INTO employee_permission(employee_code,permission_code) VALUES(?,?)",code,permission.asText());
        if ("OFFBOARD".equals(p.get("action").asText()))
            db.update("UPDATE employee SET active=false,version=version+1 WHERE employee_code=?",code);
        else db.update("UPDATE employee SET role=?,manager_code=?,version=version+1 WHERE employee_code=?",
            p.get("target_role").asText(),p.get("manager").asText(),code);
        db.update("UPDATE access_request SET status='APPLIED',applied_at=CURRENT_TIMESTAMP(6) WHERE request_id=?",id);
        audit(id,actor,"APPLIED");
    }

    public Map<String,Object> profile(String actor) {
        var row=one("""
            SELECT e.employee_code,e.name,e.role,e.department FROM employee e JOIN app_user u ON u.employee_code=e.employee_code
            WHERE u.username=? AND e.active
            """,actor);
        row.put("permissions",db.queryForList("SELECT permission_code FROM employee_permission WHERE employee_code=? ORDER BY permission_code",String.class,row.get("employee_code")));
        row.put("requests",db.queryForList(SUMMARY+" WHERE r.employee_code=? ORDER BY r.request_id DESC",row.get("employee_code")));
        return row;
    }
}

