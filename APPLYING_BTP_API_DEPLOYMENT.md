# Prerequisite Setup: Applying BTP API Deployment

To successfully run `deploy_to_btp.py` and deploy your ABAP code to your SAP BTP Trial system (`TRL`) via the API, you must configure the repository mapping inside your BTP system first.

Here are the step-by-step requirements:

---

## 🛠️ Step 1: Push Your ABAP Code to GitHub

gCTS pulls your code from a Git provider. You must first push your ABAP code to a GitHub repository (public or private):

1. **Repository Structure:** Create a repository with a `src/` folder.
2. **abapGit Config:** Add an `abapgit.xml` metadata file to the root of the repository to identify it as a valid ABAP package.
3. **ABAP Code:** Place your BTP-compatible ABAP Class code inside the `src/` folder (e.g., `src/zcl_todo_app.clas.abap`).

---

## 🌐 Step 2: Register the Repository in SAP BTP Fiori Launchpad

Your BTP ABAP system needs to know which Git repository corresponds to your software component.

1. **Open Fiori Launchpad:** Go to the SAP BTP Cockpit, open your ABAP trial dashboard, and click the link to open the **SAP Fiori Launchpad**.
2. **Open "Manage Software Components":** Find and open the Fiori app named **Manage Software Components**.
3. **Create a Software Component:**
   * Click **Create** (or **+**).
   * Enter a name (e.g. `Z_TODO_APP`). This name will be your **Repository ID**.
   * Select a package name if prompted (typically starting with `Z`).
4. **Link to GitHub Repository:**
   * Inside the newly created software component details page, navigate to the **Repositories** tab.
   * Enter the HTTPS URL of your GitHub repository (e.g. `https://github.com/your-username/abap-todo-app.git`).
   * Save the configuration.

---

## 🔑 Step 3: Configure Git Credentials in SAP BTP

If your GitHub repository is private, or if BTP needs authentication to write/commit back to GitHub:

1. **GitHub Token:** In your GitHub account, generate a **Personal Access Token (PAT)** with repository read/write permissions.
2. **Configure in BTP:** Inside the *Manage Software Components* app for your repository, click **Credentials**.
3. **Save Token:** Enter your GitHub username and paste the Personal Access Token. This authorizes the BTP `TRL` system to access your Git repository.

---

## 🚀 Step 4: Run the Deployment Script

Now that BTP is configured, your script can trigger the API.

1. Open your terminal in the workspace:
   ```bash
   cd "/media/aashikant/GAME Volume/aicode/myaiagent"
   ```
2. Run the Python script, replacing `Z_TODO_APP` with the software component name you created in Step 2:
   ```bash
   python3 deploy_to_btp.py Z_TODO_APP
   ```

### What Happens When You Run It:
1. The script calls the SAP UAA auth server (`https://c345e0fbtrial.authentication.us10.hana.ondemand.com`) to exchange client ID and secret for a session token.
2. The script calls the gCTS pull API endpoint:
   `https://bb8534dd-13b7-4042-bba9-41728e5288ac.abap.us10.hana.ondemand.com/sap/bc/cts_abapvcs/repositories/Z_TODO_APP/pullByCommit?request=latest`
3. Your SAP BTP trial system fetches the code directly from GitHub, parses it, compiles it, and activates it.
4. The terminal prints the success JSON response from BTP.
