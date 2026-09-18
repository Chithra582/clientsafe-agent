/**
 * ClinSafe Agent Client Application Logic.
 * Handles preset patient selection, document ingestion, PHI diff inspection,
 * deterministic criteria matrix, confidence governance, and FDA dossier downloads.
 */

let currentPresetId = 'patient_01';
let currentRunId = null;
let currentDossierData = null;
let presetsData = {};
let activePatientFormat = 'json';

// Initialize application on load
document.addEventListener('DOMContentLoaded', async () => {
  await loadPresets();
  await refreshAimsEvents();
});

// Switch between tabs
function switchTab(tabName) {
  const tabs = ['screen', 'phi', 'results', 'dossier'];
  tabs.forEach(t => {
    const el = document.getElementById(`tab-${t}`);
    const btn = document.getElementById(`tab-btn-${t}`);
    if (t === tabName) {
      el.classList.remove('hidden');
      btn.classList.add('active', 'text-white');
      btn.classList.remove('text-slate-400');
    } else {
      el.classList.add('hidden');
      btn.classList.remove('active', 'text-white');
      btn.classList.add('text-slate-400');
    }
  });
}

// Fetch synthetic presets and sample protocol
async function loadPresets() {
  try {
    const res = await fetch('/api/ingest/presets');
    if (!res.ok) return;
    const data = await res.json();
    presetsData = data;

    // Populate protocol textarea with sample protocol
    if (data.protocol_sample_text) {
      document.getElementById('protocol-text').value = data.protocol_sample_text;
    }

    // Default select patient 1
    selectPreset('patient_01');
  } catch (err) {
    console.error('Failed loading presets:', err);
  }
}

// Select preset patient card
function selectPreset(presetId) {
  currentPresetId = presetId;
  const cards = ['patient_01', 'patient_02', 'patient_03'];
  cards.forEach((pid, idx) => {
    const cardEl = document.getElementById(`card-preset-${idx + 1}`);
    if (pid === presetId) {
      cardEl.classList.add('border-blue-600', 'ring-2', 'ring-blue-400/50');
      cardEl.classList.remove('border-slate-200');
    } else {
      cardEl.classList.remove('border-blue-600', 'ring-2', 'ring-blue-400/50');
      cardEl.classList.add('border-slate-200');
    }
  });

  const presetObj = (presetsData.presets || []).find(p => p.id === presetId);
  if (!presetObj) return;

  const labelEl = document.getElementById('patient-filename-label');
  labelEl.innerText = `Loaded: ${presetObj.name}`;

  if (activePatientFormat === 'json') {
    document.getElementById('patient-input').value = JSON.stringify(presetObj.patient_data, null, 2);
  } else {
    document.getElementById('patient-input').value = presetObj.patient_note;
  }
}

// Format toggle for patient input
function setPatientInputFormat(format) {
  activePatientFormat = format;
  const btnJson = document.getElementById('btn-fmt-json');
  const btnNote = document.getElementById('btn-fmt-note');

  if (format === 'json') {
    btnJson.className = 'px-2.5 py-1 text-xs font-medium bg-cyan-600 text-white rounded';
    btnNote.className = 'px-2.5 py-1 text-xs font-medium bg-slate-100 text-slate-600 rounded';
  } else {
    btnNote.className = 'px-2.5 py-1 text-xs font-medium bg-cyan-600 text-white rounded';
    btnJson.className = 'px-2.5 py-1 text-xs font-medium bg-slate-100 text-slate-600 rounded';
  }
  selectPreset(currentPresetId);
}

// Handle protocol file upload
async function handleProtocolUpload(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/ingest/protocol', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      document.getElementById('protocol-text').value = data.extracted_text;
      document.getElementById('protocol-filename-label').innerText = `Uploaded: ${file.name} (${data.length_chars} chars)`;
    } else {
      alert('Error parsing protocol: ' + data.detail);
    }
  } catch (err) {
    alert('Failed uploading protocol file');
  }
}

// Handle patient file upload
async function handlePatientUpload(input) {
  if (!input.files || input.files.length === 0) return;
  const file = input.files[0];
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch('/api/ingest/patient', {
      method: 'POST',
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      if (data.format === 'json') {
        setPatientInputFormat('json');
        document.getElementById('patient-input').value = JSON.stringify(data.patient_data, null, 2);
      } else {
        setPatientInputFormat('note');
        document.getElementById('patient-input').value = data.raw_text;
      }
      document.getElementById('patient-filename-label').innerText = `Uploaded: ${file.name}`;
    } else {
      alert('Error parsing patient: ' + data.detail);
    }
  } catch (err) {
    alert('Failed uploading patient file');
  }
}

// Execute Governed Screening Pipeline
async function executeScreeningPipeline() {
  const btn = document.getElementById('btn-run-screening');
  const spinner = document.getElementById('spinner-run');
  btn.disabled = true;
  spinner.classList.remove('hidden');

  const protocolText = document.getElementById('protocol-text').value.trim();
  const patientText = document.getElementById('patient-input').value.trim();

  let patientPayload = null;
  let rawTextPayload = null;

  try {
    if (activePatientFormat === 'json') {
      patientPayload = JSON.parse(patientText);
    } else {
      rawTextPayload = patientText;
    }
  } catch (e) {
    // If json parse failed, fall back to raw text
    rawTextPayload = patientText;
  }

  const payload = {
    protocol_text: protocolText,
    protocol_id: 'ONCO-2026-X',
    patient_data: patientPayload,
    patient_raw_text: rawTextPayload,
    preset_patient_id: (!patientPayload && !rawTextPayload) ? currentPresetId : null
  };

  try {
    const res = await fetch('/api/screen/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      alert('Screening error: ' + (err.detail || 'Pipeline execution failed'));
      return;
    }

    const result = await res.json();
    currentRunId = result.run_id;
    currentDossierData = result.audit_dossier;

    // Render results across all views
    renderBannerStatus(result);
    renderPhiAudit(result);
    renderResultsMatrix(result);
    renderDossierView(result);
    await refreshAimsEvents();

    // Switch view to Results
    switchTab('results');

  } catch (err) {
    console.error('Execution error:', err);
    alert('Pipeline network error: ' + err.message);
  } finally {
    btn.disabled = false;
    spinner.classList.add('hidden');
  }
}

// Render Top Status & HITL Banners
function renderBannerStatus(result) {
  const banner = document.getElementById('banner-run-status');
  const hitlBanner = document.getElementById('banner-hitl-alert');
  const iconEl = document.getElementById('banner-icon');
  const decisionEl = document.getElementById('banner-decision-text');
  const confEl = document.getElementById('banner-confidence-badge');
  const runIdEl = document.getElementById('banner-run-id');
  const summaryEl = document.getElementById('banner-summary-text');

  banner.classList.remove('hidden');
  runIdEl.innerText = result.run_id;
  decisionEl.innerText = result.final_decision;
  confEl.innerText = `${result.confidence_percentage}% Confidence`;

  if (result.final_decision === 'ELIGIBLE') {
    banner.className = 'rounded-xl border border-emerald-300 bg-emerald-50/90 p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4';
    iconEl.className = 'w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg bg-emerald-600 text-white';
    iconEl.innerText = '✓';
    decisionEl.className = 'text-xl font-bold tracking-tight text-emerald-900';
    confEl.className = 'px-3 py-0.5 rounded-full text-xs font-bold bg-emerald-200 text-emerald-900';
    summaryEl.innerText = 'Patient successfully meets all inclusion criteria and exhibits no exclusionary contraindications.';
  } else if (result.final_decision === 'INELIGIBLE') {
    banner.className = 'rounded-xl border border-red-300 bg-red-50/90 p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4';
    iconEl.className = 'w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg bg-red-600 text-white';
    iconEl.innerText = '✕';
    decisionEl.className = 'text-xl font-bold tracking-tight text-red-900';
    confEl.className = 'px-3 py-0.5 rounded-full text-xs font-bold bg-red-200 text-red-900';
    const failedList = result.screening_evaluation.failed_criteria.join(', ');
    summaryEl.innerText = `Disqualified based on deterministic criteria failure (${failedList}) and/or medical safety contraindications.`;
  } else {
    banner.className = 'rounded-xl border border-amber-300 bg-amber-50/90 p-4 shadow-sm flex flex-col md:flex-row items-start md:items-center justify-between gap-4';
    iconEl.className = 'w-12 h-12 rounded-xl flex items-center justify-center font-bold text-lg bg-amber-600 text-white';
    iconEl.innerText = '!';
    decisionEl.className = 'text-xl font-bold tracking-tight text-amber-900';
    confEl.className = 'px-3 py-0.5 rounded-full text-xs font-bold bg-amber-200 text-amber-900';
    summaryEl.innerText = 'Borderline biomarkers, narrow washout window, or missing lab tests require human coordinator review.';
  }

  // HITL Alert Banner
  if (result.hitl_pause_triggered) {
    hitlBanner.classList.remove('hidden');
    const reasons = (result.confidence_governance.reasons_for_flag || []).join('; ');
    document.getElementById('hitl-reason-text').innerText = reasons || 'Confidence is below 90% regulatory threshold. Pipeline paused for human verification.';
  } else {
    hitlBanner.classList.add('hidden');
  }
}

// Render PHI Redaction Audit View
function renderPhiAudit(result) {
  const phi = result.phi_scrubbing;
  const tbody = document.getElementById('phi-diff-tbody');
  tbody.innerHTML = '';

  document.getElementById('phi-count-badge').innerText = `${phi.entities_redacted_count} Entities Redacted`;

  if (phi.diff && phi.diff.length > 0) {
    phi.diff.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td class="px-4 py-2 font-mono font-bold text-slate-800">${item.entity_type}</td>
        <td class="px-4 py-2 font-mono text-red-600 bg-red-50/50">${escapeHtml(String(item.original_value))}</td>
        <td class="px-4 py-2 font-mono text-emerald-700 bg-emerald-50/50 font-semibold">${escapeHtml(String(item.redacted_value))}</td>
        <td class="px-4 py-2 text-slate-500 text-[11px]">${item.detector || 'safe_ai_rule'}</td>
      `;
      tbody.appendChild(tr);
    });
  } else {
    tbody.innerHTML = '<tr><td colspan="4" class="px-4 py-4 text-center text-slate-400">No PHI detected or input was already de-identified.</td></tr>';
  }

  // Side-by-side text display
  document.getElementById('phi-raw-view').innerText = document.getElementById('patient-input').value;
  document.getElementById('phi-sanitized-view').innerText = JSON.stringify(phi.sanitized_record, null, 2);
  document.getElementById('hash-raw-label').innerText = 'Input Checked';
  document.getElementById('hash-clean-label').innerText = 'Zero Raw PHI Past Gate';
}

// Render Criteria Matrix & Safety Results
function renderResultsMatrix(result) {
  const scr = result.screening_evaluation;
  const safety = result.medical_safety;
  const gov = result.confidence_governance;

  // Overview metrics
  document.getElementById('res-metric-status').innerText = result.final_decision;
  document.getElementById('res-metric-confidence').innerText = `${result.confidence_percentage}% (${gov.agreement_type || 'Convergent'})`;
  document.getElementById('res-metric-passing').innerText = `${scr.passed_count} / ${scr.total_evaluated} Passed (${scr.failed_count} Failed, ${scr.unknown_count} Missing)`;
  document.getElementById('res-metric-safety').innerText = `${safety.safety_decision} (${safety.contraindications_count} flags)`;

  // Rules table
  const tbody = document.getElementById('criteria-eval-tbody');
  tbody.innerHTML = '';
  document.getElementById('matrix-rules-count').innerText = `${scr.total_evaluated} Criteria Rules Evaluated`;

  scr.evaluations.forEach(ev => {
    const tr = document.createElement('tr');
    const status = ev.status;
    let badgeClass = 'bg-emerald-100 text-emerald-800';
    if (status === 'FAIL') badgeClass = 'bg-red-100 text-red-800';
    if (status === 'UNKNOWN') badgeClass = 'bg-amber-100 text-amber-800';

    const obsStr = ev.observed_value !== null ? `${ev.observed_value} ${ev.unit || ''}`.trim() : '<span class="text-amber-600 font-bold">UNRECORDED</span>';

    tr.innerHTML = `
      <td class="px-3.5 py-2.5 font-mono font-bold text-slate-900">${ev.criterion_id}</td>
      <td class="px-3.5 py-2.5 text-slate-500 font-mono text-[11px]">p.${ev.protocol_page}</td>
      <td class="px-3.5 py-2.5 font-mono text-slate-700">${ev.field} ${ev.operator} ${ev.target_value} ${ev.unit || ''}</td>
      <td class="px-3.5 py-2.5 font-mono text-slate-800">${obsStr}</td>
      <td class="px-3.5 py-2.5"><span class="px-2 py-0.5 rounded text-[11px] font-bold ${badgeClass}">${status}</span></td>
      <td class="px-3.5 py-2.5 text-slate-600 text-xs">${escapeHtml(ev.reasoning)}</td>
    `;
    tbody.appendChild(tr);
  });

  // Safety findings
  const safetyBadge = document.getElementById('safety-status-badge');
  safetyBadge.innerText = safety.safety_decision;
  safetyBadge.className = safety.safety_decision === 'SAFE' 
    ? 'px-3 py-1 text-xs font-bold rounded-full bg-emerald-100 text-emerald-800'
    : 'px-3 py-1 text-xs font-bold rounded-full bg-red-100 text-red-800';

  const safetyContainer = document.getElementById('safety-contraindications-container');
  safetyContainer.innerHTML = '';

  if (safety.flagged_contraindications && safety.flagged_contraindications.length > 0) {
    safety.flagged_contraindications.forEach(c => {
      const div = document.createElement('div');
      div.className = 'p-3 bg-red-50 border border-red-200 rounded-xl text-xs space-y-1';
      div.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-red-800">[${c.ontology} ${c.code}] ${c.description}</span>
          <span class="px-2 py-0.5 bg-red-200 text-red-900 rounded font-bold uppercase text-[10px]">Risk: ${c.risk_level}</span>
        </div>
        <p class="text-red-700">${escapeHtml(c.finding)}</p>
        <p class="text-[11px] text-red-600 font-mono">Action: ${c.action_required}</p>
      `;
      safetyContainer.appendChild(div);
    });
  } else {
    const div = document.createElement('div');
    div.className = 'p-3 bg-emerald-50 border border-emerald-200 rounded-xl text-xs text-emerald-800 flex items-center';
    div.innerHTML = `
      <svg class="w-4 h-4 mr-2 text-emerald-600" fill="currentColor" viewBox="0 0 20 20">
        <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clip-rule="evenodd" />
      </svg>
      <span>Cleared: No exclusionary ICD-10 comorbidities, active autoimmune flares, or unstable cardiac conditions found.</span>
    `;
    safetyContainer.appendChild(div);
  }

  if (safety.ambiguous_safety_risks && safety.ambiguous_safety_risks.length > 0) {
    safety.ambiguous_safety_risks.forEach(a => {
      const div = document.createElement('div');
      div.className = 'p-3 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-900 mt-2';
      div.innerHTML = `<b>Ambiguity Detected (${a.field}):</b> ${escapeHtml(a.issue)}`;
      safetyContainer.appendChild(div);
    });
  }
}

// Render Dossier Explorer & PDF Download
function renderDossierView(result) {
  const dossier = result.audit_dossier;
  document.getElementById('dossier-json-view').innerText = JSON.stringify(dossier, null, 2);
  document.getElementById('dossier-hash-display').innerText = `SHA-256: ${dossier.electronic_audit_hash.substring(0, 20)}...`;
}

// Download FDA PDF Dossier
function downloadCurrentPdf() {
  if (!currentRunId) {
    alert('Please execute a screening run first.');
    return;
  }
  window.open(`/api/dossier/${currentRunId}/pdf`, '_blank');
}

// Copy Dossier JSON to clipboard
function copyDossierJson() {
  if (!currentDossierData) return;
  navigator.clipboard.writeText(JSON.stringify(currentDossierData, null, 2));
  alert('Audit Dossier JSON copied to clipboard!');
}

// Refresh Live Lyzr AIMS Events Stream
async function refreshAimsEvents() {
  try {
    const res = await fetch('/api/aims/events?limit=25');
    if (!res.ok) return;
    const events = await res.json();
    const container = document.getElementById('aims-events-container');
    container.innerHTML = '';

    if (events.length === 0) {
      container.innerHTML = '<p class="text-xs text-slate-400 italic">No telemetry recorded yet.</p>';
      return;
    }

    events.slice().reverse().forEach(evt => {
      const div = document.createElement('div');
      let layerBadge = 'bg-blue-100 text-blue-800';
      if (evt.triad_layer === 'ENVIRONMENT') layerBadge = 'bg-slate-100 text-slate-800';
      if (evt.triad_layer === 'AGENT') layerBadge = 'bg-purple-100 text-purple-800';
      if (evt.triad_layer === 'INFERENCE') layerBadge = 'bg-cyan-100 text-cyan-800';
      if (evt.triad_layer === 'GOVERNANCE') layerBadge = 'bg-amber-100 text-amber-800';
      if (evt.triad_layer === 'COMPLIANCE') layerBadge = 'bg-emerald-100 text-emerald-800';

      div.className = 'p-2.5 bg-slate-50 border border-slate-200 rounded-lg text-xs space-y-1';
      div.innerHTML = `
        <div class="flex items-center justify-between">
          <span class="font-bold text-slate-800 font-mono">${evt.event_type}</span>
          <span class="px-1.5 py-0.5 rounded text-[10px] font-bold ${layerBadge}">${evt.triad_layer}</span>
        </div>
        <div class="flex items-center justify-between text-[11px] text-slate-500">
          <span>Agent: <b>${evt.agent_name}</b></span>
          <span class="font-mono">${evt.latency_ms} ms</span>
        </div>
      `;
      container.appendChild(div);
    });
  } catch (err) {
    console.error('Failed refreshing AIMS:', err);
  }
}

// Utility: Escape HTML
function escapeHtml(text) {
  if (!text) return '';
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
