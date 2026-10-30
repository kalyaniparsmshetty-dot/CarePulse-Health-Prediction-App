# Publishing to GitHub (Windows PowerShell)

1. **Create the repository:** on github.com click New repository, name it `health-prediction-app`, leave "Add README/.gitignore" **unticked**, create it.
2. **Open PowerShell in the project folder:** `cd path\to\health-prediction-app`
3. **Initialise Git:**
   ```powershell
   git init
   git branch -M main
   ```
4. **Review files:** `git status` (run after step 7 as well).
5. **Verify `.env` is excluded:** `git check-ignore -v .env` should print a `.gitignore` rule. `.env.example` (placeholders only) is fine.
6. **Verify venv and database are excluded:** `git check-ignore -v venv instance\health_app.db` should print rules for both.
7. **Add files:** `git add .` then `git status` — make sure no `.env`, `venv`, `instance`, `*.db` appear.
8. **Commit:**
   ```powershell
   git commit -m "Health Prediction and Patient Management System"
   ```
9. **Push:**
   ```powershell
   git remote add origin https://github.com/YOUR-USERNAME/health-prediction-app.git
   git push -u origin main
   ```
10. **Copy the repository URL** from the browser address bar for your submission email.

Never commit API keys, passwords, real patient data or virtual environments. If a key was committed by mistake, revoke it in Google AI Studio and create a new one.
