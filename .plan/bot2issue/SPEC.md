# SPEC: bot2issue (Universal Bot-to-Issue Hub)

- **Owner**: michmingcao
- **Target Repo for this codebase**: `michmingcao/bot2issue`
- **Target Egress Repos**: Configurable via `config/projects.json` / commands
- **Channels**: WeChat ClawBot (Tencent iLink) & WeCom (Enterprise WeChat)
- **Status**: ready-for-dev

## Key Technical Decisions
1. **Zero External Heavy Dependencies**:
   - Built on pure Python 3 standard library + minimal cryptography for iLink AES-128-ECB.
2. **Channel Abstraction**:
   - `BaseChannel` interface decoupling iLink and WeCom from the core AI engine.
3. **Cloud AI Protocol**:
   - Standard OpenAI-compatible format (`/v1/chat/completions`), seamlessly working with DeepSeek, Qwen/DashScope, Zhipu GLM, etc.
4. **GitHub Dispatching**:
   - Uses `GITHUB_TOKEN` or local authenticated `gh` CLI to create issues with labels, media links, and markdown formatting.
