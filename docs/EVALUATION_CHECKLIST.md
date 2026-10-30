# Evaluation checklist (demonstration steps)

Before starting: complete the README setup, then run `python -m flask --app app init-db`.

1. **Start the app:** `python app.py`, open http://127.0.0.1:5000.
2. **Register a user:** Create an account (name, email, password with a letter and number).
3. **Log in as the user** on the Sign in page.
4. **View the dashboard:** four summary cards (zeros at first) and charts ("No data yet").
5. **Add a patient:** sidebar → Add Patient. Example: Robyn Pears, 28/01/1960, robyn@gmail.com, 232, 13.5, 180.
6. **Show all seven fields** in order: Full Name, DOB, Email, Glucose, Haemoglobin, Cholesterol, Remarks.
7. **Confirm Remarks** is the text area directly below Cholesterol.
8. **Validation errors:** try DOB `31/11/2001`, DOB `19/10/2030`, email `hunter@gmail`, glucose `-5` and an empty name. Messages appear per field and typed values are kept.
9. **Saved record:** save a valid patient; see it in Patients and on the dashboard.
10. **Details page:** click View (DOB shows as DD/MM/YYYY; your remarks and AI assessment are separate).
11. **Edit email:** click Edit and change the email to `gokul@infocare.com` (manual step only).
12. **Save and show** the updated record.
13. **Delete:** click Delete, accept the confirmation.
14. **Dashboard/charts** update (counts and bars change).
15. **AI assessment (if you have a key):** put `GEMINI_API_KEY` in `.env`, restart, add a patient; see the AI-generated remarks.
16. **AI pending/retry:** without a key (or with a wrong key) a patient shows "AI not configured"/"failed"; fix the key, restart and press Retry assessment. Also: edit a glucose value and see "Outdated".
17. **Create an admin:** in a second PowerShell (venv active) run `python -m flask --app app create-admin`.
18. **Admin login:** open /admin/login and sign in.
19. **Admin Dashboard:** totals, charts, recent activity; All Patients shows owners.
20. **User management:** search a user, open Details, Deactivate then Activate.
21. **Audit history:** shows logins, failures, logouts, deactivations (no passwords).
22. **Role check:** as a regular user open /admin → "Access denied". On /admin/login a regular user's password is refused.
23. **Isolation:** with two users, user B cannot open user A's patient URL (404).
24. **Logout:** click Logout, then open /dashboard → redirected to login.

Extra: `python -m scripts.validate_records` (shows records 2, 4, 8 invalid) and `python -m pytest -q`.
