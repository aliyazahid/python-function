import json
import time
import jwt
import requests
import boto3
from typing import Any


def get_github_app_token(
    app_id: str,
    installation_id: str,
    private_key_pem: str
) -> str:
    """Generate an installation access token for a GitHub App."""
    # Create JWT for GitHub App authentication
    now = int(time.time())
    payload = {
        "iat": now - 60,  # Issued 60 seconds ago to account for clock drift
        "exp": now + (10 * 60),  # Expires in 10 minutes
        "iss": app_id
    }
    
    jwt_token = jwt.encode(payload, private_key_pem, algorithm="RS256")
    
    # Exchange JWT for installation access token
    headers = {
        "Authorization": f"Bearer {jwt_token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    
    response = requests.post(
        f"https://api.github.com/app/installations/{installation_id}/access_tokens",
        headers=headers
    )
    response.raise_for_status()
    
    return response.json()["token"]


def trigger_github_workflow(
    app_id: str,
    installation_id: str,
    secret_name: str,
    repo_owner: str,
    repo_name: str,
    workflow_file: str,
    ref: str,
    workflow_inputs: dict[str, Any] | None = None,
    region_name: str = "us-east-1"
) -> dict[str, Any]:
    """
    Trigger a GitHub Actions workflow using GitHub App credentials.
    
    Args:
        app_id: GitHub App ID (numeric string)
        installation_id: GitHub App Installation ID for the repo/org
        secret_name: AWS Secrets Manager secret name containing the PEM key
        repo_owner: Repository owner (organization or username)
        repo_name: Repository name
        workflow_file: Workflow filename (e.g., "deploy.yml")
        ref: Branch or tag reference (e.g., "main", "refs/heads/main")
        workflow_inputs: Optional dictionary of workflow inputs
        region_name: AWS region for Secrets Manager (default: us-east-1)
    
    Returns:
        dict with 'success' (bool), 'status_code' (int), and 'message' (str)
    """
    try:
        # Retrieve PEM key from Secrets Manager
        secrets_client = boto3.client("secretsmanager", region_name=region_name)
        secret_response = secrets_client.get_secret_value(SecretId=secret_name)
        
        # Handle both string and binary secrets
        if "SecretString" in secret_response:
            private_key_pem = secret_response["SecretString"]
            # If stored as JSON, extract the key
            try:
                secret_json = json.loads(private_key_pem)
                private_key_pem = secret_json.get("private_key", private_key_pem)
            except json.JSONDecodeError:
                pass  # Already a plain PEM string
        else:
            private_key_pem = secret_response["SecretBinary"].decode("utf-8")
        
        # Get installation access token
        access_token = get_github_app_token(app_id, installation_id, private_key_pem)
        
        # Trigger the workflow
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        
        payload = {"ref": ref}
        if workflow_inputs:
            payload["inputs"] = workflow_inputs
        
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/actions/workflows/{workflow_file}/dispatches"
        
        response = requests.post(url, headers=headers, json=payload)
        
        # 204 No Content = success for workflow dispatch
        if response.status_code == 204:
            return {
                "success": True,
                "status_code": 204,
                "message": f"Workflow '{workflow_file}' triggered successfully on ref '{ref}'"
            }
        else:
            error_detail = response.json() if response.text else {}
            return {
                "success": False,
                "status_code": response.status_code,
                "message": error_detail.get("message", response.text),
                "errors": error_detail.get("errors", [])
            }
            
    except requests.exceptions.HTTPError as e:
        return {
            "success": False,
            "status_code": e.response.status_code if e.response else 500,
            "message": str(e)
        }
    except Exception as e:
        return {
            "success": False,
            "status_code": 500,
            "message": f"Unexpected error: {str(e)}"
        }


# Lambda handler wrapper
def lambda_handler(event: dict, context) -> dict:
    """AWS Lambda handler."""
    return trigger_github_workflow(
        app_id=event["app_id"],
        installation_id=event["installation_id"],
        secret_name=event["secret_name"],
        repo_owner=event["repo_owner"],
        repo_name=event["repo_name"],
        workflow_file=event["workflow_file"],
        ref=event["ref"],
        workflow_inputs=event.get("workflow_inputs"),
        region_name=event.get("region_name", "us-east-1")
    )
```

**Dependencies for your Lambda (requirements.txt):**
```
PyJWT>=2.0.0
requests>=2.28.0
cryptography>=3.4.0
