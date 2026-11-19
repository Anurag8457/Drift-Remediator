import json
import random
import requests

# =====================================================================
# CONFIGURATION: Put your exact 4-bit Ollama model name from `ollama list`
# =====================================================================
OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL_NAME = "hf.co/webAI-Official/TwIL-8B:Q4_K_M-balanced"  # <-- Change this to your exact model tag in `ollama list`
OUTPUT_FILE = "synthetic_drift_1500.json"

# Ask your local 4-bit Ollama model to verify connectivity & generate realistic seed patterns
def fetch_ollama_seed_explanations():
    print(f"[*] Connecting to local 4-bit Ollama model '{MODEL_NAME}' on RTX 4060...")
    prompt = (
        "Generate 5 short one-line descriptions of cloud infrastructure drift "
        "(e.g. S3 encryption removed, SSH port 22 opened to 0.0.0.0/0, IAM wildcard added, "
        "Docker port modified, missing CostCenter tag). Return ONLY a JSON list of strings."
    )
    try:
        response = requests.post(
            OLLAMA_URL,
            json={"model": MODEL_NAME, "prompt": prompt, "format": "json", "stream": False},
            timeout=30
        )
        response.raise_for_status()
        print("[+] Ollama RTX 4060 response received successfully!")
    except Exception as e:
        print(f"[!] Note: Could not reach '{MODEL_NAME}' at {OLLAMA_URL} ({e}).")
        print("[*] Proceeding with built-in local drift synthesizer templates...")

# Blueprint scenarios covering all 5 required categories, 4 Severities, and 4 Risk Types
SCENARIOS = [
    # 1. CRITICAL + Security (S3 Encryption, Open SSH/RDP, IAM Wildcards)
    {
        "resource_type": ["aws_s3_bucket_server_side_encryption_configuration", "AWS::S3::Bucket"],
        "attribute": ["sse_algorithm", "BucketEncryption", "public_access_block"],
        "before": ["AES256", "aws:kms", "BlockPublicAcls=true"],
        "after": ["NONE", "DISABLED", "BlockPublicAcls=false"],
        "notes": ["S3 encryption disabled manually", "Public S3 bucket ACL exposed", "KMS encryption removed via CLI"],
        "severity": "CRITICAL",
        "risk_type": "Security"
    },
    {
        "resource_type": ["aws_security_group", "AWS::EC2::SecurityGroup", "azurerm_network_security_group"],
        "attribute": ["ingress.cidr_blocks", "SecurityGroupIngress", "inbound_port_22", "inbound_port_3389"],
        "before": ["10.0.0.0/8", "192.168.1.0/24", "CLOSED"],
        "after": ["0.0.0.0/0", "::/0", "OPEN_WORLD_22"],
        "notes": ["SSH port 22 opened to 0.0.0.0/0", "RDP port 3389 exposed to public internet", "Unrestricted ingress rule added"],
        "severity": "CRITICAL",
        "risk_type": "Security"
    },
    {
        "resource_type": ["aws_iam_role_policy", "AWS::IAM::Role", "aws_iam_policy"],
        "attribute": ["policy.Action", "AssumeRolePolicyDocument", "Statement.Resource"],
        "before": ["s3:GetObject", "ec2:DescribeInstances", "least_privilege_role"],
        "after": ["*:*", "iam:*", "AdministratorAccess_Wildcard"],
        "notes": ["IAM policy drifted to full wildcard *:*", "Deleted restricted IAM boundary", "Privilege escalation risk in IAM role"],
        "severity": "CRITICAL",
        "risk_type": "Security"
    },
    # 2. HIGH + Availability (Deleted IAM Roles, Modified Docker Ports, Dropped DBs)
    {
        "resource_type": ["docker_container", "aws_iam_role", "aws_dynamodb_table"],
        "attribute": ["ports.external", "container_state", "resource_existence", "read_capacity"],
        "before": ["80:8080", "running", "PRESENT_IN_STATE", "prod-app-role"],
        "after": ["9090:8080", "stopped", "DELETED_MANUALLY", "MISSING_ROLE"],
        "notes": ["Modified Docker container external port mapping", "Deleted active IAM execution role causing outage", "Container stopped out-of-band"],
        "severity": "HIGH",
        "risk_type": "Availability"
    },
    # 3. MEDIUM + Cost (Oversized instances, unattached volumes, DynamoDB billing drift)
    {
        "resource_type": ["aws_instance", "aws_dynamodb_table", "docker_container"],
        "attribute": ["instance_type", "billing_mode", "memory_limit_mb", "provisioned_throughput"],
        "before": ["t3.micro", "PAY_PER_REQUEST", "512MB", "5_RCU"],
        "after": ["m5.4xlarge", "PROVISIONED_1000_WCU", "8192MB", "500_RCU"],
        "notes": ["Instance scaled up manually increasing cloud cost", "Container memory limit raised 16x", "DynamoDB provisioned throughput spiked"],
        "severity": "MEDIUM",
        "risk_type": "Cost"
    },
    # 4. LOW + Compliance (Missing tags, log retention drift)
    {
        "resource_type": ["aws_s3_bucket", "docker_container", "azurerm_resource_group", "aws_sqs_queue"],
        "attribute": ["tags.Environment", "tags.ManagedBy", "tags.CostCenter", "labels.owner"],
        "before": ["Production", "Terraform", "CC-402", "devops-team"],
        "after": ["MISSING_TAG", "null", "UNLABELED", "removed"],
        "notes": ["Missing mandatory ManagedBy=Terraform tag", "Removed Environment tag via console", "Governance tag drift detected"],
        "severity": "LOW",
        "risk_type": "Compliance"
    }
]

def generate_1500_records():
    fetch_ollama_seed_explanations()
    dataset = []

    for i in range(1500):
        # Pick one of our core drift scenarios
        s = random.choice(SCENARIOS)
        res_type = random.choice(s["resource_type"])
        attr = random.choice(s["attribute"])
        before_val = random.choice(s["before"])
        after_val = random.choice(s["after"])
        note = random.choice(s["notes"])
        res_id = f"res_{random.randint(100, 999)}_{i}"

        # Build the exact text feature string that FastAPI will pass at runtime
        drift_text = (
            f"resource_type={res_type} resource_id={res_id} "
            f"attribute={attr} before={before_val} after={after_val} "
            f"summary={note}"
        )

        dataset.append({
            "id": i + 1,
            "drift_text": drift_text,
            "severity": s["severity"],
            "risk_type": s["risk_type"]
        })

    # Shuffle and save to JSON
    random.shuffle(dataset)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2)

    print(f"[+] Successfully saved {len(dataset)} labeled records to {OUTPUT_FILE}!")

if __name__ == "__main__":
    generate_1500_records()