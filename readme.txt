Required inputs you've listed:

GitHub App name (actually, you need the App ID, not the name)
Secret Manager secret name (for the PEM key)
GitHub repo name (need owner/org too)
Branch reference
Workflow file name
Workflow inputs

Additional inputs you'll need:

GitHub App ID (numeric ID, not the name)
GitHub App Installation ID (the installation ID for your org/repo)
Repository owner/organization (or include it in repo name as owner/repo)


Key notes:

Installation ID is required and different from App ID — you find it in your GitHub App's installation settings or via the API
The workflow file must have workflow_dispatch trigger configured
Returns 204 on success (GitHub's standard response for dispatch)
The PEM key can be stored as plain text or as JSON with a private_key field


                            
