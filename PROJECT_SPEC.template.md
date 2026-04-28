# Project Specification: [Project Name]

project:
  name: "SOC Root"
  type: "cybersecurity_platform"
  tech_stack: ["Python", "Docker", "Wazuh", "Cloudflare"]
  
environment:
  python_version: "3.10+"
  required_tools:
    - docker
    - ansible
    - nmap
    - nuclei
  
ai_configuration:
  primary_llm: "gemini-2.0-flash"
  fallback_llm: "deepseek-chat"
  
  skills_to_build:
    - name: "Evidence Chain Verifier"
      path: ".gemini/antigravity/skills/evidence_verification.md"
      template: "security_audit_expert"
    
    - name: "NCA Compliance Mapper"
      path: ".gemini/antigravity/skills/nca_mapping.md"
      template: "compliance_expert"
  
  mcp_servers:
    - name: "filesystem"
      package: "@modelcontextprotocol/server-filesystem"
      args: ["/media/kyrie/SOCROOT"]
    
    - name: "custom-evidence-store"
      type: "custom"
      path: "./mcp-servers/evidence-store/server.js"
  
  agents:
    - name: "security_analyzer"
      role: "threat_detection"
      tools: ["wazuh", "nuclei", "nmap"]
    
    - name: "compliance_reporter"
      role: "report_generation"
      tools: ["fpdf2", "arabic-reshaper"]

secrets:
  required:
    - GEMINI_API_KEY
    - CLOUDFLARE_API_TOKEN
    - CLOUDFLARE_ZONE_ID
    - TELEGRAM_BOT_TOKEN
    - SMTP_PASSWORD
    - SSH_PRIVATE_KEY
  
  storage_method: "encrypted_env"

automation:
  workflows:
    - name: "client_onboarding"
      trigger: "webhook"
      file: "n8n_workflows/onboarding.json"
  
  cron_jobs:
    - schedule: "0 2 * * 1"
      command: "python3 scheduler.py --run-due"
      description: "Weekly scans"

system_modifications:
  antigravity_core:
    - file: ".gemini/antigravity/knowledge/project_context.md"
      action: "create"
      content_from: "docs/PROJECT_CONTEXT.md"
    
    - file: ".gemini/antigravity/settings.json"
      action: "merge"
      settings:
        auto_commit: true
        max_parallel_agents: 5
