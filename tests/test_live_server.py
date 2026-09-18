import requests

base = 'http://127.0.0.1:8000'

# 1. Health check
r = requests.get(f'{base}/api/health')
print('Health check:', r.status_code, r.json()['status'])

# 2. Presets
r = requests.get(f'{base}/api/ingest/presets')
print('Presets count:', len(r.json()['presets']))

# 3. Screen Patient 1
r1 = requests.post(f'{base}/api/screen/run', json={'preset_patient_id': 'patient_01'})
d1 = r1.json()
print('Screen Patient 1:', d1['final_decision'], f"Conf={d1['confidence_percentage']}%, RunID={d1['run_id']}")

# 4. Screen Patient 2
r2 = requests.post(f'{base}/api/screen/run', json={'preset_patient_id': 'patient_02'})
d2 = r2.json()
print('Screen Patient 2:', d2['final_decision'], f"Conf={d2['confidence_percentage']}%, RunID={d2['run_id']}")

# 5. Screen Patient 3
r3 = requests.post(f'{base}/api/screen/run', json={'preset_patient_id': 'patient_03'})
d3 = r3.json()
print('Screen Patient 3:', d3['final_decision'], f"Conf={d3['confidence_percentage']}%, HITL={d3['hitl_pause_triggered']}, RunID={d3['run_id']}")

# 6. Test PDF download for Run 1
run_id = d1['run_id']
r_pdf = requests.get(f'{base}/api/dossier/{run_id}/pdf')
print('PDF Download:', r_pdf.status_code, len(r_pdf.content), 'bytes')

# 7. AIMS Stats
r_stats = requests.get(f'{base}/api/aims/stats')
print('AIMS Stats:', r_stats.json())

# 8. Webhook logs
r_wh = requests.get(f'{base}/api/webhook/logs')
print('Webhook logs count:', len(r_wh.json()))

# 9. Frontend Root
r_ui = requests.get(base)
print('UI Root status:', r_ui.status_code, 'HTML title present:', 'ClinSafe Agent' in r_ui.text)
