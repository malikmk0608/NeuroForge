-- Apply once to a new MySQL 8 database selected by the operator.
CREATE TABLE role_policy (
  role VARCHAR(32) PRIMARY KEY,
  version BIGINT NOT NULL DEFAULT 1 CHECK (version > 0)
) ENGINE=InnoDB;
CREATE TABLE permission (
  permission_code VARCHAR(64) PRIMARY KEY
) ENGINE=InnoDB;
CREATE TABLE role_permission (
  role VARCHAR(32) NOT NULL,
  permission_code VARCHAR(64) NOT NULL,
  PRIMARY KEY(role, permission_code),
  FOREIGN KEY(role) REFERENCES role_policy(role),
  FOREIGN KEY(permission_code) REFERENCES permission(permission_code)
) ENGINE=InnoDB;
CREATE TABLE employee (
  employee_code VARCHAR(16) PRIMARY KEY,
  name VARCHAR(120) NOT NULL,
  department VARCHAR(80) NOT NULL,
  role VARCHAR(32) NOT NULL,
  manager_code VARCHAR(16),
  active BOOLEAN NOT NULL DEFAULT TRUE,
  version BIGINT NOT NULL DEFAULT 1 CHECK (version > 0),
  FOREIGN KEY(role) REFERENCES role_policy(role),
  FOREIGN KEY(manager_code) REFERENCES employee(employee_code)
) ENGINE=InnoDB;
CREATE TABLE employee_permission (
  employee_code VARCHAR(16) NOT NULL,
  permission_code VARCHAR(64) NOT NULL,
  PRIMARY KEY(employee_code, permission_code),
  FOREIGN KEY(employee_code) REFERENCES employee(employee_code),
  FOREIGN KEY(permission_code) REFERENCES permission(permission_code)
) ENGINE=InnoDB;
CREATE TABLE app_user (
  username VARCHAR(80) PRIMARY KEY,
  employee_code VARCHAR(16) UNIQUE,
  authority ENUM('EMPLOYEE','APPROVER','HR') NOT NULL,
  password_hash VARCHAR(100),
  FOREIGN KEY(employee_code) REFERENCES employee(employee_code)
) ENGINE=InnoDB;
CREATE TABLE access_request (
  request_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  idempotency_key CHAR(36) NOT NULL,
  requester VARCHAR(80) NOT NULL,
  employee_code VARCHAR(16) NOT NULL,
  action ENUM('ROLE_CHANGE','OFFBOARD') NOT NULL,
  target_role VARCHAR(32),
  expected_employee_version BIGINT NOT NULL,
  expected_policy_version BIGINT,
  effective_date DATE NOT NULL,
  reviewed_snapshot JSON NOT NULL,
  status ENUM('PENDING_APPROVAL','APPROVED','REJECTED','APPLIED') NOT NULL DEFAULT 'PENDING_APPROVAL',
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  applied_at TIMESTAMP(6),
  UNIQUE(requester,idempotency_key),
  FOREIGN KEY(requester) REFERENCES app_user(username),
  FOREIGN KEY(employee_code) REFERENCES employee(employee_code),
  FOREIGN KEY(target_role) REFERENCES role_policy(role)
) ENGINE=InnoDB;
CREATE TABLE request_approval (
  request_id BIGINT NOT NULL,
  approver VARCHAR(80) NOT NULL,
  decision ENUM('APPROVE','REJECT') NOT NULL,
  decided_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY(request_id,approver),
  FOREIGN KEY(request_id) REFERENCES access_request(request_id),
  FOREIGN KEY(approver) REFERENCES app_user(username)
) ENGINE=InnoDB;
CREATE TABLE audit_log (
  audit_id BIGINT PRIMARY KEY AUTO_INCREMENT,
  request_id BIGINT,
  actor VARCHAR(80) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  details JSON NOT NULL,
  occurred_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  FOREIGN KEY(request_id) REFERENCES access_request(request_id),
  FOREIGN KEY(actor) REFERENCES app_user(username)
) ENGINE=InnoDB;
