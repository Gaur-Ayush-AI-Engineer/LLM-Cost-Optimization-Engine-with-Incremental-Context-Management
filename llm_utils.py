import requests
import json
from typing import List, Dict, Iterator
from config import (
    OPENROUTER_KEY, 
    OPENROUTER_URL, 
    MODEL_CONFIG,
    SUMMARY_PROMPT,
    COMPRESS_PROMPT
)


def call_llm(messages: List[Dict], max_tokens: int = 4000, temperature: float = 0.8) -> str:
    """Call OpenRouter API"""
    payload = {
        "model": MODEL_CONFIG["name"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        r = requests.post(url=OPENROUTER_URL, json=payload, headers=headers, timeout=120)
        r.raise_for_status()
        
        response_data = r.json()
        content = response_data["choices"][0]["message"]["content"]
        usage = response_data.get("usage", {})

        return content,usage
    except Exception as e:
        print(f"❌ LLM call failed: {e}")
        raise

def call_llm_stream(messages: List[Dict], max_tokens: int = 4000, temperature: float = 0.8) -> Iterator[str]:
    """Call OpenRouter API with streaming"""
    payload = {
        "model": MODEL_CONFIG["name"],
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "top_p": 0.9,
        "stream": True  # ← Enable streaming!
    }
    
    headers = {
        "Authorization": f"Bearer {OPENROUTER_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            url=OPENROUTER_URL, 
            json=payload, 
            headers=headers, 
            stream=True,  # ← Important!
            timeout=120
        )
        response.raise_for_status()
        
        # Process streaming response
        for line in response.iter_lines():
            if line:
                line = line.decode('utf-8')
                
                # OpenRouter sends: "data: {...}"
                if line.startswith('data: '):
                    data_str = line[6:]  # Remove "data: " prefix
                    
                    # Check for end signal
                    if data_str == '[DONE]':
                        break
                    
                    try:
                        data = json.loads(data_str)
                        # Extract the text chunk
                        if 'choices' in data and len(data['choices']) > 0:
                            delta = data['choices'][0].get('delta', {})
                            content = delta.get('content', '')
                            if content:
                                yield content  # ← Yield each chunk
                    except json.JSONDecodeError:
                        continue
                        
    except Exception as e:
        print(f"❌ Streaming LLM call failed: {e}")
        raise

def generate_summary(messages: List[Dict], max_tokens: int = 2000) -> str:
    """Generate summary using LLM"""
    # Format messages for summary
    conversation_text = ""
    for msg in messages:
        conversation_text += f"{msg['role']}: {msg['content']}\n\n"
    
    summary_messages = [
        {"role": "system", "content": SUMMARY_PROMPT},
        {"role": "user", "content": f"Summarize this story conversation:\n\n{conversation_text}"}
    ]
    
    try:
        summary,_ = call_llm(summary_messages, max_tokens=max_tokens, temperature=0.5)
        return summary
    except Exception as e:
        print(f"❌ Summary generation failed: {e}")
        return "Story context available."


def compress_message(content: str, target_tokens: int = 800) -> str:
    """Compress a single long message"""
    compress_messages = [
        {"role": "system", "content": COMPRESS_PROMPT},
        {"role": "user", "content": content}
    ]
    
    try:
        compressed,_ = call_llm(compress_messages, max_tokens=target_tokens, temperature=0.8)
        return compressed
    except Exception as e:
        print(f"❌ Message compression failed: {e}")
        # Fallback: truncate
        return content[:target_tokens * 4]