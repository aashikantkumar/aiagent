#!/usr/bin/env python3
import json
import ssl
import urllib.request
import urllib.parse
import sys

# Load service key credentials (either from this file or from a path)
SERVICE_KEY = {
  "uaa": {
    "tenantmode": "dedicated",
    "sburl": "https://internal-xsuaa.authentication.us10.hana.ondemand.com",
    "subaccountid": "415c26c0-6dcf-4fb3-a768-1d8b61693a24",
    "credential-type": "binding-secret",
    "clientid": "sb-acd27e89-1a1d-4d28-935e-8659a266de1c!b652961|abap-trial-service-broker!b3132",
    "xsappname": "acd27e89-1a1d-4d28-935e-8659a266de1c!b652961|abap-trial-service-broker!b3132",
    "clientsecret": "56cf07bc-4639-4194-8900-1c7bc6601eb5$HRzjbtD05tm1Prr3r_MwA7hUwoeL9r125dnYWemTaAo=",
    "serviceInstanceId": "acd27e89-1a1d-4d28-935e-8659a266de1c",
    "url": "https://c345e0fbtrial.authentication.us10.hana.ondemand.com",
    "uaadomain": "authentication.us10.hana.ondemand.com",
    "verificationkey": "-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAiUBxmPvqnf/dbfIqt+20\n0bMZQoXAn41QDMbYFco2S0Z06TuUhxXp2vWhrL3EfRenMgmhNobymer2M3BAWJln\nvJqkLE2fd05doCIQ+8rqcWOP+86iehUGLxpcD+1y4/ULtLk51HHj5x1THjUAO483\ngh5FVtAS69MaGWZdYJphdxlIHAhRyBpWuLHkN9m/SAKCADBwSZKI9iVb2OJ8lHVG\nfQqk8LeM1reL5jHW4kbQnbNraxCJ6WmL763xmV/MXbfWgwWLK3EoKIdjowkSFW9H\nAHAnFjFb2JoVUv4eEhtu9r8CAuD+XOtUKW5QECgZH5SYtP10EbelxLCTitDAEXRP\nmQIDAQAB\n-----END PUBLIC KEY-----",
    "apiurl": "https://api.authentication.us10.hana.ondemand.com",
    "identityzone": "c345e0fbtrial",
    "identityzoneid": "415c26c0-6dcf-4fb3-a768-1d8b61693a24",
    "tenantid": "415c26c0-6dcf-4fb3-a768-1d8b61693a24",
    "zoneid": "415c26c0-6dcf-4fb3-a768-1d8b61693a24"
  },
  "url": "https://bb8534dd-13b7-4042-bba9-41728e5288ac.abap.us10.hana.ondemand.com",
  "sap.cloud.service": "com.sap.cloud.abap",
  "systemid": "TRL",
  "endpoints": {
    "abap": "https://bb8534dd-13b7-4042-bba9-41728e5288ac.abap.us10.hana.ondemand.com"
  },
  "catalogs": {
    "abap": {
      "path": "/sap/opu/odata/IWFND/CATALOGSERVICE;v=2",
      "type": "sap_abap_catalog_v1"
    }
  },
  "binding": {
    "env": "cf",
    "version": "1.0.1.1",
    "type": "oauth",
    "id": "56cf07bc-4639-4194-8900-1c7bc6601eb5"
  },
  "preserve_host_header": True
}

def get_oauth_token():
    """Retrieve an OAuth 2.0 Access Token from XSUAA using Client Credentials."""
    uaa_url = SERVICE_KEY["uaa"]["url"] + "/oauth/token"
    client_id = SERVICE_KEY["uaa"]["clientid"]
    client_secret = SERVICE_KEY["uaa"]["clientsecret"]
    
    print(f"Requesting token from: {uaa_url}...")
    
    # Prepare URL-encoded form data
    payload = urllib.parse.urlencode({
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret
    }).encode("utf-8")
    
    req = urllib.request.Request(
        uaa_url,
        data=payload,
        headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }
    )
    
    # Disable strict SSL hostname/certificate checks if running on trials/private networks
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ssl_context) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            token = res_data["access_token"]
            print("Successfully retrieved OAuth token.")
            return token
    except Exception as e:
        print(f"Error fetching token: {e}", file=sys.stderr)
        return None

def trigger_gcts_pull(access_token, repo_id, commit_id="latest"):
    """Trigger gCTS code deployment on the BTP ABAP Environment system."""
    abap_url = SERVICE_KEY["url"]
    
    # Path for standard Git VCS pulls
    # GET /sap/bc/cts_abapvcs/repositories/{id}/pullByCommit?request={commitId}
    pull_url = f"{abap_url}/sap/bc/cts_abapvcs/repositories/{repo_id}/pullByCommit?request={commit_id}"
    
    print(f"Triggering gCTS pull at: {pull_url}...")
    
    req = urllib.request.Request(
        pull_url,
        headers={
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/json"
        }
    )
    
    # Disable strict SSL verification
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    
    try:
        with urllib.request.urlopen(req, context=ssl_context) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            print("\nDeployment Response:")
            print(json.dumps(res_data, indent=2))
            return True
    except Exception as e:
        print(f"Error triggering deploy: {e}", file=sys.stderr)
        return False

if __name__ == "__main__":
    # Get the repo ID (repository registered in your BTP gCTS Fiori app)
    # E.g. z_todo_app
    if len(sys.argv) < 2:
        print("Usage: python3 deploy_to_btp.py <repository_id> [commit_id]")
        print("Example: python3 deploy_to_btp.py z_todo_app latest")
        sys.exit(1)
        
    repo = sys.argv[1]
    commit = sys.argv[2] if len(sys.argv) > 2 else "latest"
    
    token = get_oauth_token()
    if token:
        trigger_gcts_pull(token, repo, commit)
