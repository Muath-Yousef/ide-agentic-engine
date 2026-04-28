# SOC Root Project Setup

This project uses a master initialization script to configure the entire development environment, AI agents, and secure credential storage.

## Prerequisites

- **Linux** (Ubuntu/Debian recommended)
- **GPG** installed (`sudo apt install gnupg`)
- **Node.js/npm** installed
- **Python 3.10+** installed
- **jq** installed (`sudo apt install jq`)

## First-Time Setup

1. **Configure Project Specification**:
   Edit `PROJECT_SPEC.md` (or copy from `PROJECT_SPEC.template.md`) to define your project needs.

2. **Prepare Secrets**:
   Copy `.env.template` to `.env` and fill in the required API keys and a `GPG_PASSPHRASE`.
   ```bash
   cp .env.template .env
   # Fill in .env
   ```

3. **Run Initialization**:
   ```bash
   chmod +x init_project.sh
   ./init_project.sh
   ```
   *Note: During the first run, you will be prompted to enter the GPG passphrase if not provided in .env.*

4. **Verify Setup**:
   The script will automatically run a verification suite at the end.

## Subsequent Runs

On subsequent runs, the script will:
- Resume from the saved state in `.project_state.json`.
- Decrypt credentials using the stored GPG file.
- Ensure all dependencies and configurations are up to date.

## Advanced Usage

### Modifying AI Skills
Edit the `ai_configuration` section in `PROJECT_SPEC.md` and re-run `./init_project.sh`.

### Manual Secret Update
If you need to update secrets, delete `.env.gpg`, update `.env`, and re-run the script.
