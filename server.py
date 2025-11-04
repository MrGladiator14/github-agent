#!/usr/bin/env python3
"""
GitHub Actions Integration with MCP Prompts
Handles webhooks and CI/CD workflows for PR agent.
"""

import json
import os
import subprocess
from typing import Optional
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from logger import setup_logger

logger = setup_logger(__name__)


os.environ
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
mcp = FastMCP("pr-agent-actions")

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATES_DIR = SCRIPT_DIR / "templates"
EVENTS_FILE = SCRIPT_DIR / "github_events.json"

# logger = get_logger(__name__)

logger.debug(f"Script directory: {SCRIPT_DIR}")
logger.debug(f"Templates directory: {TEMPLATES_DIR}")
logger.debug(f"Templates directory exists: {TEMPLATES_DIR.exists()}")
if TEMPLATES_DIR.exists():
    logger.debug(f"Found templates: {list(TEMPLATES_DIR.glob('*.md'))}")

DEFAULT_TEMPLATES = {
    "bug.md": "Bug Fix",
    "feature.md": "Feature",
    "docs.md": "Documentation",
    "refactor.md": "Refactor",
    "test.md": "Test",
    "performance.md": "Performance",
    "security.md": "Security"
}

TYPE_MAPPING = {
    "bug": "bug.md",
    "fix": "bug.md",
    "feature": "feature.md",
    "enhancement": "feature.md",
    "docs": "docs.md",
    "documentation": "docs.md",
    "refactor": "refactor.md",
    "cleanup": "refactor.md",
    "test": "test.md",
    "testing": "test.md",
    "performance": "performance.md",
    "optimization": "performance.md",
    "security": "security.md"
}



@mcp.tool()
async def analyze_file_changes(
    base_branch: str = "master",
    include_diff: bool = False,
    max_diff_lines: int = 5000,
    working_directory: Optional[str] = None,
    command_timeout: int = 180  # Increased default timeout from 10 to 30 seconds
) -> str:
    """Get the full diff and list of changed files in the current git repository.
    
    Args:
        base_branch: Base branch to compare against (default: main)
        include_diff: Include the full diff content (default: true)
        max_diff_lines: Maximum number of diff lines to include (default: 500)
        working_directory: Directory to run git commands in (default: current directory)
    """
    logger.debug(f"Starting analyze_file_changes with base_branch={base_branch}, include_diff={include_diff}, max_diff_lines={max_diff_lines}")
    
    try:
        if working_directory is None:
            try:
                logger.debug("No working directory provided, attempting to get it from MCP context")
                context = mcp.get_context()
                roots_result = await context.session.list_roots()
                # Get the first root - Claude Code sets this to the CWD
                root = roots_result.roots[0]
                # FileUrl object has a .path property that gives us the path directly
                working_directory = root.uri.path
                logger.debug(f"Got working directory from MCP context: {working_directory}")
            except Exception as e:
                logger.warning(f"Could not get working directory from MCP context: {e}", exc_info=True)
        
        cwd = working_directory if working_directory else os.getcwd()
        logger.debug(f"Using working directory: {cwd}")
        
        # Get changed files with progress indicator
        logger.debug("Getting list of changed files...")
        
        # First, get the list of changed files (faster than getting full diff)
        try:
            logger.debug("Getting list of modified files...")
            files_result = subprocess.run(
                ["git", "diff", "--name-only", f"{base_branch}..HEAD"],
                capture_output=True,
                text=True,
                check=True,
                cwd=cwd,
                timeout=command_timeout  # Should be fast for just file names
            )
            changed_files = [f.strip() for f in files_result.stdout.splitlines() if f.strip()]
            logger.debug(f"Found {len(changed_files)} changed files")
            
            # If we need the status, get it separately
            if changed_files:
                logger.debug("Getting status of changed files...")
                status_result = subprocess.run(
                    ["git", "diff", "--name-status", "--no-renames", f"{base_branch}..HEAD", "--"] + changed_files[:100],  # Limit to first 100 files if many
                    capture_output=True,
                    text=True,
                    check=True,
                    cwd=cwd,
                    timeout=command_timeout
                )
                files_result.stdout = status_result.stdout
            else:
                files_result.stdout = ""
                
        except subprocess.CalledProcessError as e:
            logger.error(f"Git command failed: {e.stderr}")
            files_result = type('', (), {'stdout': '', 'stderr': e.stderr})()
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            files_result = type('', (), {'stdout': '', 'stderr': str(e)})()
        logger.debug(f"Got {len(files_result.stdout.splitlines())} changed files")
        
        # Get diff statistics
        logger.debug("Getting diff statistics...")
        stat_result = subprocess.run(
            ["git", "diff", "--stat", f"{base_branch}...HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd,
            timeout=command_timeout
        )
        logger.debug(f"Diff statistics: {stat_result.stdout.strip() or 'No changes'}")
        
        diff_content = ""
        truncated = False
        
        if include_diff:
            logger.debug("Getting full diff content...")
            diff_result = subprocess.run(
                ["git", "diff", f"{base_branch}...HEAD"],
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=command_timeout
            )
            diff_lines = diff_result.stdout.split('\n')
            logger.debug(f"Got {len(diff_lines)} lines of diff")
            
            if len(diff_lines) > max_diff_lines:
                logger.debug(f"Truncating diff from {len(diff_lines)} to {max_diff_lines} lines")
                diff_content = '\n'.join(diff_lines[:max_diff_lines])
                diff_content += f"\n\n... Output truncated. Showing {max_diff_lines} of {len(diff_lines)} lines ..."
                diff_content += "\n... Use max_diff_lines parameter to see more ..."
                truncated = True
            else:
                diff_content = diff_result.stdout
        else:
            logger.debug("Skipping full diff content as include_diff is False")
        
        # Get commit history
        logger.debug("Getting commit history...")
        commits_result = subprocess.run(
            ["git", "log", "--oneline", f"{base_branch}..HEAD"],
            capture_output=True,
            text=True,
            cwd=cwd
        )
        commits = commits_result.stdout.splitlines()
        logger.debug(f"Found {len(commits)} commits in the current branch")
        
        analysis = {
            "base_branch": base_branch,
            "files_changed": files_result.stdout,
            "statistics": stat_result.stdout,
            "commits": commits_result.stdout,
            "diff": diff_content if include_diff else "Diff not included (set include_diff=true to see full diff)",
            "truncated": truncated,
            "total_diff_lines": len(diff_lines) if include_diff else 0
        }
        
        logger.debug(f"Analysis complete. Returning {len(analysis)} items in the response")
        return json.dumps(analysis, indent=2)
        
    except subprocess.TimeoutExpired as e:
        error_msg = f"Git command timed out after {e.timeout} seconds. The repository might be too large or the diff too complex."
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "error": "Git command timeout",
            "details": error_msg,
            "solution": "Try with a higher timeout value using the 'command_timeout' parameter"
        })
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Git command failed with exit code {e.returncode}: {e.stderr or e.stdout or 'No output'}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "error": "Git command execution failed",
            "details": error_msg,
            "command": " ".join(e.cmd) if hasattr(e, 'cmd') else "unknown"
        })
        
    except FileNotFoundError as e:
        error_msg = "Git command not found. Make sure Git is installed and in your PATH."
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "error": "Git not found",
            "details": error_msg,
            "solution": "Please install Git and ensure it's available in your system PATH"
        })
        
    except json.JSONDecodeError as e:
        error_msg = f"Failed to serialize the response: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "error": "Serialization error",
            "details": error_msg
        })
        
    except PermissionError as e:
        error_msg = f"Permission denied when accessing {e.filename if hasattr(e, 'filename') else 'the specified directory'}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "error": "Permission denied",
            "details": error_msg,
            "solution": "Check file permissions and ensure the application has the necessary access rights"
        })
        
    except Exception as e:
        error_type = type(e).__name__
        error_msg = f"Unexpected {error_type} in analyze_file_changes: {str(e)}"
        logger.error(error_msg, exc_info=True)
        return json.dumps({
            "error": f"Unexpected {error_type}",
            "details": str(e),
            "context": {
                "base_branch": base_branch,
                "working_directory": working_directory or os.getcwd(),
                "include_diff": include_diff,
                "max_diff_lines": max_diff_lines
            }
        })


@mcp.tool()
async def get_pr_templates() -> str:
    """List available PR templates with their content."""
    try:
        logger.debug(f"\n=== get_pr_templates called ===")
        logger.debug(f"Current working directory: {Path.cwd()}")
        logger.debug(f"Script file location: {Path(__file__).resolve()}")
        logger.debug(f"Script directory: {SCRIPT_DIR}")
        logger.debug(f"Templates directory: {TEMPLATES_DIR}")
        logger.debug(f"Templates directory exists: {TEMPLATES_DIR.exists()}")
        
        if not TEMPLATES_DIR.exists():
            # Try to create it if it doesn't exist
            try:
                TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Created templates directory: {TEMPLATES_DIR}")
            except Exception as mkdir_error:
                return json.dumps({
                    "error": f"Templates directory not found and could not be created: {TEMPLATES_DIR}",
                    "mkdir_error": str(mkdir_error),
                    "current_working_directory": str(Path.cwd()),
                    "script_location": str(Path(__file__).resolve()),
                    "script_parent": str(Path(__file__).resolve().parent)
                }, indent=2)
            
        templates = []
        for filename, template_type in DEFAULT_TEMPLATES.items():
            template_path = TEMPLATES_DIR / filename
            logger.debug(f"\nChecking template: {filename}")
            logger.debug(f"Full path: {template_path}")
            logger.debug(f"Exists: {template_path.exists()}")
            
            if not template_path.exists():
                logger.warning(f"Warning: Template file not found: {template_path}")
                continue
                
            try:
                content = template_path.read_text(encoding='utf-8')
                templates.append({
                    "filename": filename,
                    "type": template_type,
                    "content": content
                })
                logger.debug(f"Successfully loaded: {filename}")
            except Exception as e:
                logger.error(f"Error reading {filename}: {str(e)}")
                continue
        
        if not templates:
            available_files = list(TEMPLATES_DIR.glob('*'))
            return json.dumps({
                "error": "No templates could be loaded",
                "available_files": [str(f) for f in available_files],
                "templates_dir": str(TEMPLATES_DIR),
                "templates_dir_exists": TEMPLATES_DIR.exists(),
                "hint": "Please create template files (.md) in the templates directory"
            }, indent=2)
            
        return json.dumps({
            "templates": templates,
            "templates_dir": str(TEMPLATES_DIR)
        }, indent=2)
        
    except Exception as e:
        import traceback
        error_details = {
            "error": f"Unexpected error: {str(e)}",
            "traceback": traceback.format_exc(),
            "script_file": str(Path(__file__).resolve()),
            "script_parent": str(Path(__file__).resolve().parent),
            "templates_dir": str(TEMPLATES_DIR),
            "templates_dir_exists": TEMPLATES_DIR.exists(),
            "current_working_directory": str(Path.cwd())
        }
        logger.error(f"Error in get_pr_templates: {error_details}")
        return json.dumps(error_details, indent=2)


@mcp.tool()
async def suggest_template(changes_summary: str, change_type: str) -> str:
    """Let Claude analyze the changes and suggest the most appropriate PR template.
    
    Args:
        changes_summary: Your analysis of what the changes do
        change_type: The type of change you've identified (bug, feature, docs, refactor, test, etc.)
    """
    
    templates_response = await get_pr_templates()
    templates_data = json.loads(templates_response)
    
    if "error" in templates_data:
        return templates_response
    
    templates = templates_data.get("templates", [])
    
    if not templates:
        return json.dumps({
            "error": "No templates available",
            "suggestion": "Please ensure template files exist in the templates directory"
        }, indent=2)
    
    template_file = TYPE_MAPPING.get(change_type.lower(), "feature.md")
    selected_template = next(
        (t for t in templates if t["filename"] == template_file),
        templates[0]  # Default to first template if no match
    )
    
    suggestion = {
        "recommended_template": selected_template,
        "reasoning": f"Based on your analysis: '{changes_summary}', this appears to be a {change_type} change.",
        "template_content": selected_template["content"],
        "usage_hint": "Claude can help you fill out this template based on the specific changes in your PR."
    }
    
    return json.dumps(suggestion, indent=2)



@mcp.tool()
async def get_recent_actions_events(limit: int = 3) -> str:
    """Get recent GitHub Actions events received via webhook.
    
    Args:
        limit: Maximum number of events to return (default: 10)
    """
    if not EVENTS_FILE.exists():
        return json.dumps([])
    
    with open(EVENTS_FILE, 'r') as f:
        events = json.load(f)
    
    # Return most recent events
    recent = events[-limit:]
    return json.dumps(recent, indent=2)


@mcp.tool()
async def get_workflow_status(workflow_name: Optional[str] = None) -> str:
    """Get the current status of GitHub Actions workflows.
    
    Args:
        workflow_name: Optional specific workflow name to filter by
    """
    if not EVENTS_FILE.exists():
        return json.dumps({"message": "No GitHub Actions events received yet"})
    
    with open(EVENTS_FILE, 'r') as f:
        events = json.load(f)
    
    if not events:
        return json.dumps({"message": "No GitHub Actions events received yet"})
    
    workflow_events = [
        e for e in events 
        if e.get("workflow_run") is not None
    ]
    
    if workflow_name:
        workflow_events = [
            e for e in workflow_events
            if e["workflow_run"].get("name") == workflow_name
        ]
    
    workflows = {}
    for event in workflow_events:
        run = event["workflow_run"]
        name = run["name"]
        if name not in workflows or run["updated_at"] > workflows[name]["updated_at"]:
            workflows[name] = {
                "name": name,
                "status": run["status"],
                "conclusion": run.get("conclusion"),
                "run_number": run["run_number"],
                "updated_at": run["updated_at"],
                "html_url": run["html_url"]
            }
    
    return json.dumps(list(workflows.values()), indent=2)



@mcp.prompt()
async def analyze_ci_results():
    """Analyze recent CI/CD results and provide insights."""
    return """Please analyze the recent CI/CD results from GitHub Actions:

1. First, call get_recent_actions_events() to fetch the latest CI/CD events
2. Then call get_workflow_status() to check current workflow states
3. Identify any failures or issues that need attention
4. Provide actionable next steps based on the results

Format your response as:
## CI/CD Status Summary
- **Overall Health**: [Good/Warning/Critical]
- **Failed Workflows**: [List any failures with links]
- **Successful Workflows**: [List recent successes]
- **Recommendations**: [Specific actions to take]
- **Trends**: [Any patterns you notice]"""


@mcp.prompt()
async def create_deployment_summary():
    """Generate a deployment summary for team communication."""
    return """Create a deployment summary for team communication:

1. Check workflow status with get_workflow_status()
2. Look specifically for deployment-related workflows
3. Note the deployment outcome, timing, and any issues

Format as a concise message suitable for Slack:

🚀 **Deployment Update**
- **Status**: [✅ Success / ❌ Failed / ⏳ In Progress]
- **Environment**: [Production/Staging/Dev]
- **Version/Commit**: [If available from workflow data]
- **Duration**: [If available]
- **Key Changes**: [Brief summary if available]
- **Issues**: [Any problems encountered]
- **Next Steps**: [Required actions if failed]

Keep it brief but informative for team awareness."""


@mcp.prompt()
async def generate_pr_status_report():
    """Generate a comprehensive PR status report including CI/CD results."""
    return """Generate a comprehensive PR status report:

1. Use analyze_file_changes() to understand what changed
2. Use get_workflow_status() to check CI/CD status
3. Use suggest_template() to recommend the appropriate PR template
4. Combine all information into a cohesive report

Create a detailed report with:

## 📋 PR Status Report

### 📝 Code Changes
- **Files Modified**: [Count by type - .py, .js, etc.]
- **Change Type**: [Feature/Bug/Refactor/etc.]
- **Impact Assessment**: [High/Medium/Low with reasoning]
- **Key Changes**: [Bullet points of main modifications]

### 🔄 CI/CD Status
- **All Checks**: [✅ Passing / ❌ Failing / ⏳ Running]
- **Test Results**: [Pass rate, failed tests if any]
- **Build Status**: [Success/Failed with details]
- **Code Quality**: [Linting, coverage if available]

### 📌 Recommendations
- **PR Template**: [Suggested template and why]
- **Next Steps**: [What needs to happen before merge]
- **Reviewers**: [Suggested reviewers based on files changed]

### ⚠️ Risks & Considerations
- [Any deployment risks]
- [Breaking changes]
- [Dependencies affected]"""


@mcp.prompt()
async def troubleshoot_workflow_failure():
    """Help troubleshoot a failing GitHub Actions workflow."""
    return """Help troubleshoot failing GitHub Actions workflows:

1. Use get_recent_actions_events() to find recent failures
2. Use get_workflow_status() to see which workflows are failing
3. Analyze the failure patterns and timing
4. Provide systematic troubleshooting steps

Structure your response as:

## 🔧 Workflow Troubleshooting Guide

### ❌ Failed Workflow Details
- **Workflow Name**: [Name of failing workflow]
- **Failure Type**: [Test/Build/Deploy/Lint]
- **First Failed**: [When did it start failing]
- **Failure Rate**: [Intermittent or consistent]

### 🔍 Diagnostic Information
- **Error Patterns**: [Common error messages or symptoms]
- **Recent Changes**: [What changed before failures started]
- **Dependencies**: [External services or resources involved]

### 💡 Possible Causes (ordered by likelihood)
1. **[Most Likely]**: [Description and why]
2. **[Likely]**: [Description and why]
3. **[Possible]**: [Description and why]

### ✅ Suggested Fixes
**Immediate Actions:**
- [ ] [Quick fix to try first]
- [ ] [Second quick fix]

**Investigation Steps:**
- [ ] [How to gather more info]
- [ ] [Logs or data to check]

**Long-term Solutions:**
- [ ] [Preventive measure]
- [ ] [Process improvement]

### 📚 Resources
- [Relevant documentation links]
- [Similar issues or solutions]"""


if __name__ == "__main__":
    # logger = get_logger(__name__)
    logger.info("Starting PR Agent MCP server...")
    mcp.run(transport='stdio')
    logger.info("To receive GitHub webhooks, run the webhook server separately:")
    logger.info("  $ python webhook_server.py")
