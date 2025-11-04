# GitHub Actions Integration with MCP Prompts

A powerful integration between GitHub Actions and MCP (Model Control Protocol) that enables intelligent CI/CD workflow automation and monitoring.

![screenshot 1](static\Screenshot1.png)
![screenshot 2](static\Screenshot2.png)

## Features

- **GitHub Webhook Integration**: Capture and process GitHub Actions workflow events in real-time
- **CI/CD Analytics**: Get insights into your CI/CD pipeline performance
- **PR Automation**: Automate PR-related tasks with AI-powered suggestions
- **Template Management**: Manage and suggest PR templates based on changes
- **Deployment Summaries**: Generate deployment reports for team communication

## Prerequisites

- Python 3.12+
- `uv` package manager (for dependency management)
- GitHub repository with GitHub Actions enabled
- (Optional) Cloudflare Tunnel for public webhook endpoints

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd github-mcp
   ```

2. Install dependencies:
   ```bash
   uv sync
   ```

## Usage

### Starting the Services

1. a. **Start the MCP Server** (optional):
   ```bash
   uv run server.py
   ```

2. b. **Gemini Configuration for MCP server integrationin Gemini CLI**

    Add to MCP server to gemini:
    ```bash
    fastmcp install gemini-cli server.py

    # or manually add/update gemini settings/settings.json to .gemini folder in C:\Users\<username>\.gemini
    ```

2. **Start the Webhook Server** (in another terminal):
   ```bash
   python webhook_server.py
   ```

3. **Configure GitHub Webhook**:
   - Go to your GitHub repository settings
   - Navigate to Webhooks > Add webhook
   - Set Payload URL to `http://your-server:8080/webhook/github`
   - Set Content type to `application/json`
   - Select events: `workflow_run`
   - Add secret (optional but recommended)

## Available Tools

- `analyze_file_changes`: Get detailed analysis of file changes in a PR
- `get_pr_templates`: List available PR templates
- `suggest_template`: Get AI-suggested PR template based on changes
- `get_recent_actions_events`: View recent GitHub Actions events
- `analyze_ci_results`: Get insights from CI/CD pipeline results
- `create_deployment_summary`: Generate deployment summaries
- `troubleshoot_workflow_failure`: Get help with failing workflows

## Testing

See [manual_test.md](manual_test.md) for detailed testing instructions and example webhook payloads.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a new Pull Request

## Support

For issues and feature requests, please use the [issue tracker](https://github.com/your-org/github-mcp/issues).