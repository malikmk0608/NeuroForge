const byId = (id) => document.getElementById(id);
const form = byId('request-form');
let employees = [];
let revision = 0;
let modelConfigured = false;
let busy = false;
let backendMode = 'mock';
let autoTitle = true;
let autoBusinessUnit = true;

function setBusy(value) {
  busy = value;
  byId('generate').disabled = value || !employees.length;
  byId('interpret-description').disabled = value || !modelConfigured || !employees.length;
  document.querySelector('.review').setAttribute('aria-busy', String(value));
}

function responseError(data) {
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((item) => `${item.loc.slice(1).join('.')}: ${item.msg}`).join(' ');
  return 'The request could not be processed. Please try again.';
}

function option(value, label) {
  const element = document.createElement('option');
  element.value = value;
  element.textContent = label;
  return element;
}

function showError(message) {
  byId('error').textContent = message;
  byId('error').hidden = !message;
}

function clearPreview() {
  revision += 1;
  byId('plan-result').hidden = true;
  byId('empty-state').hidden = false;
  byId('plan-status').textContent = 'Awaiting details';
  showError('');
}

function updateEmployee() {
  const employee = employees.find((item) => item.employee_code === byId('employee').value);
  byId('employee-context').textContent = employee
    ? `Current employee record for ${employee.name}.`
    : 'Select an employee to see their current role.';
  byId('current-role').value = employee?.role || '';
  byId('current-department').value = employee?.department || '';
  const previousManager = byId('manager').value;
  byId('manager').replaceChildren(option('', 'Select a manager'));
  employees.filter((item) => item.employee_code !== byId('employee').value).forEach((item) => {
    byId('manager').append(option(item.employee_code, `${item.name} · ${item.employee_code}`));
  });
  if (previousManager !== byId('employee').value) byId('manager').value = previousManager;
  updateContextSuggestions();
}

function updateContextSuggestions() {
  const employee = employees.find((item) => item.employee_code === byId('employee').value);
  if (autoTitle) {
    const action = byId('request-type').value === 'OFFBOARD' ? 'offboarding' : `role change to ${byId('target-role').value || 'a new role'}`;
    byId('request-title').value = employee ? `${employee.name} - ${action}` : 'Employee access change';
  }
  if (autoBusinessUnit) byId('business-unit').value = employee?.department || '';
}

function readRequestContext() {
  return {
    request_title: byId('request-title').value.trim(),
    priority: byId('priority').value,
    requester_reference: byId('requester-reference').value.trim() || null,
    business_unit: byId('business-unit').value.trim() || null,
  };
}

function demoEffectiveDate() {
  const parts = Object.fromEntries(new Intl.DateTimeFormat('en-CA', {
    timeZone: 'Asia/Kolkata', year: 'numeric', month: '2-digit', day: '2-digit',
  }).formatToParts(new Date()).map((part) => [part.type, part.value]));
  const day = new Date(Date.UTC(Number(parts.year), Number(parts.month) - 1, Number(parts.day) + 1));
  while (day.getUTCDay() === 0 || day.getUTCDay() === 6) day.setUTCDate(day.getUTCDate() + 1);
  return day.toISOString().slice(0, 10);
}

function prefillForm() {
  if (busy || backendMode !== 'mock') return;
  const offboarding = byId('request-type').value === 'OFFBOARD';
  const code = offboarding ? 'EF-1004' : 'EF-1001';
  if (!employees.some((employee) => employee.employee_code === code)) return;
  autoTitle = true;
  autoBusinessUnit = true;
  byId('employee').value = code;
  byId('target-role').value = offboarding ? '' : 'MANAGER';
  updateEmployee();
  byId('manager').value = 'EF-1002';
  byId('effective-date').value = demoEffectiveDate();
  byId('assignment-type').value = offboarding ? '' : 'PERMANENT';
  byId('temporary-note').hidden = true;
  byId('justification').value = offboarding
    ? 'Employee departure following completion of the handover. Revoke all existing access on the effective date.'
    : 'Taking responsibility for the engineering team and its delivery reporting.';
  byId('requester-reference').value = 'Rohan Mehta - HR Operations (demo)';
  byId('priority').value = 'NORMAL';
  byId('ai-description').value = '';
  byId('ai-feedback').hidden = true;
  updateRequestType();
}

function updateRequestType() {
  const offboarding = byId('request-type').value === 'OFFBOARD';
  byId('target-role-field').hidden = offboarding;
  byId('target-role').required = !offboarding;
  byId('assignment-field').hidden = offboarding;
  byId('assignment-type').required = !offboarding;
  byId('offboard-note').hidden = !offboarding;
  byId('request-tag').textContent = offboarding ? 'Offboarding' : 'Role change';
  updateContextSuggestions();
  clearPreview();
}

function renderPlan(data) {
  if (!data.plan) {
    const questions = data.interpretation?.clarification_questions || [];
    throw new Error([data.message, ...questions].join(' '));
  }
  const plan = data.plan;
  byId('empty-state').hidden = true;
  byId('plan-result').hidden = false;
  byId('plan-status').textContent = plan.has_changes ? 'Draft' : 'No changes';
  byId('plan-summary').textContent = plan.action === 'OFFBOARD'
    ? `${data.current_employee.name}: offboarding · Revoke all current access`
    : `${data.current_employee.name}: ${plan.current_role} → ${plan.target_role}`;
  const context = plan.request_context;
  byId('plan-context').textContent = `${context.request_title} · Priority: ${context.priority}`
    + (context.business_unit ? ` · ${context.business_unit}` : '')
    + (context.requester_reference ? ` · Requester reference: ${context.requester_reference}` : '');
  byId('permission-groups').replaceChildren();
  for (const [key, label] of [['grant', 'Grant'], ['revoke', 'Revoke'], ['retain', 'Retain']]) {
    const section = document.createElement('div');
    section.className = `permission-group ${key}`;
    const heading = document.createElement('div');
    heading.className = 'permission-heading';
    heading.textContent = `${label} (${plan.permissions[key].length})`;
    const list = document.createElement('div');
    list.className = 'permission-list';
    if (!plan.permissions[key].length) {
      const empty = document.createElement('span');
      empty.className = 'none';
      empty.textContent = 'None';
      list.append(empty);
    }
    plan.permissions[key].forEach((permission) => {
      const badge = document.createElement('span');
      badge.className = 'permission';
      badge.textContent = permission;
      list.append(badge);
    });
    section.append(heading, list);
    byId('permission-groups').append(section);
  }
  byId('questions').hidden = !plan.clarification_questions.length;
  byId('questions').textContent = plan.clarification_questions.join(' ');
  byId('risk-heading').textContent = `Suggested risk: ${plan.risk_suggestion.level}`;
  byId('risk-reasons').replaceChildren();
  plan.risk_suggestion.reasons.forEach((reason) => {
    const item = document.createElement('li');
    item.textContent = reason;
    byId('risk-reasons').append(item);
  });
  byId('activity').replaceChildren();
  data.activity_steps.forEach((step) => {
    const item = document.createElement('li');
    item.textContent = step.message;
    byId('activity').append(item);
  });
}

form.addEventListener('input', () => {
  clearPreview();
  byId('ai-feedback').hidden = true;
});
byId('request-title').addEventListener('input', () => { autoTitle = false; });
byId('business-unit').addEventListener('input', () => { autoBusinessUnit = false; });
byId('target-role').addEventListener('change', updateContextSuggestions);
byId('ai-description').addEventListener('input', () => {
  clearPreview();
  byId('ai-feedback').hidden = true;
});
byId('employee').addEventListener('change', updateEmployee);
byId('request-type').addEventListener('change', updateRequestType);
byId('assignment-type').addEventListener('change', () => {
  byId('temporary-note').hidden = byId('assignment-type').value !== 'TEMPORARY';
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  if (busy) return;
  if (!byId('justification').value.trim()) {
    showError('Please enter a business justification.');
    return;
  }
  const currentRevision = revision;
  const button = byId('generate');
  setBusy(true);
  button.textContent = 'Generating plan…';
  byId('plan-status').textContent = 'Generating';
  showError('');
  try {
    const offboarding = byId('request-type').value === 'OFFBOARD';
    const payload = {
      employee_code: byId('employee').value,
      request_context: readRequestContext(),
      details: {
        effective_date: byId('effective-date').value,
        justification: byId('justification').value.trim(),
        manager: byId('manager').value,
      },
    };
    if (!offboarding) {
      payload.target_role = byId('target-role').value;
      payload.details.assignment_type = byId('assignment-type').value;
    }
    const response = await fetch(offboarding ? '/agent/offboard' : '/agent/role-change', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(payload),
      signal: AbortSignal.timeout(35000),
    });
    const data = await response.json();
    if (currentRevision !== revision) return;
    if (!response.ok) {
      throw new Error(responseError(data));
    }
    renderPlan(data);
  } catch (error) {
    if (currentRevision === revision) {
      byId('plan-status').textContent = 'Needs attention';
      showError(error.name === 'TimeoutError' ? 'The service took too long to respond. Please try again.' : error.message);
    }
  } finally {
    setBusy(false);
    button.textContent = 'Generate access plan';
  }
});

function fillExtractedFields(data) {
  const interpretation = data.interpretation;
  const details = data.extracted_details;
  // Missing values clear old fields so the user cannot unknowingly mix requests.
  byId('request-type').value = interpretation.action || 'ROLE_CHANGE';
  byId('employee').value = interpretation.employee_code || '';
  updateEmployee();
  byId('target-role').value = interpretation.target_role || '';
  byId('manager').value = details.manager || '';
  byId('effective-date').value = details.effective_date || '';
  byId('justification').value = details.justification || '';
  byId('assignment-type').value = details.assignment_type || '';
  byId('temporary-note').hidden = details.assignment_type !== 'TEMPORARY';
  updateRequestType();
}

byId('interpret-description').addEventListener('click', async () => {
  if (busy) return;
  const message = byId('ai-description').value.trim();
  if (!message) {
    byId('ai-feedback').textContent = 'Enter a request description first.';
    byId('ai-feedback').hidden = false;
    return;
  }
  clearPreview();
  const currentRevision = revision;
  const button = byId('interpret-description');
  setBusy(true);
  button.textContent = 'Interpreting request…';
  byId('ai-feedback').hidden = true;
  byId('plan-status').textContent = 'Interpreting';
  try {
    const response = await fetch('/agent/plan', {
      method: 'POST', headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({message, use_model: true, request_context: readRequestContext()}),
      signal: AbortSignal.timeout(45000),
    });
    const data = await response.json();
    if (currentRevision !== revision) return;
    if (!response.ok) throw new Error(responseError(data));
    // Partial, ambiguous, or refused interpretations never become a final plan.
    fillExtractedFields(data);
    if (data.plan) renderPlan(data);
    const questions = [...data.interpretation.clarification_questions, ...(data.plan?.clarification_questions || [])];
    byId('ai-feedback').textContent = questions.length
      ? `Review the extracted fields and complete the missing details. ${questions.join(' ')}`
      : 'AI filled the request fields. Review them, then choose Generate access plan to confirm your final draft.';
    byId('ai-feedback').hidden = false;
    if (!data.plan && !questions.length) showError(data.message);
  } catch (error) {
    if (currentRevision === revision) {
      byId('plan-status').textContent = 'Needs attention';
      showError(error.name === 'TimeoutError' ? 'AI interpretation took too long. Retry later or complete the form manually.' : error.message);
    }
  } finally {
    button.textContent = 'Use AI to fill form';
    setBusy(false);
  }
});

async function loadOptions() {
  try {
    const response = await fetch('/agent/form-options', {signal: AbortSignal.timeout(10000)});
    if (!response.ok) throw new Error('Unable to load employee data. Reload the page to try again.');
    const data = await response.json();
    employees = data.employees;
    backendMode = data.backend_mode;
    modelConfigured = Boolean(data.model?.configured);
    const provider = data.model?.provider === 'groq' ? 'Groq' : 'OpenAI';
    byId('model-status').textContent = modelConfigured ? `${provider} configured` : 'AI not configured';
    byId('provider-disclosure').textContent = modelConfigured
      ? `Use AI to fill form sends your description to ${provider}. Review the extracted fields before continuing.`
      : 'AI assistance is unavailable on this server. You can still complete the form manually.';
    byId('employee').replaceChildren(option('', 'Select an employee'));
    employees.forEach((employee) => byId('employee').append(option(employee.employee_code, `${employee.name} · ${employee.employee_code}`)));
    data.roles.forEach((role) => byId('target-role').append(option(role, role)));
    updateEmployee();
    ['employee', 'target-role', 'manager'].forEach((id) => { byId(id).disabled = false; });
    setBusy(false);
    if (backendMode === 'mock') prefillForm();
  } catch (error) {
    showError(error.message || 'Unable to load form data. Reload the page to try again.');
  }
}
loadOptions();
