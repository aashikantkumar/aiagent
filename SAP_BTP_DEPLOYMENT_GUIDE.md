# Guide: Deploying ABAP Applications to SAP BTP

Deploying ABAP applications to **SAP Business Technology Platform (SAP BTP) ABAP Environment** (frequently referred to as *Steampunk*) involves a Git-based lifecycle. 

Here is everything you need and how to do it step-by-step.

---

## 📋 1. Infrastructure & Account Requirements

To deploy code, you need access to an SAP BTP account. Specifically:

* **SAP BTP Subaccount:** Active Global Account with a Subaccount configured.
* **Entitlements:** You must add the entitlement for **SAP BTP ABAP Environment (Steampunk)** to your subaccount.
* **ABAP Instance:** Create an instance of the ABAP system (usually under the `abap` service plan).
* **Role Assignments:** Your user must be assigned to the Developer role group (e.g. `ABAP_Developer` or custom equivalent) inside the BTP cockpit.

---

## 💻 2. Local Developer Tools Needed

You cannot develop or deploy to BTP directly from a standard web browser. You must set up:

1. **Eclipse IDE:** Install the latest version of Eclipse.
2. **ABAP Development Tools (ADT):** Install the ADT plugin inside Eclipse via `Help > Install New Software` using the SAP development tools URL: `https://tools.hana.ondemand.com/latest`.
3. **abapGit ADT Plugin:** Add the abapGit plugin to Eclipse ADT to enable cloning of Git repositories into your BTP instance.

---

## ⚠️ 3. Code Compatibility: Moving from Local ABAP to ABAP Cloud

SAP BTP ABAP Environment runs under strict **ABAP Cloud** rules (formerly "ABAP for Cloud Development"). Because of this:

* **No Traditional Reports (`REPORT`) & `WRITE` statements:** You cannot use classic report scripts or `WRITE /` statements.
* **Console Execution:** For simple console/background execution (like our CLI To-Do app), you must encapsulate the code in a class implementing the `if_oo_adt_classrun` interface and use the `out->write( )` method:
  ```abap
  CLASS zcl_todo_app DEFINITION PUBLIC FINAL CREATE PUBLIC.
    PUBLIC SECTION.
      INTERFACES if_oo_adt_classrun.
  ENDCLASS.
  
  CLASS zcl_todo_app IMPLEMENTATION.
    METHOD if_oo_adt_classrun~main.
      out->write( '--- ABAP TO-DO LIST ---' ).
      " ... your table looping and output here ...
    ENDMETHOD.
  ENDCLASS.
  ```
* **Real Web / Mobile UI (RAP Model):** To build a real web interface for your To-Do App on BTP, you will need to use the **ABAP RESTful Application Programming Model (RAP)**:
  1. Define a transparent database table (e.g., `ztodo_table`) to store tasks.
  2. Create a **Core Data Services (CDS) Data Model** over it.
  3. Define a **Behavior Definition (BDEF)** for CRUD operations.
  4. Create a **Service Definition** and **Service Binding** to expose it as an OData Web API.
  5. Generate a **Fiori Elements** web app in BTP to serve as the user interface.

---

## 🚀 4. Deployment Workflow (Step-by-Step)

### Step A: Push Your ABAP Code to Git (GitHub/GitLab)
Ensure your ABAP files are organized in the standard **abapGit** directory structure:
* The source file should be placed inside a folder named `src` (e.g., `src/zcl_todo_app.clas.abap` and `src/zcl_todo_app.clas.xml`).
* Ensure there is an `abapgit.xml` metadata file at the root of the repository describing the package configuration.

### Step B: Connect Eclipse ADT to SAP BTP
1. Open Eclipse ADT.
2. Select `File > New > ABAP Project`.
3. Choose **SAP BTP ABAP Environment** as the connection type.
4. Log in using your SAP BTP credentials (this opens a browser window to authenticate).
5. Eclipse will establish a connection to your cloud system.

### Step C: Create a Package in BTP
1. In the ADT Project Explorer, right-click on the ABAP system and select `New > ABAP Package`.
2. Name it (e.g., `Z_TODO_APP`).
3. Make sure to assign it to the Software Component assigned to your system (often `ZLOCAL` or a custom software component managed in the Fiori *Manage Software Components* app).

### Step D: Clone & Deploy Code using abapGit
1. In Eclipse ADT, open the **abapGit Repositories** view (`Window > Show View > Other > abapGit > abapGit Repositories`).
2. Click the **+** icon (Clone repository).
3. Enter your Git repository URL (e.g., `https://github.com/your-username/abap-todo-app.git`).
4. Select your newly created ABAP Package (`Z_TODO_APP`).
5. Right-click the repository in the view and select **Pull**.
6. Activate all pulled objects.

Once activated, your code is compiled and fully deployed inside the SAP BTP environment! You can run console classes using `F9` in Eclipse.
