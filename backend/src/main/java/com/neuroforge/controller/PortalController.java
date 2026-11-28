package com.neuroforge.controller;

import java.security.Principal;
import com.neuroforge.repository.DirectoryRepository;
import java.util.*;
import com.fasterxml.jackson.databind.JsonNode;
import com.neuroforge.service.*;
import org.springframework.http.*;
import org.springframework.security.core.Authentication;
import org.springframework.security.web.csrf.CsrfToken;
import org.springframework.web.bind.annotation.*;

@RestController
public class PortalController {
    private final DirectoryRepository directory;
    private final PlannerBridge planner;
    private final AccessWorkflow workflow;
    public PortalController(PlannerBridge planner, AccessWorkflow workflow, DirectoryRepository directory) { this.directory=directory; this.planner=planner; this.workflow=workflow; }

    @GetMapping("/portal/session")
    Map<String,Object> session(Authentication auth, CsrfToken csrf) {
        var data=new HashMap<String,Object>();
        data.put("csrf",csrf.getToken());
        if (auth!=null) {
            data.put("username",auth.getName());
            data.put("role",auth.getAuthorities().iterator().next().getAuthority().substring(5));
        }
        return data;
    }
    @GetMapping("/portal/planner/form-options")
    ResponseEntity<String> options(Principal who) { return planner.forward(who.getName(),"form-options",null,null); }
    @PostMapping("/portal/planner/{route:role-change|offboard|plan|submit}")
    ResponseEntity<String> plan(Principal who,@PathVariable String route,@RequestBody String body,
            @RequestHeader(name="Idempotency-Key",required=false) UUID key) {
        return planner.forward(who.getName(),route,body,key==null?null:key.toString());
    }
    @PostMapping("/api/access-requests") @ResponseStatus(HttpStatus.CREATED)
    Map<String,Object> create(Principal who,@RequestHeader("Idempotency-Key") UUID key,@RequestBody JsonNode plan) {
        return workflow.create(who.getName(),key,plan);
    }
    @GetMapping("/portal/directory")
    List<DirectoryRepository.Employee> directory() { return directory.employees(null); }
    @GetMapping("/portal/requests")
    List<Map<String,Object>> requests() { return workflow.list(); }
    @GetMapping("/portal/requests/{id}")
    Map<String,Object> request(@PathVariable long id) { return workflow.detail(id); }
    record Decision(String decision) {}
    @PostMapping("/portal/requests/{id}/decisions") @ResponseStatus(HttpStatus.NO_CONTENT)
    void decide(@PathVariable long id,Principal who,@RequestBody Decision choice) {
        workflow.decide(id,who.getName(),Objects.toString(choice.decision(),""));
    }
    @PostMapping("/portal/requests/{id}/apply") @ResponseStatus(HttpStatus.NO_CONTENT)
    void apply(@PathVariable long id,Principal who) { workflow.apply(id,who.getName()); }
    @GetMapping("/portal/profile")
    Map<String,Object> profile(Principal who) { return workflow.profile(who.getName()); }

    @ExceptionHandler(org.springframework.web.server.ResponseStatusException.class)
    ResponseEntity<?> error(org.springframework.web.server.ResponseStatusException e) {
        return ResponseEntity.status(e.getStatusCode()).body(Map.of("detail",Objects.toString(e.getReason(),"Request failed")));
    }
}

