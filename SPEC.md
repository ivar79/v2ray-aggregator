# Telegram V2Ray Configuration Aggregator
## SPEC.md — Devin Implementation Specification

> **Status:** Initial specification  
> **Purpose:** Single source of truth for implementation  
> **Primary development environment:** VS Code + Git Bash  
> **Target:** Production-oriented, modular Python application

---

## 1. Executive Summary

Build a production-ready Telegram V2Ray configuration aggregator.

The system must:

1. Monitor a configurable list of Telegram source channels for which the operator has permission to collect and republish content.
2. Read historical and new messages.
3. Extract supported proxy/V2Ray configuration URIs.
4. Normalize configurations into a canonical representation.
5. Detect and remove duplicates intelligently.
6. Perform safe structural validation.
7. Apply the operator's own Telegram channel branding to public output.
8. Publish generated files automatically to a configured GitHub repository.
9. Provide a Telegram administration bot.
10. Support scheduled and manual collection.
11. Preserve internal source metadata for traceability while keeping source-channel details out of public output by default.
12. Be modular so additional protocols and output formats can be added later.

The operator has permission to collect and republish content from the configured source channels.

---

# 2. Critical Instruction for Devin

Treat this file as the project's primary specification.

Before implementing the complete system:

1. Inspect the repository.
2. Review this specification.
3. Identify ambiguities, technical risks, and Telegram/GitHub API constraints.
4. Propose the final architecture.
5. Do **not** immediately implement the entire project.
6. First provide an implementation plan and list of important decisions.
7. After approval, implement in phases.
8. Do not claim a feature works unless it has actually been tested.

Do not make unrelated changes to an existing repository.

If this is a new repository, create the project cleanly from scratch.

---

# 3. High-Level Architecture

Do not make the Telegram Bot itself responsible for collecting channel messages.

Use separate components:

### A. Telegram Client / Collector

Responsible for:

- Telegram authentication
- Reading source channels
- Historical collection
- Monitoring new messages
- Fetching message text/captions/documents where practical
- Sending extracted messages/configurations to the processing pipeline

Preferred library:

- Telethon

### B. Telegram Admin Bot

Responsible for:

- Managing source channels
- Starting collection manually
- Showing status
- Showing statistics
- Showing errors
- Showing GitHub publishing status
- Managing authorized administrators

Preferred library:

- aiogram or python-telegram-bot

### C. Processing Pipeline

```text
Telegram Channels
       |
       v
Telegram Client / Collector
       |
       v
Message Parser
       |
       v
Configuration Extractor
       |
       v
Normalizer
       |
       v
Deduplication Engine
       |
       v
Structural Validator
       |
       v
Database
       |
       v
Output Generator
       |
       v
GitHub Publisher
```

### D. Admin Control

```text
Telegram Admin Bot
       |
       v
Application Service Layer
       |
       +---- Collector
       +---- Database
       +---- Publisher
       +---- Scheduler
```

---

# 4. Recommended Technology Stack

Use:

- Python 3.11+
- Telethon
- aiogram or python-telegram-bot
- SQLite initially
- SQLAlchemy or a clean repository/database abstraction
- Pydantic
- python-dotenv
- pytest
- GitPython OR subprocess-based Git integration
- GitHub API where appropriate

Keep dependencies reasonably minimal.

The project must run from:

- VS Code
- Git Bash

Do not require PowerShell-specific commands.

---

# 5. Project Structure

Use a modular structure similar to:

```text
v2ray-aggregator/
│
├── app/
│   ├── bot/
│   │   ├── handlers.py
│   │   └── bot.py
│   │
│   ├── collector/
│   │   ├── telegram_client.py
│   │   └── collector.py
│   │
│   ├── parser/
│   │   ├── base.py
│   │   ├── vmess.py
│   │   ├── vless.py
│   │   ├── trojan.py
│   │   ├── shadowsocks.py
│   │   └── hysteria.py
│   │
│   ├── processor/
│   │   ├── extractor.py
│   │   ├── normalizer.py
│   │   ├── deduplicator.py
│   │   └── validator.py
│   │
│   ├── database/
│   │   ├── models.py
│   │   ├── repository.py
│   │   └── database.py
│   │
│   ├── github/
│   │   └── publisher.py
│   │
│   ├── scheduler/
│   │   └── scheduler.py
│   │
│   ├── config.py
│   ├── logging_config.py
│   └── main.py
│
├── tests/
│   ├── fixtures/
│   ├── test_extractors.py
│   ├── test_normalization.py
│   ├── test_deduplication.py
│   ├── test_database.py
│   └── test_output.py
│
├── configs/
│   └── .gitkeep
│
├── .env.example
├── .gitignore
├── README.md
├── SETUP.md
├── TROUBLESHOOTING.md
├── requirements.txt
├── SPEC.md
└── main.py
```

The exact structure may be improved if there is a strong technical reason. Keep responsibilities separated.

---

# 6. Supported Protocols

Initial support:

- VMess
- VLESS
- Trojan
- Shadowsocks
- Hysteria
- Hysteria2

The parser architecture must allow future protocols to be added without rewriting the entire pipeline.

A single Telegram message may contain:

- one configuration
- multiple configurations
- text + configurations
- code blocks
- URLs
- mixed protocols

The extractor must return all supported configurations found in a message.

---

# 7. Message Extraction

Search relevant content from:

- message text
- captions
- text/code blocks
- message entities where appropriate
- attached text files/documents where practical

Recognize protocol prefixes such as:

```text
vmess://
vless://
trojan://
ss://
hysteria://
hysteria2://
```

Do not blindly treat arbitrary strings beginning with these prefixes as valid.

Perform basic structural checks.

One malformed configuration must not terminate message processing.

---

# 8. Normalization

Normalization is a core requirement.

The same logical configuration can appear with different formatting.

Pipeline:

```text
Raw configuration
       |
       v
Decode
       |
       v
Parse
       |
       v
Normalize fields
       |
       v
Canonical representation
       |
       v
SHA-256 hash
```

Normalization should account for:

- URL encoding
- unnecessary whitespace
- parameter ordering
- equivalent representations
- fragment/name differences where appropriate
- JSON field ordering for VMess-style JSON representations
- other protocol-specific formatting differences

Do not modify connection-critical values.

Do not normalize in a way that changes the actual connection semantics.

The objective is:

```text
Same logical configuration
+
Different textual formatting
=
Same canonical hash
```

---

# 9. Deduplication

Implement at least three levels.

### 9.1 Exact duplicate

Identical raw configuration.

### 9.2 Normalized duplicate

Different formatting but identical canonical configuration.

### 9.3 Database duplicate

A configuration whose canonical hash already exists must not be inserted as a new public configuration.

Use:

```text
SHA-256(canonical_representation)
```

as the primary deduplication fingerprint.

Avoid using only raw string equality.

---

# 10. Source Metadata

Retain source information internally.

For every discovered configuration, retain where possible:

- source channel ID
- source channel username
- source message ID
- first seen timestamp
- last seen timestamp

This information is for:

- traceability
- debugging
- deduplication
- auditing
- future analytics

By default, source channel information must NOT appear in public GitHub files.

Public source disclosure must be configurable and disabled by default.

---

# 11. Database

Use SQLite initially.

Recommended tables:

## channels

Fields:

- id
- telegram_id
- username
- title
- enabled
- last_message_id
- created_at
- updated_at

## configs

Fields:

- id
- protocol
- raw_config
- normalized_config
- config_hash
- source_channel_id
- source_message_id
- first_seen_at
- last_seen_at
- is_valid
- is_active

## collection_runs

Fields:

- id
- started_at
- finished_at
- status
- messages_scanned
- configs_found
- configs_added
- duplicates_removed
- invalid_configs
- errors

Add indexes for:

- config_hash
- protocol
- source_channel_id
- source_message_id

Use proper transactions.

Do not lose collected data because GitHub publishing fails.

---

# 12. Telegram Collector

The collector must support:

### Initial historical synchronization

Configurable message limit:

```text
FIRST_RUN_MESSAGE_LIMIT=5000
```

The initial run should:

1. Read historical messages.
2. Extract configurations.
3. Normalize.
4. Deduplicate.
5. Store.
6. Generate output.
7. Publish if enabled.

### Incremental synchronization

After initial synchronization:

- process only messages newer than the stored last message ID
- update last processed message ID
- resume correctly after interruption

Do not repeatedly scan the entire channel on every scheduled run.

---

# 13. Scheduling

Default collection interval:

```text
COLLECTION_INTERVAL_MINUTES=30
```

Make it configurable.

Requirements:

- scheduled collection
- manual collection
- no overlapping collection jobs
- graceful shutdown
- retry handling

Use an application-level lock/mutex/job state.

---

# 14. Telegram Authentication

The collector uses a Telegram client account, not only the Bot API.

On first run:

1. Ask for phone number.
2. Request Telegram login code.
3. Handle 2FA when enabled.
4. Save Telethon session securely.
5. Reuse the session on future runs.

Never commit the session file.

Document the authentication process in `SETUP.md`.

---

# 15. Telegram Admin Bot

Implement at least:

```text
/start
/help
/status
/channels
/addchannel
/removechannel
/run
/lastupdate
/github
/stats
/errors
```

Examples:

```text
/addchannel @example
```

```text
/removechannel @example
```

```text
/run
```

The `/run` command triggers an immediate collection cycle.

Example result:

```text
Collection completed.

Messages scanned: 1,245
Configurations found: 382
New configurations: 97
Duplicates removed: 285
Invalid configurations: 12
Published to GitHub: Yes
```

---

# 16. Admin Authorization

Only authorized Telegram user IDs may use administration commands.

Environment variable:

```text
ADMIN_USER_IDS=123456789,987654321
```

Unauthorized users must not be able to:

- add channels
- remove channels
- run collection
- view sensitive system status
- trigger GitHub publishing

---

# 17. Branding

Public output must use the operator's own Telegram channel branding.

Environment/configuration:

```text
CHANNEL_NAME="MY CHANNEL NAME"
CHANNEL_USERNAME="@my_channel"
CHANNEL_ID="123456789"
```

The branding must be configurable.

Example human-readable header:

```text
==================================================
MY CHANNEL NAME
@my_channel

Updated automatically
==================================================
```

Do not expose source channel names publicly by default.

Important compatibility requirement:

Machine-readable files should remain one-configuration-per-line.

If a branding header would break client compatibility, create:

1. a clean machine-readable file
2. a separate branded human-readable file

Do not insert comments/headers into files where clients expect every line to be a configuration.

---

# 18. GitHub Repository Structure

Recommended public repository:

```text
README.md

configs/
├── all.txt
├── vmess.txt
├── vless.txt
├── trojan.txt
├── shadowsocks.txt
└── hysteria.txt

metadata/
└── stats.json
```

The structure may be improved if there is a better design.

Requirements:

- one configuration per line in machine-readable files
- protocol-specific files
- combined file
- generated statistics
- professional README
- operator branding

Do not expose private source-channel metadata.

---

# 19. GitHub Publishing

Do not create one commit per configuration.

Instead:

```text
Collect batch
      |
Process batch
      |
Deduplicate
      |
Generate files
      |
Generate README/stats
      |
Single Git commit
      |
Push
```

Example commit:

```text
Update configs — 2026-08-20 12:30
```

If GitHub is unavailable:

- keep local database state
- keep generated files
- record publication failure
- retry later
- do not lose collected configurations

Never log the GitHub token.

---

# 20. README Generation

Automatically generate/update README.md.

It should include:

- project title
- operator's Telegram channel branding
- last update time
- total unique configurations
- count by protocol
- links to generated files
- usage instructions
- update information

Do not expose private source-channel data.

---

# 21. Validation

Implement structural validation first.

Separate:

```text
STRUCTURAL VALIDATION
```

from:

```text
NETWORK VALIDATION
```

Structural validation should check things such as:

- valid protocol
- valid URI structure
- required fields
- decodable data
- valid parameter structure

Do not make network testing mandatory.

Network validation can create:

- false negatives
- delays
- unnecessary network traffic
- temporary failures

If network validation is added later, make it optional/configurable.

---

# 22. Error Handling

The system must continue processing when individual messages/configurations fail.

Use:

- per-message exception handling
- structured logging
- retry logic
- Telegram FloodWait handling
- GitHub API retry/error handling
- transaction safety

One malformed configuration must never stop an entire collection run.

---

# 23. Logging

Use Python's standard `logging` module.

Log:

- startup
- shutdown
- channel processing
- messages scanned
- configurations extracted
- duplicates detected
- invalid configurations
- database errors
- GitHub publication
- bot commands
- scheduled jobs

Never log:

- Telegram API hash
- Telegram bot token
- GitHub token
- session secrets
- other credentials

---

# 24. Environment Variables

Create `.env.example`.

Suggested values:

```env
TELEGRAM_API_ID=
TELEGRAM_API_HASH=
TELEGRAM_BOT_TOKEN=

GITHUB_TOKEN=
GITHUB_OWNER=
GITHUB_REPO=
GITHUB_BRANCH=main

CHANNEL_NAME=
CHANNEL_USERNAME=
CHANNEL_ID=

ADMIN_USER_IDS=

COLLECTION_INTERVAL_MINUTES=30
FIRST_RUN_MESSAGE_LIMIT=5000

DRY_RUN=true

LOG_LEVEL=INFO
```

Do not hard-code credentials.

Add `.env` to `.gitignore`.

Add Telegram session files to `.gitignore`.

---

# 25. Dry Run Mode

Implement:

```env
DRY_RUN=true
```

When enabled:

Allowed:

- Telegram collection
- parsing
- normalization
- deduplication
- local database testing
- output generation

Disabled:

- GitHub push
- destructive operations

This mode must be usable during development.

---

# 26. CLI

Provide a simple CLI.

Examples:

```bash
python main.py collect
python main.py run
python main.py status
python main.py publish
python main.py test-parser
```

Commands must work from Git Bash.

Provide help output.

---

# 27. Testing Requirements

Create unit tests for:

- VMess extraction
- VLESS extraction
- Trojan extraction
- Shadowsocks extraction
- Hysteria extraction
- Hysteria2 extraction
- multiple configurations in one message
- malformed configuration handling
- normalization
- equivalent formatting
- duplicate detection
- database insertion
- database uniqueness
- output generation
- branding
- GitHub publishing logic

Fixtures should include:

- exact duplicates
- normalized duplicates
- different fragments/names
- URL-encoded values
- malformed URLs
- mixed Telegram messages
- multiple protocols in one message

Run:

```bash
pytest
```

All tests must pass before declaring the implementation complete.

---

# 28. Security Requirements

Never:

- hard-code credentials
- commit `.env`
- commit Telegram sessions
- expose admin IDs unnecessarily
- expose source channel information publicly unless explicitly enabled
- print secrets in logs

Validate administrator authorization server-side.

Do not trust Telegram message contents.

Treat all incoming messages as untrusted input.

Avoid unsafe shell execution with configuration values.

If subprocess/Git is used, pass arguments safely rather than constructing unsafe shell commands.

---

# 29. Reliability Requirements

The application should survive:

- malformed messages
- Telegram rate limits
- temporary Telegram errors
- temporary GitHub failures
- database interruptions
- process restarts
- partial collection
- duplicate messages
- repeated scheduler triggers

Collection state must be persisted.

Do not depend on in-memory state for critical progress tracking.

---

# 30. Performance

Avoid:

- scanning entire channels on every cycle
- inserting duplicates repeatedly
- committing every configuration individually
- unnecessary network validation
- loading huge datasets into memory when avoidable

Use incremental collection.

Use database indexes.

Batch database operations where appropriate.

Batch GitHub publishing.

---

# 31. Important Parser Design

Use a common parser interface.

Conceptually:

```python
class ConfigParser:
    protocol: str

    def extract(self, text: str) -> list[str]:
        ...

    def parse(self, raw: str):
        ...

    def normalize(self, parsed):
        ...

    def validate(self, parsed) -> bool:
        ...
```

Protocol-specific parsers should implement this interface or an equivalent clean abstraction.

Do not create one giant regular expression for every protocol.

---

# 32. Important Deduplication Design

Deduplication should be deterministic.

Conceptually:

```text
raw config
    ↓
protocol parser
    ↓
parsed object
    ↓
canonical representation
    ↓
SHA-256
    ↓
config_hash
```

The database should enforce uniqueness where appropriate.

Do not rely exclusively on application-level checks.

---

# 33. Public vs Private Data

### Public

Only:

- branded configuration files
- public statistics
- public README
- update timestamp
- protocol counts

### Private/internal

Keep:

- source channel
- source message ID
- first/last seen
- internal database IDs
- processing errors
- admin configuration

Do not accidentally publish the internal database.

---

# 34. Initial Development Phases

Implement in this order.

## Phase 0 — Analysis

Before coding:

- inspect repository
- confirm architecture
- identify ambiguities
- identify dependencies
- produce implementation plan

STOP and report before full implementation.

---

## Phase 1 — Project Scaffold

Create:

- package structure
- configuration
- logging
- database foundation
- tests
- `.env.example`
- `.gitignore`

Verify project starts.

---

## Phase 2 — Parser

Implement:

- extractors
- parsers
- normalization
- structural validation

Write tests first where practical.

---

## Phase 3 — Database

Implement:

- channels
- configs
- collection_runs
- repository methods
- uniqueness/indexes

Test persistence.

---

## Phase 4 — Telegram Collector

Implement:

- authentication
- channel loading
- historical scan
- incremental scan
- FloodWait handling
- progress persistence

Test with a controlled channel.

---

## Phase 5 — Output Generator

Implement:

- all.txt
- protocol files
- branding
- stats
- README generation

Test output compatibility.

---

## Phase 6 — GitHub Publisher

Implement:

- GitHub authentication
- local generation
- commit
- push
- retry/error handling

Test against a dedicated test repository first.

---

## Phase 7 — Admin Bot

Implement:

- authorization
- channel management
- run
- status
- stats
- GitHub status
- errors

---

## Phase 8 — Scheduler

Implement:

- scheduled collection
- locking
- graceful shutdown
- retry logic

---

## Phase 9 — Integration Testing

Test the complete pipeline:

```text
Telegram
   ↓
Collector
   ↓
Parser
   ↓
Normalizer
   ↓
Deduplication
   ↓
Database
   ↓
Output
   ↓
GitHub
```

---

# 35. Acceptance Criteria

The project is complete only when all of the following are true.

### Telegram

- [ ] Telegram client authenticates successfully.
- [ ] Configured source channels can be added.
- [ ] Historical messages can be collected.
- [ ] New messages can be collected incrementally.
- [ ] FloodWait is handled.
- [ ] Collection can resume after restart.

### Parser

- [ ] VMess extraction works.
- [ ] VLESS extraction works.
- [ ] Trojan extraction works.
- [ ] Shadowsocks extraction works.
- [ ] Hysteria extraction works.
- [ ] Hysteria2 extraction works.
- [ ] Multiple configurations in one message work.
- [ ] Malformed configurations do not crash the pipeline.

### Deduplication

- [ ] Exact duplicates are removed.
- [ ] Normalized duplicates are removed.
- [ ] Hash-based uniqueness works.
- [ ] Duplicate database inserts are prevented.

### Database

- [ ] Channels persist.
- [ ] Configurations persist.
- [ ] Collection progress persists.
- [ ] Collection runs are recorded.

### Branding

- [ ] Public output uses configured operator branding.
- [ ] Source channel information is private by default.
- [ ] Machine-readable files remain compatible.

### GitHub

- [ ] Authentication works.
- [ ] Files are generated.
- [ ] Git commit is created.
- [ ] Changes are pushed.
- [ ] Failed pushes do not lose collected data.

### Bot

- [ ] Admin authentication works.
- [ ] `/status` works.
- [ ] `/channels` works.
- [ ] `/addchannel` works.
- [ ] `/removechannel` works.
- [ ] `/run` works.
- [ ] `/stats` works.
- [ ] `/github` works.
- [ ] `/errors` works.

### Security

- [ ] Secrets are environment variables.
- [ ] `.env` is ignored.
- [ ] Telegram sessions are ignored.
- [ ] Secrets do not appear in logs.
- [ ] Unauthorized users cannot control the system.

### Testing

- [ ] `pytest` passes.
- [ ] Dry-run works.
- [ ] Parser fixtures pass.
- [ ] Duplicate fixtures pass.
- [ ] Integration test passes.

---

# 36. Documentation Requirements

Create:

## README.md

Include:

- project overview
- architecture
- features
- repository output
- quick start
- usage

## SETUP.md

Include:

- Python setup
- virtual environment
- dependency installation
- Telegram API credentials
- Telegram authentication
- bot creation/configuration
- GitHub token
- environment variables
- first run
- Git Bash commands

## TROUBLESHOOTING.md

Include solutions for:

- Telegram authentication problems
- FloodWait
- invalid API credentials
- bot authorization
- GitHub authentication
- Git push failures
- database errors
- parser failures
- session problems

---

# 37. Git Bash Commands

Documentation should use Git Bash-compatible commands.

Typical setup:

```bash
python -m venv .venv
source .venv/Scripts/activate
pip install -r requirements.txt
```

Running:

```bash
python main.py run
```

Testing:

```bash
pytest
```

Do not make PowerShell syntax the primary documented workflow.

---

# 38. Operational Recommendation

The first deployment should use:

```text
DRY_RUN=true
```

and a dedicated test GitHub repository.

After successful validation:

```text
DRY_RUN=false
```

Then move to the production repository.

Do not immediately point the first test deployment at the production repository.

---

# 39. Future Improvements

Do not implement these unless requested, but keep architecture compatible with them:

- PostgreSQL
- Redis
- web dashboard
- Docker
- multiple GitHub repositories
- multiple output formats
- advanced configuration scoring
- optional network validation
- configuration health history
- automatic expiry/removal
- statistics dashboard
- webhook-based GitHub updates
- multiple Telegram accounts
- horizontal workers

---

# 40. Final Devin Reporting Format

After implementation, report:

1. Summary of what was implemented.
2. Final architecture.
3. Files created/modified.
4. Dependencies.
5. Environment variables.
6. Telegram authentication steps.
7. GitHub setup steps.
8. Exact Git Bash commands to run.
9. Test results.
10. Dry-run results.
11. Known limitations.
12. Recommended next improvements.

Do not say "tested" unless the test was actually executed.

Do not hide failing tests or known limitations.

---

# 41. Final Instruction

Prioritize:

1. Correctness
2. Security
3. Data integrity
4. Deduplication accuracy
5. Reliability
6. Maintainability
7. Performance

Keep the implementation modular and understandable.

Do not over-engineer the first version.

Start with **Phase 0 — Analysis** and report the proposed architecture and important decisions before implementing the complete system.
