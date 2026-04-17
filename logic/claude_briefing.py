import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

def generate_expert_briefing(
    task_title: str,
    task_domain: str,
    task_priority: int,
    time_spent: float,
    employee_text: str,
    detected_emotions: dict
) -> dict:
    """
    Generates a smart briefing for the expert
    using Groq AI before they join the session.
    """

    # Build priority label
    priority_labels = {
        1: "Critical",
        2: "High",
        3: "Medium",
        4: "Low",
        5: "Very Low"
    }
    priority_label = priority_labels.get(task_priority, "Medium")

    # Format emotions for prompt
    emotion_text = "None detected"
    if detected_emotions:
        emotion_text = ", ".join([
            f"{emotion} ({round(score * 100)}%)"
            for emotion, score in detected_emotions.items()
        ])

    # Build the prompt
    prompt = f"""
You are an expert technical advisor helping a senior developer 
understand a colleague's problem quickly.

Here is the situation:

Task: {task_title}
Domain: {task_domain}
Priority: {priority_label}
Time spent: {time_spent} minutes
Employee's message: "{employee_text}"
Detected emotions: {emotion_text}

Please provide a structured briefing with exactly these 3 sections:

1. SUMMARY
A 2-3 sentence summary of what the developer is struggling with 
and their current mental state.

2. POSSIBLE CAUSES
List 3 most likely technical causes of this problem.

3. SUGGESTED STEPS
List 3 concrete first steps the expert should take when joining.

Keep it concise and technical. No fluff.
"""

    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            max_tokens=500,
            temperature=0.7
        )

        raw_text = response.choices[0].message.content

        # Parse the response into sections
        briefing = parse_briefing(raw_text)
        return briefing

    except Exception as e:
        # If API fails return a basic briefing
        return {
            "summary": f"Developer stuck on {task_title} for {time_spent} minutes.",
            "possible_causes": [
                "Check error logs for stack trace",
                "Verify environment configuration",
                "Review recent code changes"
            ],
            "suggested_steps": [
                "Ask developer to share their screen",
                "Review the error message together",
                "Check documentation for known issues"
            ],
            "error": str(e)
        }


def parse_briefing(raw_text: str) -> dict:
    """
    Parses the AI response into a structured dict.
    """
    lines = raw_text.strip().split("\n")

    summary = []
    possible_causes = []
    suggested_steps = []

    current_section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if "SUMMARY" in line.upper():
            current_section = "summary"
            continue
        elif "POSSIBLE CAUSES" in line.upper():
            current_section = "causes"
            continue
        elif "SUGGESTED STEPS" in line.upper():
            current_section = "steps"
            continue

        if current_section == "summary":
            summary.append(line)
        elif current_section == "causes":
            # Remove leading numbers or dashes
            clean = line.lstrip("0123456789.-) ").strip()
            if clean:
                possible_causes.append(clean)
        elif current_section == "steps":
            clean = line.lstrip("0123456789.-) ").strip()
            if clean:
                suggested_steps.append(clean)

    return {
        "summary": " ".join(summary) if summary else raw_text[:200],
        "possible_causes": possible_causes[:3] if possible_causes else [],
        "suggested_steps": suggested_steps[:3] if suggested_steps else [],
        "raw": raw_text
    }