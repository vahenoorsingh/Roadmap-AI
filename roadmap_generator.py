import json
import re
import ollama

def build_prompt(goal: str, known: str) -> str:
    """Build the prompt instructing llama3.1 to generate an overview, nodes, and edges."""
    return f"""You are a curriculum graph generator.

Goal: {goal}
Known: {known}

Return JSON only with overview, nodes, and edges.

Overview:
A concise 1-2 sentence overview of this learning roadmap.

Nodes:
{{"id": "...", "label": "...", "description": "...", "difficulty": "beginner|intermediate|advanced", "hours": 5}}

Edges:
{{"from": "...", "to": "...", "reason": "..."}}

Expected JSON format:
{{
  "overview": "A 1-2 sentence overview summarizing the path from current knowledge to the goal.",
  "nodes": [
    {{"id": "1", "label": "...", "description": "...", "difficulty": "beginner|intermediate|advanced", "hours": 5}}
  ],
  "edges": [
    {{"from": "1", "to": "2", "reason": "..."}}
  ]
}}

Rules:
- 5-8 nodes if topics are not specified by user.
- Edge means from must be learned before to.
- No cycles.
- Only JSON.
"""

def generate_roadmap(goal: str, known: str = "None", model: str = "llama3.1") -> str:
    """Pass prompt to llama3.1 via Ollama and return the raw response content."""
    prompt = build_prompt(goal=goal, known=known)
    response = ollama.chat(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        format="json"
    )
    return response["message"]["content"]

def parse_roadmap_data(response_content: str) -> dict:
    """Parse and clean JSON response from llama3.1."""
    text = response_content.strip()
    # Strip markdown code blocks if present
    if "```" in text:
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
        if match:
            text = match.group(1).strip()
    
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{[\s\S]*\})", text)
        if match:
            return json.loads(match.group(1))
        raise

if __name__ == "__main__":
    sample_goal = "Become a backend developer"
    sample_known = "Basic Python"
    print(f"Goal: {sample_goal}\nKnown: {sample_known}\n")
    print("Calling llama3.1...")
    raw = generate_roadmap(sample_goal, sample_known)
    data = parse_roadmap_data(raw)
    print("\nOverview:")
    print(data.get("overview"))
    print("\nNodes count:", len(data.get("nodes", [])))
    print("Edges count:", len(data.get("edges", [])))