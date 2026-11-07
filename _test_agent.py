import sys, traceback
from urllib.parse import urlparse

from google import genai
from app.config import settings
import switch_trust

print("gateway:", settings.switch_trust_gateway_url)
print("policy:", settings.switch_trust_policy_id)
print("agent_id:", settings.agent_id)
print("agent_name:", settings.agent_name)
print("model:", settings.gemini_model)

gateway_url = urlparse(settings.switch_trust_gateway_url)
allow_insecure_gateway = (
    gateway_url.scheme == "http"
    and gateway_url.hostname in {"localhost", "127.0.0.1", "::1"}
)
client = genai.Client(api_key=settings.google_api_key)
switch_trust.wrap(
    client,
    gateway_url=settings.switch_trust_gateway_url,
    api_key=settings.switch_trust_api_key,
    llm_api_key=settings.google_api_key,
    policy_id=settings.switch_trust_policy_id,
    allow_insecure_gateway=allow_insecure_gateway,
)
try:
    resp = client.models.generate_content(
        model=settings.gemini_model,
        contents="ping",
    )
    print("success:", resp.content)
except Exception as e:
    traceback.print_exc()
    sys.exit(1)
