import re
import base64
import logging

CANARY_TOKEN = 'CANARY_TOKEN_FIN_AGENT_2024'

def sanitize_user_input(user_input: str) -> tuple[bool, str, str]:
    """Check user input for prompt injection attacks."""
    injection_patterns = [
        r'ignore\s+(all\s+)?(previous\s+|prior\s+|above\s+|any\s+)?(instructions|rules|constraints|prompts)',
        r'system\s*prompt',
        r'you\s+are\s+now',
        r'pretend\s+(you\s+are|to\s+be)',
        r'act\s+as\s+(a\s+)?different',
        r'new\s+instructions',
        r'override\s+(all|the|my|your|previous)',
        r'disregard\s+(all|the|my|your|previous|above)',
        r'forget\s+(all|everything|your)',
        r'reveal\s+(your|the)\s+(prompt|instructions|system)',
        r'what\s+(are|is)\s+your\s+(instructions|prompt|system)',
        r'repeat\s+(your|the)\s+(instructions|prompt|system)',
        r'output\s+(your|the)\s+(instructions|prompt|system)',
        r'show\s+me\s+(your|the)\s+(prompt|instructions|system|rules)',
        r'ADMIN\s*MODE',
        r'DEVELOPER\s*MODE',
        r'DAN\s+mode',
        r'jailbreak',
        r'bypass\s+(security|filter|restriction|access|rbac)',
        r'show\s+(me\s+)?everything\s+for\s+all\s+roles',
        r'give\s+me\s+access\s+to\s+all',
        r'switch\s+(my\s+)?role\s+to',
        r'elevate\s+(my\s+)?privileges',
    ]
    
    # Check for direct patterns
    for pattern in injection_patterns:
        if re.search(pattern, user_input, re.IGNORECASE):
            return False, user_input, f"Prompt injection detected: matched pattern '{pattern}'"
            
    # Check for base64 encoding attacks
    try:
        words = user_input.split()
        for word in words:
            if len(word) > 10 and re.match(r'^[A-Za-z0-9+/]+={0,2}$', word):
                try:
                    decoded = base64.b64decode(word).decode('utf-8')
                    for pattern in injection_patterns:
                        if re.search(pattern, decoded, re.IGNORECASE):
                            return False, user_input, f"Base64 encoded prompt injection detected."
                except Exception:
                    pass
    except Exception:
        pass
        
    # Check for role confusion
    role_patterns = [
        r'System:', r'system:', r'Assistant:', r'assistant:', r'AI:', r'ai:'
    ]
    for pattern in role_patterns:
        if re.search(pattern, user_input):
            return False, user_input, "Role confusion detected."
            
    return True, user_input, ''

def sanitize_document_content(content: str, source_file: str) -> str:
    """Clean document content during ingestion."""
    # Look for patterns like 'AI:', 'Assistant:', 'System:', 'Instruction:' followed by imperative text
    suspicious_patterns = [
        r'(?i)AI:.*?(\n|$)',
        r'(?i)Assistant:.*?(\n|$)',
        r'(?i)System:.*?(\n|$)',
        r'(?i)Instruction:.*?(\n|$)'
    ]
    
    cleaned_content = content
    for pattern in suspicious_patterns:
        matches = re.finditer(pattern, cleaned_content)
        for match in matches:
            logging.warning(f"Suspicious content found in {source_file}: {match.group(0).strip()}")
        cleaned_content = re.sub(pattern, '', cleaned_content)
        
    return cleaned_content

def validate_output(response: str) -> tuple[bool, str]:
    """Check agent output for leaked system info."""
    is_safe = True
    cleaned_response = response
    
    if CANARY_TOKEN in cleaned_response:
        is_safe = False
        cleaned_response = cleaned_response.replace(CANARY_TOKEN, '[REDACTED]')
        
    sensitive_patterns = [
        r'(?i)RBAC rules?:?.*',
        r'(?i)internal configuration.*',
        r'(?i)api[-_]key\s*[:=]\s*\S+',
        r'(?i)token\s*[:=]\s*\S+'
    ]
    
    for pattern in sensitive_patterns:
        if re.search(pattern, cleaned_response):
            is_safe = False
            cleaned_response = re.sub(pattern, '[REDACTED]', cleaned_response)
            
    return is_safe, cleaned_response
