# Deploy PickPilot on Streamlit Community Cloud

1. Publish this repository to `vandanareddyn2920-hub/pickpilot-ai` on GitHub.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/) with your GitHub account and choose **Create app**.
3. Choose the repository `vandanareddyn2920-hub/pickpilot-ai`, branch `main`, and main file `app.py`.
4. Under **Advanced settings**, choose Python **3.11**. Leave secrets empty for the public, no-key portfolio demo.
5. Choose an available app subdomain, then deploy. Share the actual `https://…streamlit.app` URL after the build succeeds.
6. Verify overview metrics, all four demo questions, risk filtering, slotting and routes, and the Validation view. Cold starts generate the seeded database and train the small model automatically.

The root `requirements.txt` supplies the dependencies. SQLite storage is ephemeral on the host; the app recreates its synthetic snapshot after a restart. There is no external database to configure. The app is a read-only prototype and stores no user edits.

## Optional live LLM

For a private or otherwise access-controlled demo, add these **root-level** secrets in Streamlit's secrets editor:

```toml
OPENAI_API_KEY = "YOUR_REAL_KEY"
OPENAI_MODEL = "YOUR_RESPONSES_COMPATIBLE_MODEL"
```

Streamlit exposes root-level secrets as environment variables, which the app reads. Never put a real key in a repository file. Restart the app after changing secrets, enable Live LLM and test a free-form question. Live API calls incur usage on the supplied account; leave secrets empty for an unrestricted recruiter demo. The no-key examples remain fully usable.

## Troubleshooting

- Dependency build fails: confirm Python 3.11 and root `requirements.txt`.
- Missing API key: leave Live LLM off, or configure the two secrets above.
- Model unavailable: set `OPENAI_MODEL` to a Responses API model enabled for your API account.
- Query rejected: the read-only executor rejects unsupported operations; try a question answerable from the displayed operational schema.
- Generated data looks stale: the snapshot is intentionally fixed to November 4, 2026 for reproducibility.

Official references: [Deploy an app](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy) and [Secrets management](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management).
