-- Development fixtures. Apply once, after schema.sql.
START TRANSACTION;
INSERT INTO role_policy(role) VALUES ('ENGINEER'),('MANAGER'),('HR'),('FINANCE');
INSERT INTO permission VALUES ('GIT_READ'),('GIT_WRITE'),('JIRA_EDIT'),('VPN_ACCESS'),
 ('TEAM_DIRECTORY'),('REPORT_VIEW'),('EMPLOYEE_DIRECTORY'),('HRIS_READ'),('HRIS_EDIT'),('ERP_READ'),('EXPENSE_APPROVE');
INSERT INTO role_permission VALUES
 ('ENGINEER','GIT_READ'),('ENGINEER','GIT_WRITE'),('ENGINEER','JIRA_EDIT'),('ENGINEER','VPN_ACCESS'),
 ('MANAGER','TEAM_DIRECTORY'),('MANAGER','REPORT_VIEW'),('MANAGER','JIRA_EDIT'),('MANAGER','VPN_ACCESS'),
 ('HR','EMPLOYEE_DIRECTORY'),('HR','HRIS_READ'),('HR','HRIS_EDIT'),
 ('FINANCE','ERP_READ'),('FINANCE','EXPENSE_APPROVE'),('FINANCE','REPORT_VIEW');
INSERT INTO employee(employee_code,name,department,role,manager_code) VALUES
 ('EF-1002','Priya Patel','Engineering','MANAGER',NULL),
 ('EF-1001','Aarav Sharma','Engineering','ENGINEER','EF-1002'),
 ('EF-1003','Rohan Mehta','HR','HR',NULL),
 ('EF-1004','Sneha Reddy','Finance','FINANCE',NULL),
 ('EF-1005','Ananya Rao','Engineering','ENGINEER','EF-1002'),
 ('EF-1006','Kabir Shah','Engineering','ENGINEER','EF-1002'),
 ('EF-1007','Diya Menon','Engineering','ENGINEER','EF-1002');
INSERT INTO employee_permission(employee_code,permission_code)
 SELECT e.employee_code,r.permission_code FROM employee e JOIN role_permission r ON r.role=e.role;
INSERT INTO app_user(username,employee_code,authority)
 SELECT employee_code,employee_code,'EMPLOYEE' FROM employee;
INSERT INTO app_user(username,authority) VALUES ('hr.operations','HR'),('department.approver','APPROVER'),('security.approver','APPROVER');
COMMIT;
